from .. import OrderType


class Order:
    @staticmethod
    def isLiquidationOrder(_orderType: OrderType) -> bool:
        return _orderType == OrderType.Liquidation
