from _typing import Side, TickSweepState, Stage
from Market import MarketEntry
from decimal import Decimal

class TickSweepStateLib:
    @staticmethod
    def create(tickSide: Side, nTicksToTryAtOnce: int) -> TickSweepState:
        ticks, tickSizes = MarketEntry.getNextNTicks(side=tickSide, nTicks=nTicksToTryAtOnce)
        initState = TickSweepState()
        if ticks.length == 0:
            return initState
        else:
            initState.stage = Stage.LOOP_BATCH
            initState.ticks = ticks
            initState.tickSizes = tickSizes
            initState.side = tickSide
            initState.nTicksToTryAtOnce = nTicksToTryAtOnce
        return initState
    
    @staticmethod
    def hasMore(sweep: TickSweepState) -> bool:
        return sweep.stage != Stage.FOUND_STOP and sweep.stage != Stage.SWEPT_ALL

    @staticmethod
    def getLastTickAndSumSize(sweep: TickSweepState) ->(int, Decimal):
        pass

    @staticmethod
    def calcSwapAMMToBookTick(sweep: TickSweepState, lastTick: int) -> Decimal:
        pass

    @staticmethod
    def transitionDown(sweep: TickSweepState) -> TickSweepState:
        if sweep.stage == Stage.LOOP_BATCH:
            TickSweepStateLib._transitionDownBatch(sweep)
        elif sweep.stage == Stage.LOOP_SINGLE:
            sweep.stage = Stage.FOUND_STOP
        elif sweep.stage == Stage.BINARY_SEARCH:
            TickSweepStateLib._transitionDownBinary(sweep)
        else:
            assert False

    @staticmethod
    def _transitionDownBatch(sweep: TickSweepState):
        pass  # todo

    @staticmethod
    def _transitionDownBinary(sweep: TickSweepState):
        pass  # todo

    @staticmethod
    def transitionUp(sweep: TickSweepState):
        if sweep.stage == Stage.LOOP_BATCH:
            TickSweepStateLib._transitionUpBatch(sweep)
        elif sweep.stage == Stage.LOOP_SINGLE:
            TickSweepStateLib._transitionUpSingle(sweep)
        elif sweep.stage == Stage.BINARY_SEARCH:
            TickSweepStateLib._transitionUpBinary(sweep)
        else:
            assert False

    @staticmethod
    def _transitionUpBatch(sweep: TickSweepState):
        pass

    @staticmethod
    def _transitionUpSingle(sweep: TickSweepState):
        pass

    @staticmethod
    def _transitionUpBinary(sweep: TickSweepState):
        pass

    @staticmethod
    def getLastTick(sweep: TickSweepState) -> int:
        if sweep.stage == Stage.LOOP_BATCH:
            return TickSweepStateLib._lastTickArray(sweep)
        if sweep.stage == Stage.LOOP_SINGLE or sweep.stage == Stage.BINARY_SEARCH or sweep.stage == Stage.FOUND_STOP:
            return sweep.ticks[sweep.singleIndex]
        assert False

    @staticmethod
    def _lastTickArray(sweep: TickSweepState) -> int:
        return  sweep.ticks[-1]



