from dataclasses import dataclass
from enum import Enum
from typing import List, NamedTuple, Union

import pandas as pd

from demeter import TokenInfo


@dataclass
class PoolConfig:
    swapImpactExponentFactor: float = 2  
    swapImpactFactor_Positive: float = 200000000000000000000 / 10**30  
    swapImpactFactor_Negative: float = 300000000000000000000 / 10**30  
    depositFeeFactor_Positive: float = 0.0005  
    depositFeeFactor_Negative: float = 0.0007  
    withdrawFeeFactor_Positive: float = 0.0005  
    withdrawFeeFactor_Negative: float = 0.0007  
    swapFeeFactor_BalanceNotImproved: float = 0.0007  
    swapFeeFactor_BalanceWasImproved: float = 0.0005  
    positionImpactExponentFactor_Positive: float = 1655417464419320500000000000000 / 10**30  # This value changes too often
    positionImpactExponentFactor_Negative: float = 1655417464419320500000000000000 / 10**30   # This value changes too often
    positionImpactFactor_Positive: float = 34111358107691540000000 / 10**30   # This value changes too often
    positionImpactFactor_Negative: float = 40933629729229850000000 / 10**30   # This value changes too often
    maxPositionImpactFactor_Positive: float = 5000000000000000000000000000 / 10**30  # 0.005
    maxPositiveImpactFactor_Negative: float = 5000000000000000000000000000 / 10**30  # 0.005
    positionFeeFactor_Positive: float = 400000000000000000000000000 / 10**30  # 0.0004
    positionFeeFactor_Negative: float = 600000000000000000000000000 / 10**30  # 0.0006
    liquidationFeeFactor: float = 400000000000000000000000000 / 10**30  
    maxPnlFactor_ForTrader_Long: float = 900000000000000000000000000000 / 10**30  # 0.9 
    maxPnlFactor_ForTrader_Short: float = 900000000000000000000000000000 / 10**30  # 0.9  
    minCollateralFactorForOpenInterestMultiplier_Long: float = 60000000000000000000 / 10**30  
    minCollateralFactorForOpenInterestMultiplier_Short: float = 60000000000000000000 / 10**30  
    minCollateralFactor: float = 5000000000000000000000000000 / 10**30  # 0.005
    minCollateralUsd: float = 1000000000000000000000000000000 / 10**30  # 1 
    minPositionSizeUsd: float = 1000000000000000000000000000000 / 10**30  # 1 
    maxPositionImpactFactorForLiquidation: float = 0  # MAX_POSITION_IMPACT_FACTOR_FOR_LIQUIDATIONS
    minCollateralFactorForLiquidation: float = 0.005


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
    openInterestLong: float  
    openInterestShort: float  
    openInterestInTokensLong: float
    openInterestInTokensShort: float
    longPrice: float
    shortPrice: float
    indexPrice: float
    virtualPositionInventory: float  
    positionImpactPoolAmount: float  # PositionImpactPoolAmountUpdated
    positionFeeFactor: float  # -> positive & negative
    positionFeeReceiverFactor: float
    borrowingFeeReceiverFactor: float
    cumulativeBorrowingFactorLong: float  # CumulativeBorrowingFactorUpdated  
    cumulativeBorrowingFactorShort: float  # CumulativeBorrowingFactorUpdated  
    longTokenFundingFeeAmountPerSizeLong: float  # FundingFeeAmountPerSizeUpdated  
    longTokenFundingFeeAmountPerSizeShort: float  # FundingFeeAmountPerSizeUpdated  
    shortTokenFundingFeeAmountPerSizeLong: float  # FundingFeeAmountPerSizeUpdated  
    shortTokenFundingFeeAmountPerSizeShort: float  # FundingFeeAmountPerSizeUpdated  
    longTokenClaimableFundingAmountPerSizeLong: float  # ClaimableFundingAmountPerSizeUpdated   
    longTokenClaimableFundingAmountPerSizeShort: float  # ClaimableFundingAmountPerSizeUpdated  
    shortTokenClaimableFundingAmountPerSizeLong: float  # ClaimableFundingAmountPerSizeUpdated  
    shortTokenClaimableFundingAmountPerSizeShort: float  # ClaimableFundingAmountPerSizeUpdated  


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
    market: GmxV2Pool | None
    initialCollateralToken: TokenInfo | None
    swapPath: List[GmxV2Pool] = None
    orderType: OrderType = OrderType.LimitIncrease
    sizeDeltaUsd: float = 0
    initialCollateralDeltaAmount: float = 0
    # triggerPrice: float = 0
    # acceptablePrice: float = 0
    isLong: bool | None = None
    decreasePositionSwapType: DecreasePositionSwapType | None = None


@dataclass
class ExecuteOrderParams:
    order: Order
    swapPathMarkets: List[GmxV2Pool]
    market: GmxV2Pool
