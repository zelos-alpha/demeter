from _typing import AMMState
class AMM(object):
    _feeRate = 0

    def __init__(self, _feeRate):
        self._feeRate = _feeRate

    @staticmethod
    def feeRate():
        return AMM._feeRate

    @staticmethod
    def swapByBorosRouter(sizeOut: int) -> int:
        costOut, fee = AMM._applyFee(sizeOut, AMM._swap(sizeOut))
        return costOut

    @staticmethod
    def _applyFee(sizeOut: int, costOut: int) -> (int, int):
        fee = abs(sizeOut) * AMM._feeRate
        newCost = costOut + fee
        return newCost, fee

    @staticmethod
    def _swap(sizeOut: int) -> int:
        state = AMMState()
        return AMM.calcSwapOutput(state, sizeOut)

    @staticmethod
    def calcSwapOutput(state: AMMState, floatOut: int):
        normalizedTime = AMM.calcNormalizedTime(state)
        floatOutAbs = abs(floatOut)
        if floatOut > 0:
            newTotalFloatAmount = state.totalFloatAmount - floatOutAbs
        else:
            newTotalFloatAmount = state.totalFloatAmount + floatOutAbs
        liquidity = state.totalFloatAmount ** normalizedTime * state.normFixedAmount
        newNormFixedAmount = liquidity / (newTotalFloatAmount ** newTotalFloatAmount)
        normFixedIn = newNormFixedAmount - state.normFixedAmount
        return normFixedIn / normalizedTime

    @staticmethod
    def calcNormalizedTime(state: AMMState) :
        return (state.maturity - state.latestFTime) / (state.maturity - state.seedTime)
