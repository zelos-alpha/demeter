from ._typing import Side, TimeInForce, OrderId, LongShort, CancelData
class OrdersLib:
    """Library for order operations"""

    @staticmethod
    def create_orders(side: Side, tif: TimeInForce, size: int, tick: int) -> LongShort:
        """Create a LongShort order structure"""
        return LongShort(
            tif=tif,
            side=side,
            sizes=[size],
            ticks=[tick]
        )

    @staticmethod
    def create_cancel(id_to_cancel: OrderId, is_strict: bool) -> CancelData:
        """Create cancel data"""
        if id_to_cancel.is_zero():
            return CancelData(ids=[], is_all=False, is_strict=False)
        return CancelData(ids=[id_to_cancel], is_all=False, is_strict=is_strict)
