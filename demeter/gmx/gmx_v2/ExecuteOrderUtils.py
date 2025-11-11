from .IncreaseOrderUtils import IncreaseOrderUtils
from .DecreaseOrderUtils import DecreaseOrderUtils
from .SwapOrderUtils import SwapOrderUtils
from ._typing import PoolConfig, GmxV2PoolStatus, Order, OrderType, ExecuteOrderParams, Market, PoolStatus
from .._typing2 import GmxV2Pool


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
        status: dict[str, PoolStatus],
        positions,
    ):

        _market = Market(
            marketToken=status[order.market].pool.market_token.address,
            indexToken=status[order.market].pool.index_token.address,
            longToken=status[order.market].pool.long_token.address,
            shortToken=status[order.market].pool.short_token.address,
        )
        params = ExecuteOrderParams(order=order, swapPathMarkets=[], market=_market)
        if ExecuteOrderUtils.isIncreaseOrder(params.order):
            return IncreaseOrderUtils.processOrder(params, pool_status, pool_config, pool, positions)
        elif ExecuteOrderUtils.isDecreaseOrder(params.order):
            return DecreaseOrderUtils.processOrder(params, pool_status, pool_config, pool, positions)
        elif ExecuteOrderUtils.isSwapOrder(params.order):
            return SwapOrderUtils.processOrder(params, pool_status, pool_config)
