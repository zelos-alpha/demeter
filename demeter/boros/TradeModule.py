from decimal import Decimal
from _typing import SingleOrderReq, Side, SwapMathParams, TimeInForce, SideLib, LongShort, CancelData
from SwapMathLib import SwapMathLib
from OrdersLib import OrdersLib
from TickSweepStateLib import TickSweepStateLib, TickSweepState, Stage
from AMM import AMM
from TradeLib import TradeLib

class TradeModule:

    def __init__(self, tickStep, maturity):
        self.tickStep = tickStep
        self.maturity = maturity

    def placeSingleOrder(self, req: SingleOrderReq):
        swaps = TradeModule._createSwapMathParams(
            tickStep=self.tickStep,
            timeToMat=TradeModule._getTimeToMat(),
            side=req.order.side)
        matched, takerOtcFee = self._splitAndSwapBookAMM(
            swaps=swaps, 
            tif=req.order.tif,
            totalSize=req.order.size,
            limitTick=req.order.tick,
            idToCancel=''
        )


    def _splitAndSwapBookAMM(
            self,
            swaps: SwapMathParams,
            tif: TimeInForce,
            totalSize: Decimal,
            limitTick: int,
            idToCancel: str
        ):
        withBook, withAMM = TradeModule.calcSwapAmountBookAMM(swaps, totalSize, limitTick)
        orders = OrdersLib.createOrders(tif, withBook, withAMM)
        cancel = OrdersLib.createCancel(idToCancel, True)
        return self._swapBookAMM(withAMM, orders, cancel)

    def _swapBookAMM(self, ammSwapSize: int, orders: LongShort, cancelData: CancelData):
        if ammSwapSize:
            ammCost = AMM.swapByBorosRouter(ammSwapSize)
            totalMatched = TradeLib._from(ammSwapSize, ammCost)



    @staticmethod
    def calcSwapAmountBookAMM(swaps: SwapMathParams, totalSize: Decimal, limitTick: int) -> (int, int):
        if totalSize <= Decimal(0):
            return 0, 0
        matchingSide = SideLib.opposite(swaps.userSide)
        sweep = TickSweepStateLib.create(matchingSide, int(swaps.nTicksToTryAtOnce))
        withBook = 0
        while TickSweepStateLib.hasMore(sweep):
            lastTick, sumTickSize = TickSweepStateLib.getLastTickAndSumSize(sweep)
            if not SideLib.canMatch(matchingSide, limitTick, lastTick):
                TickSweepStateLib.transitionDown(sweep)
                continue
            tmpWithAMM = TickSweepStateLib.calcSwapAMMToBookTick(sweep, lastTick)
            tmpWithBook = withBook + SideLib.toSignedSize(sumTickSize, swaps.userSide)
            newTotalSize = tmpWithAMM + tmpWithBook

            if newTotalSize == totalSize:
                return tmpWithBook, tmpWithAMM

            if abs(newTotalSize) > abs(totalSize):
                TickSweepStateLib.transitionDown(sweep)
            else:
                withBook = tmpWithBook
                TickSweepStateLib.transitionUp(sweep)
        return TradeModule._calcFinalSwapAmount(swaps, sweep, withBook, totalSize, limitTick)

    @staticmethod
    def _calcFinalSwapAmount(swaps: SwapMathParams, sweepState: TickSweepState, withBook: Decimal, totalSize: Decimal, limitTick: int):
        finalTick = TradeModule._getFinalTick(swaps, sweepState, limitTick)
        maxWithAMM = TickSweepStateLib.calcSwapAMMToBookTick(sweepState, finalTick)
        withAMM = SideLib.toSignedSize(min(abs(totalSize - withBook), abs(maxWithAMM)), swaps.userSide)
        return totalSize - withAMM, withAMM

    @staticmethod
    def _getFinalTick(swaps: SwapMathParams, sweepState: TickSweepState, limitTick: int) -> int:
        if sweepState.stage == Stage.FOUND_STOP:
            lastTick = TickSweepStateLib.getLastTick(sweepState)
            matchingSide = SideLib.opposite(swaps.userSide)
            return lastTick if SideLib.canMatch(matchingSide, limitTick, lastTick) else limitTick
        elif sweepState.stage == Stage.SWEPT_ALL:
            return limitTick
        assert False

    @staticmethod
    def _getTimeToMat():
        return 0  # todo

    @staticmethod
    def _createSwapMathParams(tickStep: int, timeToMat: int, side: Side):
        numTicksToTryAtOnce = TradeModule._getNumTicksToTryAtOnce()
        return SwapMathLib.create(
            tickStep=tickStep,
            nTicksToTryAtOnce=numTicksToTryAtOnce,
            userSide=side,
            timeToMat=timeToMat
        )

    @staticmethod
    def _getNumTicksToTryAtOnce():
        # todo read from data csv
        return 0