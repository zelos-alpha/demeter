from BaseAMM import BaseAMM
from _typing import AMMState
from Market import MarketEntry
from PositiveAMMMath import PositiveAMMMath


class PositiveAMM(BaseAMM):
    @staticmethod
    def _mint(_state, totalCash: int, totalSize: int, maxCashIn: int, exactSizeIn: int):
        state = AMMState()  # todo init from _state
        markRate = MarketEntry.getMarkRate()
        updatedState, netCashIn, netLpOut = PositiveAMMMath.calcMintOutput(state, markRate, totalCash, totalSize, maxCashIn, exactSizeIn)
        print('PositiveAMM _mint')
        return updatedState, netCashIn, netLpOut

    @staticmethod
    def _burn(_state, totalCash: int, totalSize: int, lpToBurn: int):
        state = AMMState()  # todo init from _state
        markRate = MarketEntry.getMarkRate()
        updatedState, netCashOut, netSizeOut, isMatured = PositiveAMMMath.calcBurnOutput(state, markRate, totalCash, totalSize, lpToBurn)
        print('PositiveAMM _burn')
        return updatedState, netCashOut, netSizeOut, isMatured

    @staticmethod
    def _swap(_state, sizeOut: int):
        state = AMMState()  # todo init from _state
        updatedState, costOut = PositiveAMMMath.calcSwapOutput(state, sizeOut)
        print('PositiveAMM _swap')
        return updatedState, costOut
