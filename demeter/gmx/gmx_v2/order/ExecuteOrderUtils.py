from .._typing import Order, OrderType


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
