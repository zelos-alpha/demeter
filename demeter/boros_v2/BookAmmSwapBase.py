#
from ._typing import (SwapMathParams, TimeInForce, Tuple, Trade, Side, MarketCache, MarketAcc, MarketId, TokenId, AMMId,
                      OrderId, TickSweepState, Stage, LongShort, CancelData, OTCTrade)
from .MarketHub import MarketHub
from .AMM import AMM
from .OrdersLib import OrdersLib
from .TickSweepStateLib import TickSweepStateLib


class BookAmmSwapBase:

    def __init__(self, market_hub: MarketHub):
        self.market_hub = market_hub
        self.amms = {}

    def register_amm(self, amm_id: AMMId, amm: AMM) -> None:
        """Register an AMM"""
        self.amms[amm_id.value] = amm

    def split_and_swap_book_amm(self, params: SwapMathParams, tif: TimeInForce,
                                total_size: int, limit_tick: int, id_to_cancel: OrderId) -> Tuple[Trade, int]:
        with_book, with_amm = self.calc_swap_amount_book_amm(params, total_size, limit_tick)

        orders = OrdersLib.create_orders(params.user_side, tif, with_book, limit_tick)
        cancel = OrdersLib.create_cancel(id_to_cancel, True)

        return self.swap_book_amm(params.user, params.amm, with_amm, orders, cancel)

    def swap_book_amm(
            self,
            user: MarketAcc,
            amm_acc: MarketAcc,
            amm_swap_size: int,
            orders: LongShort,
            cancel_data: CancelData
    ) -> Tuple[Trade, int]:
        """Execute swap with AMM and book"""
        # Get AMM
        amm_id = int(amm_acc.root.split("_")[1]) if "_" in amm_acc.root else 0
        amm = self.amms.get(amm_id, AMM(0, 0))

        total_matched = Trade(0, 0)

        # Place order on book
        market_id = MarketId(amm.market_id)
        otcs = []
        if amm_swap_size != 0:
            # Swap with AMM
            amm_cost = amm.swap_by_router(amm_swap_size)
            total_matched = Trade(signed_size=amm_swap_size, signed_cost=amm_cost)
            otcs.append(OTCTrade(
                counter=amm_acc,
                trade=Trade(amm_swap_size, amm_cost),
                cash_to_counter=0
            ))

        book_matched, taker_otc_fee = self.market_hub.order_and_otc(
            market_id,
            user,
            orders,
            cancel_data,
            otcs
        )

        # Combine matches
        total_matched = Trade(
            signed_size=total_matched.signed_size + book_matched.signed_size,
            signed_cost=total_matched.signed_cost + book_matched.signed_cost
        )

        return total_matched, taker_otc_fee

    def calc_swap_amount_book_amm(
        self,
        params: SwapMathParams,
        total_size: int,
        limit_tick: int
    ) -> Tuple[int, int]:
        if params.amm.is_zero() or total_size == 0:
            return (0, 0)
        matching_side = Side.SHORT if params.user_side == Side.LONG else Side.LONG
        mock_ticks = [100, 102, 104, 106, 108] if matching_side == Side.LONG else [-100, -102, -104, -106, -108]
        mock_sizes = [100000, 200000, 150000, 300000, 250000]
        sweep = TickSweepStateLib.create(
            market=params.market,
            tick_side=matching_side,
            n_ticks_to_try_at_once=params.n_ticks_to_try_at_once,
            mock_ticks=mock_ticks,
            mock_sizes=mock_sizes
        )
        with_book = 0
        while TickSweepStateLib.has_more(sweep):
            last_tick, sum_tick_size = TickSweepStateLib.get_last_tick_and_sum_size(sweep)
            if not self._can_match(matching_side, limit_tick, last_tick):
                TickSweepStateLib.transition_down(sweep)
                continue
            tmp_with_amm = self._calc_swap_amm_to_book_tick(params, last_tick)
            # Accumulate book size
            signed_tick_size = sum_tick_size if params.user_side == Side.LONG else -sum_tick_size
            tmp_with_book = with_book + signed_tick_size

            new_total_size = tmp_with_book + tmp_with_amm

            # Check if we have exact match
            if new_total_size == total_size:
                return (tmp_with_book, tmp_with_amm)

            # Check if exceeded total size
            if abs(new_total_size) > abs(total_size):
                TickSweepStateLib.transition_down(sweep)
            else:
                with_book = tmp_with_book
                TickSweepStateLib.transition_up(sweep)

            # Calculate final amounts using remaining logic
        return self._calc_final_swap_amount(params, sweep, with_book, total_size, limit_tick)

    def _calc_final_swap_amount(
            self,
            params: SwapMathParams,
            sweep_state: TickSweepState,
            with_book: int,
            total_size: int,
            limit_tick: int
    ) -> Tuple[int, int]:
        """
        Calculate final swap amounts when sweep completes.
        Based on _calcFinalSwapAmount in SwapMath.sol (lines 160-171).
        """
        final_tick = self._get_final_tick(params, sweep_state, limit_tick)
        max_with_amm = self._calc_swap_amm_to_book_tick(params, final_tick)

        remaining = total_size - with_book
        with_amm = min(abs(remaining), abs(max_with_amm))
        with_amm = with_amm if params.user_side == Side.LONG else -with_amm

        return (total_size - with_amm, with_amm)

    def _get_final_tick(
            self,
            params: SwapMathParams,
            sweep_state: TickSweepState,
            limit_tick: int
    ) -> int:
        """Get final tick based on sweep state"""
        matching_side = Side.SHORT if params.user_side == Side.LONG else Side.LONG

        if sweep_state.stage == Stage.FOUND_STOP:
            last_tick = TickSweepStateLib.get_last_tick(sweep_state)
            if self._can_match(matching_side, limit_tick, last_tick):
                return last_tick
            return limit_tick
        elif sweep_state.stage == Stage.SWEPT_ALL:
            return limit_tick

        raise AssertionError("Invalid sweep state")


    def _can_match(self, matching_side: Side, limit_tick: int, tick: int) -> bool:
        """Check if tick can match based on side and limit"""
        if matching_side == Side.LONG:
            return tick <= limit_tick  # Buy orders: lower tick is better
        else:
            return tick >= limit_tick  # Sell orders: higher tick is better


    def create_swap_math_params(self, cache: MarketCache, user: MarketAcc, amm: MarketAcc,
                                 side: Side, time_to_mat: int) -> SwapMathParams:
        """Create swap math parameters"""
        return SwapMathParams(
            market=cache.market,
            user=user,
            amm=amm,
            user_side=side,
            taker_fee_rate=500000000000000,
            amm_otc_fee_rate=500000000000000,
            amm_all_in_fee_rate=1000000000000000,
            tick_step=cache.tick_step,
            n_ticks_to_try_at_once=5,
            time_to_mat=time_to_mat
        )

    def get_market_cache(self, market_id: MarketId) -> MarketCache:
        return MarketCache(
            market=f"0xMARKET_{market_id.value}",
            token_id=TokenId(1),
            maturity=86400 * 30,
            tick_step=2
        )

    def get_amm_id_to_acc(self, amm_id: AMMId) -> MarketAcc:
        """Get AMM account from AMM ID"""
        return MarketAcc(f"0xAMM_{amm_id.value}", 1, self.amms.get(amm_id.value, AMM(0, 0)).market_id)

    def get_time_to_mat(self, cache: MarketCache) -> int:
        return cache.maturity  # todo

    def _calc_swap_amm_to_book_tick(self, params: SwapMathParams, book_tick: int) -> int:
        """
        Calculate AMM swap size needed to reach book tick rate.
        Based on calcSwapAMMToBookTick in SwapMath.sol (lines 68-76).

        The calculation:
        1. Convert book tick to base rate (includes taker fee)
        2. Convert base rate to AMM rate (includes AMM fee)
        3. Calculate swap size needed to reach that AMM rate
        4. Return 0 if result doesn't match user side
        """
        # Step 1: Convert book tick to base rate
        # baseRate = bookRate +/- takerFeeRate (depending on side)
        book_rate = book_tick * params.tick_step
        if params.user_side == Side.LONG:
            base_rate = book_rate + params.taker_fee_rate
        else:
            base_rate = book_rate - params.taker_fee_rate

        # Step 2: Convert base rate to AMM rate
        # ammRate = baseRate +/- ammAllInFeeRate (depending on side)
        if params.user_side == Side.LONG:
            amm_rate = base_rate - params.amm_all_in_fee_rate
        else:
            amm_rate = base_rate + params.amm_all_in_fee_rate

        # Step 3: Calculate swap size from AMM rate
        # This uses the AMM's rate curve to determine swap size
        swap_size = self._calc_swap_size_from_amm_rate(params, amm_rate)

        # Step 4: Ensure swap is in correct direction
        # If swap_size doesn't match user_side, return 0
        if params.user_side == Side.LONG and swap_size < 0:
            return 0
        if params.user_side == Side.SHORT and swap_size > 0:
            return 0

        return swap_size

    def _calc_swap_size_from_amm_rate(self, params: SwapMathParams, amm_rate: int) -> int:
        """
        Calculate swap size given target AMM rate.
        Based on IAMM.calcSwapSize in the actual implementation.
        """
        # Get AMM from params
        amm_id = int(params.amm.root.split("_")[1]) if "_" in params.amm.root else 0
        amm = self.amms.get(amm_id)

        if amm is None:
            return 0

        # Call AMM to calculate swap size
        return amm.calc_swap_size(amm_rate)  # todo update code