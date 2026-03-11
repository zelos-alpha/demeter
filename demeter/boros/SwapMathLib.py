from Market import MarketEntry
from _typing import SwapMathParams, Side
from AMM import AMM
from decimal import Decimal

class SwapMathLib:
    @staticmethod
    def create(tickStep: int, nTicksToTryAtOnce: int, userSide: Side, timeToMat: int):
        takerFeeRate, ammOtcFeeRate = MarketEntry.getBestFeeRates()
        return SwapMathParams(
            userSide=userSide, 
            takerFeeRate=takerFeeRate,
            ammOtcFeeRate=ammOtcFeeRate,
            ammAllInFeeRate=ammOtcFeeRate + AMM.feeRate(),
            tickStep=Decimal(tickStep),
            nTicksToTryAtOnce=Decimal(nTicksToTryAtOnce),
            timeToMat=Decimal(timeToMat)
        )