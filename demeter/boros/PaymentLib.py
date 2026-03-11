from _typing import Trade
from PMath import PMath
from TradeLib import TradeLib

class PaymentLib:

    @staticmethod
    def calcUpfrontFixedCost(cost: int, timeToMat: int) -> int:
        return cost * timeToMat / PMath.IONE_YEAR


    @staticmethod
    def toUpfrontFixedCost(trade: Trade, timeToMat: int) -> int:
        return PaymentLib.calcUpfrontFixedCost(TradeLib.signedCost(trade), timeToMat)