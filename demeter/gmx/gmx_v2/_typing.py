from dataclasses import dataclass
from enum import Enum
from typing import List, NamedTuple, Union

import pandas as pd

from demeter import TokenInfo


@dataclass
class PoolConfig:
    longDecimal: int
    shortDecimal: int
    swapImpactExponentFactor: float = 2  # 👒
    swapImpactFactor_Positive: float = 200000000000000000000 / 10 ** 30  # 👒
    swapImpactFactor_Negative: float = 300000000000000000000 / 10 ** 30  # 👒
    depositFeeFactor_Positive: float = 0.0005  # 👒
    depositFeeFactor_Negative: float = 0.0007  # 👒
    withdrawFeeFactor_Positive: float = 0.0005  # 👒
    withdrawFeeFactor_Negative: float = 0.0007  # 👒
    swapFeeFactor_BalanceNotImproved: float = 0.0007  # 👒
    swapFeeFactor_BalanceWasImproved: float = 0.0005  # 👒
    positionImpactExponentFactor = 1655417464419320500000000000000 / 10**30  # 👒 #TODO
    positionImpactFactor_Positive = 34111358107691540000000 / 10 ** 30  # 👒
    positionImpactFactor_Negative = 40933629729229850000000 / 10 ** 30  # 👒
    maxPositionImpactFactor_Positive = 5000000000000000000000000000 / 10 ** 30  # 0.005
    maxPositiveImpactFactor_Negative = 5000000000000000000000000000 / 10 ** 30  # 0.005
    positionFeeFactor_Positive = 400000000000000000000000000 / 10 ** 30  # 0.0004# 👒
    positionFeeFactor_Negative = 600000000000000000000000000 / 10 ** 30  # 0.0006# 👒
    liquidationFeeFactor = 400000000000000000000000000 / 10**30  # 👒
    maxPnlFactor_ForTrader_Long = 900000000000000000000000000000 / 10 ** 30  # 0.9 👒
    maxPnlFactor_ForTrader_Short = 900000000000000000000000000000 / 10 ** 30  # 0.9  👒
    minCollateralFactorForOpenInterestMultiplier_Long = 60000000000000000000 / 10 ** 30  # 👒
    minCollateralFactorForOpenInterestMultiplier_Short = 60000000000000000000 / 10 ** 30  # 👒
    minCollateralFactor = 5000000000000000000000000000 / 10**30  # 0.005👒
    minCollateralUsd = 1000000000000000000000000000000 / 10**30  # 1 👒
    minPositionSizeUsd = 1000000000000000000000000000000 / 10**30  # 1 👒

    # SKIP_BORROWING_FEE_FOR_SMALLER_SIDE
    skip_borrowing_fee_for_smaller_side = True
    ignore_open_interest_for_usage_factor = True # REMOVE this !!!! doesn't support kink
    openInterestReserveFactor_Long = 2.7
    openInterestReserveFactor_Short = 2.7  # todo check
    baseBorrowingFactor_Long = 14269406392694063926940 / 10 ** 30
    baseBorrowingFactor_Short = 14269406392694063926940 / 10 ** 30
    fundingIncreaseFactorPerSecond = 1988547595363155833 / 10**30
    fundingDecreaseFactorPerSecond = 0  # todo

    fundingExponentFactor = 1
    fundingFactor = 0  # todo
    thresholdForStableFunding = 0.04
    thresholdForDecreaseFunding = 0  # todo
    minFundingFactorPerSecond = 317097919837645865043 / 10**30
    maxFundingFactorPerSecond = 21476314029922083333333 / 10**30

    maxPositionImpactFactorForLiquidation = 0  # MAX_POSITION_IMPACT_FACTOR_FOR_LIQUIDATIONS
    minCollateralFactorForLiquidation=0

class GmxV2Pool(NamedTuple):
    long_token: TokenInfo
    short_token: TokenInfo
    index_token: TokenInfo

    def __eq__(self, other):
        if not isinstance(other, GmxV2Pool):
            return False
        return (
            self.long_token == other.long_token
            and self.short_token == other.short_token
            and self.index_token == other.index_token
        )

    def __str__(self):
        return f"{self.index_token.name}/USD[{self.long_token.name}-{self.short_token.name}]"

    def __repr__(self):
        return self.__str__()

@dataclass
class Prices:
    maxPrice: float
    minPrice: float

    @property
    def midPrice(self) -> float:
        return (self.maxPrice + self.minPrice) / 2


@dataclass
class GmxV2PoolStatus:
    longAmount: float
    shortAmount: float
    virtualSwapInventoryLong: float
    virtualSwapInventoryShort: float
    poolValue: float
    marketTokensSupply: float
    impactPoolAmount: float
    pendingPnl: float  # pnl caused by open interest
    realizedPnl: float  # pnl for decreased position
    realizedProfit: float  # pnl + fee + priceImpact
    openInterestLong: float  # 👒
    openInterestShort: float  # 👒
    openInterestLongIsLong: float
    openInterestLongNotLong: float
    openInterestShortIsLong: float
    openInterestShortNotLong: float
    openInterestInTokensLong: float
    openInterestInTokensShort: float
    longPrice: float
    shortPrice: float
    indexPrice: float
    # positionImpactExponentFactor: float
    # positionImpactFactorPositive: float
    # positionImpactFactorNegative: float
    virtualPositionInventoryLong: float  # 👒
    virtualPositionInventoryShort: float  # 👒
    positionImpactPoolAmount: float  # PositionImpactPoolAmountUpdated
    positionFeeFactor: float  # -> positive & negative
    positionFeeReceiverFactor: float
    borrowingFeeReceiverFactor: float
    cumulativeBorrowingFactorLong: float  # CumulativeBorrowingFactorUpdated  👒
    cumulativeBorrowingFactorShort: float  # CumulativeBorrowingFactorUpdated  👒
    longTokenFundingFeeAmountPerSizeLong: float  # FundingFeeAmountPerSizeUpdated  👒
    longTokenFundingFeeAmountPerSizeShort: float  # FundingFeeAmountPerSizeUpdated  👒
    shortTokenFundingFeeAmountPerSizeLong: float  # FundingFeeAmountPerSizeUpdated  👒
    shortTokenFundingFeeAmountPerSizeShort: float  # FundingFeeAmountPerSizeUpdated  👒
    longTokenClaimableFundingAmountPerSizeLong: float  # ClaimableFundingAmountPerSizeUpdated   👒
    longTokenClaimableFundingAmountPerSizeShort: float  # ClaimableFundingAmountPerSizeUpdated  👒
    shortTokenClaimableFundingAmountPerSizeLong: float  # ClaimableFundingAmountPerSizeUpdated  👒
    shortTokenClaimableFundingAmountPerSizeShort: float  # ClaimableFundingAmountPerSizeUpdated  👒



@dataclass
class PoolData:
    market: GmxV2Pool
    status: Union[GmxV2PoolStatus, pd.Series]
    config: PoolConfig


@dataclass
class LPResult:
    long_amount: float
    short_amount: float
    total_usd: float

    gm_amount: float
    gm_usd: float

    long_fee: float
    short_fee: float
    fee_usd: float

    price_impact_usd: float


@dataclass
class PositionResult:
    collateralToken: str
    collateralAmount: float
    sizeInUsd: float
    sizeInTokens: float
    borrowingFactor: float
    fundingFeeAmountPerSize: float
    longTokenClaimableFundingAmountPerSize: float
    shortTokenClaimableFundingAmountPerSize: float
    isLong: bool


class OrderType(Enum):
    MarketSwap = 0
    LimitSwap = 1
    MarketIncrease = 2
    LimitIncrease = 3
    MarketDecrease = 4
    LimitDecrease = 5
    StopLossDecrease = 6
    Liquidation = 7
    StopIncrease = 8


class DecreasePositionSwapType(Enum):
    NoSwap = 0
    SwapPnlTokenToCollateralToken = 1
    SwapCollateralTokenToPnlToken = 2


@dataclass
class Order:
    market: GmxV2Pool|None
    initialCollateralToken: TokenInfo|None
    swapPath: List[GmxV2Pool] = None
    orderType: OrderType = OrderType.LimitIncrease
    sizeDeltaUsd: float = 0
    initialCollateralDeltaAmount: float = 0
    triggerPrice: float = 0
    acceptablePrice: float = 0
    isLong: bool | None = None
    decreasePositionSwapType: DecreasePositionSwapType | None = None


@dataclass
class ExecuteOrderParams:
    order: Order
    swapPathMarkets: List[GmxV2Pool]
    market: GmxV2Pool


@dataclass
class CollateralType:
    longToken: float = 0
    shortToken: float = 0


class PositionType:
    long: CollateralType
    short: CollateralType


@dataclass
class GetNextFundingAmountPerSizeResult:
    fundingFeeAmountPerSizeDelta: PositionType = PositionType()
    claimableFundingAmountPerSizeDelta: PositionType = PositionType()
    longsPayShorts: bool = False
    fundingFactorPerSecond: float = 0


@dataclass
class GetNextFundingAmountPerSizeCache:
    openInterest: PositionType = PositionType()
    longOpenInterest: float = 0
    shortOpenInterest: float = 0
    durationInSeconds: float = 0
    sizeOfLargerSide: float = 0
    fundingUsd: float = 0
    fundingUsdForLongCollateral: float = 0
    fundingUsdForShortCollateral: float = 0


@dataclass
class GetNextFundingFactorPerSecondCache:
    diffUsd: float = 0
    totalOpenInterest: float = 0
    fundingFactor: float = 0
    fundingExponentFactor: float = 0
    diffUsdAfterExponent: float = 0
    diffUsdToOpenInterestFactor: float = 0
    savedFundingFactorPerSecond: float = 0
    savedFundingFactorPerSecondMagnitude: float = 0
    nextSavedFundingFactorPerSecond: float = 0
    nextSavedFundingFactorPerSecondWithMinBound: float = 0


@dataclass
class FundingConfigCache:
    thresholdForStableFunding: float = 0
    thresholdForDecreaseFunding: float = 0
    fundingIncreaseFactorPerSecond: float = 0
    fundingDecreaseFactorPerSecond: float = 0
    minFundingFactorPerSecond: float = 0
    maxFundingFactorPerSecond: float = 0


class FundingRateChangeType(Enum):
    NoChange = 0
    Increase = 1
    Decrease = 2
