from _typing import TimeInForce, LongShort, Side, CancelData

class OrdersLib:
    @staticmethod
    def createOrders(tif: TimeInForce, size: int, limitTick: int) -> LongShort:
        res = LongShort()
        if size == 0:
            return res
        res.tif = tif
        res.side = Side.LONG if size > 0 else Side.SHORT
        res.sizes = [size]
        res.limitTicks = [limitTick]
        return res

    @staticmethod
    def createCancel(idToCancel: str, isStrict: bool):
        return CancelData()
