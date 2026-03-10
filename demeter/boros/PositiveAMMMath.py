import math

from _typing import AMMState
from PMath import PMath

class PositiveAMMMath:
    @staticmethod
    def calcMintOutput(state: AMMState, markRate: int, totalCash: int, _totalSize: int, maxCashIn: int, exactSizeIn: int) -> (AMMState, int, int):
        totalSize = PositiveAMMMath._snapSmallSizeTo0(_totalSize)
        if totalSize == 0:
            netLpOut = (state.totalLp * maxCashIn) / totalCash
            netCashIn = maxCashIn
        else:
            absTotalSize = abs(totalSize)
            absExactSizeIn = abs(exactSizeIn)
            isPositionValuePositive = (PMath.sign(totalSize) == PMath.sign(markRate))
            if isPositionValuePositive:
                netLpOut = (state.totalLp * absExactSizeIn) / absTotalSize  # 向下取整
            else:
                netLpOut = (state.totalLp * absExactSizeIn) / absTotalSize  # 向下取整
            netCashIn = (totalCash * netLpOut) / state.totalLp

        state.totalFloatAmount += (state.totalFloatAmount * netLpOut) / state.totalLp
        state.normFixedAmount += (state.normFixedAmount * netLpOut) / state.totalLp
        state.totalLp += netLpOut
        return state, netCashIn, netLpOut


    @staticmethod
    def _snapSmallSizeTo0(size: int) -> int:
        return size if size > 1e3 else 0  # todo div 1e18

    @staticmethod
    def calcBurnOutput(state: AMMState, markRate: int, totalCash: int, _totalSize: int, lpToBurn: int) -> (AMMState, int, int, bool):
        netCashOut = (totalCash * lpToBurn) / state.totalLp
        isMatured = state.maturity <= state.latestFTime
        if isMatured:
            return state, netCashOut, 0, isMatured
        totalSize = PositiveAMMMath._snapSmallSizeTo0(_totalSize)
        isPositionValuePositive = (PMath.sign(totalSize) == PMath.sign(markRate))
        if isPositionValuePositive:
            absSizeOut = (abs(totalSize) * lpToBurn) / state.totalLp
        else:
            absSizeOut = (abs(totalSize) * lpToBurn) / state.totalLp
        netSizeOut = absSizeOut * PMath.sign(totalSize)
        state.totalFloatAmount -= (state.totalFloatAmount * lpToBurn) / state.totalLp
        state.normFixedAmount -= (state.normFixedAmount * lpToBurn) / state.totalLp
        state.totalLp -= lpToBurn
        return state, netCashOut, netSizeOut, isMatured

    @staticmethod
    def calcSwapOutput(state: AMMState, floatOut: int) -> (AMMState, int):
        normalizedTime = PositiveAMMMath.calcNormalizedTime(state)
        floatOutAbs = abs(floatOut)
        if floatOut > 0:
            newTotalFloatAmount = state.totalFloatAmount - floatOutAbs
        else:
            newTotalFloatAmount = state.totalFloatAmount + floatOutAbs
        liquidity = math.pow(state.totalFloatAmount, normalizedTime) * state.normFixedAmount  # todo div ONE
        newNormFixedAmount = liquidity / math.pow(newTotalFloatAmount, normalizedTime)
        normFixedIn = newNormFixedAmount - state.normFixedAmount
        state.totalFloatAmount = newTotalFloatAmount
        state.normFixedAmount = newNormFixedAmount
        fixedIn = normFixedIn // normalizedTime
        return state, fixedIn

    @staticmethod
    def calcNormalizedTime(state: AMMState) -> int:
        pass