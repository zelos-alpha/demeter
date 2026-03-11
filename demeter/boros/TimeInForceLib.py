from _typing import TimeInForce


class TimeInForceLib:
    @staticmethod
    def isALO(tif: TimeInForce) -> bool:
        return tif == TimeInForce.ALO or tif == TimeInForce.SOFT_ALO

    @staticmethod
    def shouldSkipMatchableOrders(tif: TimeInForce) -> bool:
        return tif == TimeInForce.SOFT_ALO
