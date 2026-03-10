from dataclasses import dataclass
from enum import Enum
from typing import Dict, NamedTuple, Union, List, NewType
from decimal import Decimal


class Side(Enum):
    LONG = 0
    SHORT = 1

class SideLib:
    @staticmethod
    def opposite(side: Side) -> Side:
        return Side.SHORT if side == Side.LONG else Side.LONG

    @staticmethod
    def sweepTickTopDown(side: Side) -> bool:
        return side == Side.LONG

    @staticmethod
    def endTick(side: Side) -> int:
        # -32,768 to 32,767
        return -32768 if side == Side.LONG else 32767

    @staticmethod
    def possibleToBeFilled(side: Side, orderTick: int, lastTickFilled: int) -> bool:
        return lastTickFilled <= orderTick if SideLib.sweepTickTopDown(side) else lastTickFilled >= orderTick

    @staticmethod
    def tickToGetFirstAvail(side: Side) -> int:
        return SideLib.endTick(side)

    @staticmethod
    def canMatch(side: Side, limitTick: int, bestTick: int) -> bool:
        return limitTick <= bestTick if SideLib.sweepTickTopDown(side) else limitTick >= bestTick

    @staticmethod
    def isOfSide(size: int, side: Side) -> bool:
        return (size > 0 and side == Side.LONG) or (size < 0 and side == Side.SHORT)

    @staticmethod
    def checkRateInBound(side: Side, rate: int, bound: int) -> bool:
        if side == Side.LONG:
            return rate <= bound
        else:
            return rate >= bound

    @staticmethod
    def toSignedSize(size: int, side: Side) -> int:
        return size if side == Side.LONG else -size

class TimeInForce(Enum):
    GTC = 0
    IOC = 1
    FOK = 2
    ALO = 3
    SOFT_ALO = 4
    
@dataclass
class OrderReq(NamedTuple):
    cross: bool
    side: Side
    tif: TimeInForce
    size: Decimal
    tick: int


@dataclass
class SingleOrderReq(NamedTuple):
    order: OrderReq

@dataclass
class SwapMathParams(NamedTuple):
    userSide: Side
    takerFeeRate: Decimal
    ammOtcFeeRate: Decimal
    ammAllInFeeRate: Decimal
    tickStep: Decimal
    nTicksToTryAtOnce: Decimal
    timeToMat: Decimal


class Stage(Enum):
    LOOP_BATCH = 0,
    LOOP_SINGLE = 1,
    BINARY_SEARCH = 2,
    FOUND_STOP = 3,
    SWEPT_ALL= 4

@dataclass
class TickSweepState(NamedTuple):
    stage: Stage = Stage.SWEPT_ALL
    ticks: List = None
    tickSizes: List = None
    singleIndex: int = 0
    bin_min: int = 0
    bin_max: int = 0
    side: Side = Side.LONG
    nTicksToTryAtOnce: int = 0


@dataclass
class LongShort(NamedTuple):
    tif: TimeInForce = TimeInForce.ALO
    side: Side = Side.LONG
    sizes: List = None
    limitTicks: List = None


@dataclass
class CancelData(NamedTuple):
    ids: List = None
    isAll: bool = False
    isStrict: bool = False

@dataclass
class AMMState(NamedTuple):
    totalFloatAmount: int = 0
    normFixedAmount: int = 0
    totalLp: int = 0
    latestFTime: int = 0
    maturity: int = 0
    seedTime: int = 0
    minAbsRate: int = 0
    maxAbsRate: int = 0
    cutOffTimestamp: int = 0


@dataclass
class UserResult(NamedTuple):
    settle: int
    payment: int
    removedIds: List
    bookMatched: str
    partialPayFee: int
    isStrictIM: bool
    finalVM: str
    
@dataclass
class MatchAux(NamedTuple):
    side: Side
    tickStep: int
    latestFTag: int
    sizes: List = None
    limitTicks: List = None


@dataclass
class TickMatchResult(NamedTuple):
    partialSize: int = 0
    partialMakerNonce: int = 0
    beginFullyFilledOrderIndex: int = 0
    endFullyFilledOrderIndex: int = 0


Trade = NewType('Trade', int)
Fill = NewType('Fill', int)
PayFee = NewType('PayFee', int)
FTag = NewType('FTag', int)
VMResult = NewType('VMResult', int)
AMMId = NewType('AMMId', int)


@dataclass
class PMDataMem(NamedTuple):
    sumLongSize: int
    sumLongPM: int
    sumShortSize: int
    sumShortPM: int


@dataclass
class UserMem(NamedTuple):
    longIds: List
    shortIds: List
    fTag: FTag
    preSettleSize: int
    postSettleSize: int
    signedSize: int
    pmData: PMDataMem


@dataclass
class OTCResult(NamedTuple):
    settle: PayFee
    payment: PayFee
    isStrictIM: bool
    finalVM: VMResult


@dataclass
class LiquidityMathParams(NamedTuple):
    _core: SwapMathParams
    maxIteration: int
    eps: int
    ammCash: int
    ammSize: int
    totalCashIn: int


@dataclass
class AddLiquiditySingleCashToAmmReq(NamedTuple):
    cross: bool
    ammId: AMMId
    netCashIn: int
    minLpOut: int
    desiredSwapSide: Side
    desiredSwapRate: int


class GetRequest(Enum):
    IM = 0
    MM = 1
    ZERO = 2

@dataclass
class SweptF(NamedTuple):
    fTag: FTag
    __fill: Fill

@dataclass
class PartialData(NamedTuple):
    sumLongSize: int
    sumLongPM: int
    sumShortSize: int
    sumShortPM: int
    fTag: FTag
    sumCost: int

