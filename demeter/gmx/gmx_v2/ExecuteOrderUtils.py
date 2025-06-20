from dataclasses import dataclass
from enum import Enum
from IncreaseOrderUtils import IncreaseOrderUtils

class OrderType(Enum):
    MarketSwap = 0
    LimitSwap = 1
    MarketIncrease = 2
    LimitIncrease = 3
    MarketDecrease = 4
    LimitDecrease = 5
    StopLossDecrease = 6
    Liquidation = 7
    StopIncrease = 8

@dataclass
class Order:
    orderType: OrderType

@dataclass
class ExecuteOrderParams:
    order: Order

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
    def executeOrder(params: ExecuteOrderParams):
        if ExecuteOrderUtils.isIncreaseOrder(params.order):
            IncreaseOrderUtils.processOrder(params)
        elif ExecuteOrderUtils.isDecreaseOrder(params.order):
            pass
        elif ExecuteOrderUtils.isSwapOrder(params.order):
            pass
