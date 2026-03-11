from typing import List
from decimal import Decimal
from .BookAmmSwapBase import BookAmmSwapBase
from ._typing import SingleOrderReq, TimeInForce, OrderId, OrdersLib, LongShort, CancelData, OTCTrade
from .OrderBookUtils import OrderBookStorageStruct
from .SwapMath import SwapMathParams
from .AMM import AMM
from .Trade import Trade


class TradeModule(BookAmmSwapBase):

    def __init__(self, ob_struct: OrderBookStorageStruct, amm: AMM):
        self.ob_struct = ob_struct  # orderbook数据
        self.amm = amm

    def place_single_order(
            self,
            req: SingleOrderReq,
            tick_step: int,
            maturity: int,
            last_f_time: int,
            taker_fee_rate: Decimal,
            amm_otc_fee_rate: Decimal,
            amm_fee_rate: Decimal, # IAMM(amm_.root()).feeRate()
            n_ticks_to_try_at_once: int=5
    ) -> None:
        order = req.order
        if order.amm:
            time_to_mat = self._get_time_to_mat(maturity, last_f_time)
            swaps = SwapMathParams(
                amm=order.amm,
                user_side=order.side,
                taker_fee_rate=taker_fee_rate,
                amm_otc_fee_rate=amm_otc_fee_rate,
                amm_all_in_fee_rate=amm_otc_fee_rate + amm_fee_rate,
                tick_step=tick_step,
                n_ticks_to_try_at_once=n_ticks_to_try_at_once,
                time_to_mat=time_to_mat
            )
            self._split_and_swap_book_amm(
                swaps=swaps,
                tif=order.tif,
                total_size=order.side.to_signed_size(order.size),
                limit_tick=order.tick,
                id_to_cancel=req.id_to_strict_cancel
            )
        else:
            pass  # todo

    def _get_time_to_mat(self, maturity, last_f_time) -> int:
        return maturity - last_f_time

    def _split_and_swap_book_amm(
            self,
            swaps: SwapMathParams,
            tif: TimeInForce,
            total_size: Decimal,
            limit_tick: int,
            id_to_cancel: OrderId
    ) -> None:
        with_book, with_amm = swaps.calc_swap_amount_book_amm(swaps, total_size, limit_tick)
        orders = OrdersLib.create_orders_from_size(tif, with_book, limit_tick)
        cancel = OrdersLib.create_cancel(id_to_cancel, True)
        self._swap_book_amm(with_amm, orders, cancel)

    def _swap_book_amm(
            self,
            amm_swap_size: Decimal,
            orders: LongShort,
            cancelData: CancelData
    ):
        pass
        # if amm_swap_size:
        #     amm_cost = self.amm.swap_by_boros_router(amm_swap_size)
        #     otcs = [OTCTrade(trade=Trade(amm_swap_size, amm_cost), cash_to_counter=Decimal('0'))]
        #     total_matched = otcs[0].trade
        # book_matched, taker_otc_fee =

