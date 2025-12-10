from demeter.gmx.gmx_v2 import OrderType


class Order:
    @staticmethod
    def isLiquidationOrder(_orderType: OrderType) -> bool:
        return _orderType == OrderType.Liquidation
