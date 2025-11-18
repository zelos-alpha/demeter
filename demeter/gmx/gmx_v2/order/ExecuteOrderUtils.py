from .IncreaseOrderUtils import IncreaseOrderUtils
from demeter.gmx.gmx_v2.order.DecreaseOrderUtils import DecreaseOrderUtils
from demeter.gmx.gmx_v2.order.SwapOrderUtils import SwapOrderUtils
from demeter.gmx.gmx_v2._typing import Order, OrderType, ExecuteOrderParams, PoolData, GmxV2Pool


class ExecuteOrderUtils:

    @staticmethod
    def isIncreaseOrder(order: Order) -> bool:
        return (
            order.orderType == OrderType.MarketIncrease
            or order.orderType == OrderType.LimitIncrease
            or order.orderType == OrderType.StopIncrease
        )

    @staticmethod
    def isDecreaseOrder(order: Order) -> bool:
        return (
            order.orderType == OrderType.MarketDecrease
            or order.orderType == OrderType.LimitDecrease
            or order.orderType == OrderType.StopLossDecrease
            or order.orderType == OrderType.Liquidation
        )

    @staticmethod
    def isSwapOrder(order: Order) -> bool:
        return order.orderType == OrderType.MarketSwap or order.orderType == OrderType.LimitSwap

    @staticmethod
    def executeOrder(
        order: Order,
        status: dict[GmxV2Pool, PoolData],
        positions,
    ):
        params = ExecuteOrderParams(order=order, swapPathMarkets=order.swapPath, market=order.market)
        if ExecuteOrderUtils.isIncreaseOrder(params.order):
            return IncreaseOrderUtils.processOrder(
                params, status[order.market].status, status[order.market].config, order.market, positions
            )
        elif ExecuteOrderUtils.isDecreaseOrder(params.order):
            return DecreaseOrderUtils.processOrder(
                params, status[order.market].status, status[order.market].config, order.market, positions
            )
        elif ExecuteOrderUtils.isSwapOrder(params.order):
            return SwapOrderUtils.processOrder(params, status)
