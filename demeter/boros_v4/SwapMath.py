from dataclasses import dataclass
from _typing import Side, Tuple
from decimal import Decimal
from .TickMath import TickMath
from .AMM import AMM
from .PMath import PMath
from .PaymentLib import PaymentLib
from .TickSweepStateLib import TickSweepState
from .MarketEntry import MarketEntry
from .OrderBookUtils import OrderBookStorageStruct
from ._typing import Stage


@dataclass
class SwapMathParams:
    amm: AMM
    user_side: Side
    taker_fee_rate: Decimal
    amm_otc_fee_rate: Decimal
    amm_all_in_fee_rate: Decimal
    tick_step: int
    n_ticks_to_try_at_once: int
    time_to_mat: int

    @staticmethod
    def create(
            amm: AMM,
            user_side: Side,
            taker_fee_rate: Decimal,
            amm_otc_fee_rate: Decimal,
            amm_all_in_fee_rate: Decimal,
            tick_step: int,
            n_ticks_to_try_at_once: int,
            time_to_mat: int
    ) -> 'SwapMathParams':
        return SwapMathParams(amm, user_side, taker_fee_rate, amm_otc_fee_rate, amm_all_in_fee_rate, tick_step, n_ticks_to_try_at_once, time_to_mat)

    def calc_swap_amm_to_book_tick(self, book_tick: int) -> Decimal:
        base_rate = self.convert_book_tick_to_base_rate(book_tick)
        amm_rate = self.convert_base_rate_to_amm_rate(base_rate)
        swap_size = self.amm.calc_swap_size(amm_rate)  # todo
        return swap_size if self._is_of_side(swap_size, self.user_side) else Decimal('0')

    def _is_of_side(self, size: Decimal, side: Side) -> bool:
        return (size > 0 and side == Side.LONG) or (size < 0 and side == Side.SHORT)

    def convert_book_tick_to_base_rate(self, book_tick: int) -> Decimal:
        book_rate = TickMath.get_rate_at_tick(book_tick, self.tick_step)  # todo
        book_rate = Decimal(book_rate)  # todo update TickMath
        return book_rate + self.taker_fee_rate if self.user_side == Side.LONG else book_rate - self.taker_fee_rate

    def convert_base_rate_to_amm_rate(self, base_rate: Decimal) -> Decimal:
        if self.user_side == Side.LONG:
            return base_rate - self.amm_all_in_fee_rate
        else:
            return base_rate + self.amm_all_in_fee_rate

    def calc_amm_otc_fee(self, swap_size: Decimal) -> Decimal:
        abs_size = PMath.abs(swap_size)
        return PaymentLib.calc_floating_fee(abs_size, self.amm_otc_fee_rate, self.time_to_mat)

    def calc_book_taker_fee(self, swap_size: Decimal) -> Decimal:
        abs_size = PMath.abs(swap_size)
        return PaymentLib.calc_floating_fee(abs_size, self.taker_fee_rate, self.time_to_mat)

    def calc_swap_amm(self, amm_swap_size: Decimal) -> Tuple[Decimal, Decimal]:
        if amm_swap_size == 0:
            return 0, 0
        amm_cost = self.amm.swap_view(amm_swap_size)
        net_cash_to_amm = PaymentLib.calc_upfront_fixed_cost(amm_cost, self.time_to_mat)
        otc_fee = self.calc_amm_otc_fee(amm_swap_size)
        net_cash_in = net_cash_to_amm + otc_fee
        return net_cash_in, net_cash_to_amm

    def calc_swap_book(self, book_swap_size: Decimal, book_cost: Decimal) -> Decimal:
        upfront_cost = PaymentLib.calc_upfront_fixed_cost(book_cost, self.time_to_mat)
        taker_fee = self.calc_book_taker_fee(book_swap_size)

        return upfront_cost + taker_fee

    def calc_swap_amount_book_amm(self, market: MarketEntry, ob_struct: OrderBookStorageStruct, total_size: Decimal, limit_tick: int) -> Tuple[Decimal, Decimal]:
        if not self.amm or not total_size:
            return Decimal('0'), Decimal('0')
        matching_side = self.user_side.opposite()
        sweep = TickSweepState.create(market, ob_struct, matching_side, self.n_ticks_to_try_at_once)
        with_book = Decimal('0')
        while sweep.has_more():
            last_tick, sum_tick_size = sweep.get_last_tick_and_sum_size()
            if not matching_side.can_match(limit_tick, last_tick):
                sweep.transition_down()
                continue

            tmp_with_amm = self.calc_swap_amm_to_book_tick(last_tick)
            tmp_with_book = with_book + self.user_side.to_signed_size(sum_tick_size)
            new_total_size = tmp_with_book + tmp_with_amm

            if new_total_size == total_size:
                return tmp_with_book, tmp_with_amm

            if PMath.abs(new_total_size) > PMath.abs(total_size):
                sweep.transition_down()
            else:
                with_book = tmp_with_book
                sweep.transition_up()
        return self._calc_final_swap_amount(sweep, with_book, total_size, limit_tick)

    def _calc_final_swap_amount(self, sweep_status: TickSweepState, with_book: Decimal, total_size: Decimal, limit_tick: int) -> Tuple[Decimal, Decimal]:
        final_tick = self._get_final_tick(sweep_status, limit_tick)
        max_with_amm = self.calc_swap_amm_to_book_tick(final_tick)
        min_amount = PMath.min(PMath.abs(total_size - with_book), PMath.abs(max_with_amm))
        with_amm = self.user_side.to_signed_size(min_amount)  # todo
        return total_size - with_amm, with_amm

    def _get_final_tick(self, sweep_status: TickSweepState, limit_tick: int) -> int:
        if sweep_status.stage == Stage.FOUND_STOP:
            last_tick = sweep_status.get_last_tick()
            matching_side = self.user_side.opposite()
            return last_tick if matching_side.can_match(limit_tick, last_tick) else limit_tick
        elif sweep_status.stage == Stage.SWEPT_ALL:
            return limit_tick
        assert False

