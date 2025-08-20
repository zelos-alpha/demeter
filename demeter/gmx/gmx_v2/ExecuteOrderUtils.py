from .IncreaseOrderUtils import IncreaseOrderUtils
from .DecreaseOrderUtils import DecreaseOrderUtils
from .SwapOrderUtils import SwapOrderUtils
from ._typing import PoolConfig, GmxV2PoolStatus, Order, OrderType, ExecuteOrderParams
from .._typing2 import GmxV2Pool


class ExecuteOrderUtils:

    @staticmethod
    def isIncreaseOrder(order: Order) -> bool:
        return (order.orderType == OrderType.MarketIncrease or
                order.orderType == OrderType.LimitIncrease or
                order.orderType == OrderType.StopIncrease)

    @staticmethod
    def isDecreaseOrder(order: Order) -> bool:
        return (order.orderType == OrderType.MarketDecrease or
                order.orderType == OrderType.LimitDecrease or
                order.orderType == OrderType.StopLossDecrease or
                order.orderType == OrderType.Liquidation)

    @staticmethod
    def isSwapOrder(order: Order) -> bool:
        return (order.orderType == OrderType.MarketSwap or
                order.orderType == OrderType.LimitSwap)

    @staticmethod
    def executeOrder(pool_status: GmxV2PoolStatus, pool_config: PoolConfig, pool: GmxV2Pool):
        params = ExecuteOrderParams()
        if ExecuteOrderUtils.isIncreaseOrder(params.order):
            IncreaseOrderUtils.processOrder(params, pool_status, pool_config)
        elif ExecuteOrderUtils.isDecreaseOrder(params.order):
            DecreaseOrderUtils.processOrder(params, pool_status, pool_config, pool)
        elif ExecuteOrderUtils.isSwapOrder(params.order):
            SwapOrderUtils.processOrder(params, pool_status, pool_config)
