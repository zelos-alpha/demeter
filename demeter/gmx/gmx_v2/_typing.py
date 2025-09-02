from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import List


@dataclass
class PoolConfig:
    longDecimal: int
    shortDecimal: int
    swapImpactExponentFactor: float = 2
    swapImpactFactorPositive: float = 200000000000000000000 / 10**30
    swapImpactFactorNegative: float = 400000000000000000000 / 10**30
    depositFeeFactorForPositiveImpact: float = 0.0005
    depositFeeFactorForNegativeImpact: float = 0.0007
    withdrawFeeFactorForPositiveImpact: float = 0.0005
    withdrawFeeFactorForNegativeImpact: float = 0.0007
    maxPnlFactorDeposit: float = 0.9
    maxPnlFactorWithdraw: float = 0.7
    positionImpactExponentFactor = 1655417464419320500000000000000 / 10 ** 30
    positionImpactFactorPositive = 34111358107691540000000 / 10 ** 30
    positionImpactFactorNegative = 40933629729229850000000 / 10 ** 30
    maxPositiveImpactFactor = 5000000000000000000000000000 / 10 ** 30  # 0.005
    maxNegativeImpactFactor = 5000000000000000000000000000 / 10 ** 30  # 0.005
    positionFeeFactorPositive = 400000000000000000000000000 / 10 ** 30  # 0.0004
    positionFeeFactorNegative = 600000000000000000000000000 / 10 ** 30  # 0.0006
    positionFeeReceiverFactor = 370000000000000000000000000000 / 10 ** 30  # 0.37
    borrowingFeeReceiverFactor = 370000000000000000000000000000 / 10 ** 30  # 0.37
    maxPnlFactorForTraderLong = 900000000000000000000000000000 / 10 ** 30  # 0.9
    maxPnlFactorForTraderShort = 900000000000000000000000000000 / 10 ** 30  # 0.9
    minCollateralFactorForOpenInterestMultiplierLong = 60000000000000000000 / 10 ** 30
    minCollateralFactorForOpenInterestMultiplierShort = 60000000000000000000 / 10 ** 30
    minCollateralFactor = 5000000000000000000000000000 / 10 ** 30  # 0.005
    minCollateralUsd = 1000000000000000000000000000000 / 10 ** 30  # 1
    minPositionSizeUsd = 1000000000000000000000000000000 / 10 ** 30  # 1


"""
    function swapImpactExponentFactorKey(address market) external pure returns (bytes32) {
        bytes32 SWAP_IMPACT_EXPONENT_FACTOR = keccak256(abi.encode("SWAP_IMPACT_EXPONENT_FACTOR"));
        return keccak256(abi.encode(SWAP_IMPACT_EXPONENT_FACTOR,market));
    }
    function swapImpactFactorKey(address market, bool isPositive) external pure returns (bytes32) {
        bytes32 SWAP_IMPACT_FACTOR = keccak256(abi.encode("SWAP_IMPACT_FACTOR"));
        return keccak256(abi.encode(SWAP_IMPACT_FACTOR,market,isPositive));
    }
    function depositFeeFactorKey(address market, bool forPositiveImpact) external pure returns (bytes32) {
        return keccak256(abi.encode(keccak256(abi.encode("DEPOSIT_FEE_FACTOR")),market,forPositiveImpact));
    }
    function positionImpactExponentFactorKey(address market) internal pure returns (bytes32) {
        return keccak256(abi.encode(
            POSITION_IMPACT_EXPONENT_FACTOR,
            market
        ));
    }
    function positionImpactFactorKey(address market, bool isPositive) internal pure returns (bytes32) {
        return keccak256(abi.encode(
            POSITION_IMPACT_FACTOR,
            market,
            isPositive
        ));
    }
    function maxPositionImpactFactorKey(address market, bool isPositive) internal pure returns (bytes32) {
        return keccak256(abi.encode(
            MAX_POSITION_IMPACT_FACTOR,
            market,
            isPositive
        ));
    }
    function positionFeeFactorKey(address market, bool forPositiveImpact) internal pure returns (bytes32) {
        return keccak256(abi.encode(
            POSITION_FEE_FACTOR,
            market,
            forPositiveImpact
        ));
    }
    function cumulativeBorrowingFactorKey(address market, bool isLong) internal pure returns (bytes32) {
        return keccak256(abi.encode(
            CUMULATIVE_BORROWING_FACTOR,
            market,
            isLong
        ));
    }
    function fundingFeeAmountPerSizeKey(address market, address collateralToken, bool isLong) internal pure returns (bytes32) {
        return keccak256(abi.encode(
            FUNDING_FEE_AMOUNT_PER_SIZE,
            market,
            collateralToken,
            isLong
        ));
    }
    function claimableFundingAmountPerSizeKey(address market, address collateralToken, bool isLong) internal pure returns (bytes32) {
        return keccak256(abi.encode(
            CLAIMABLE_FUNDING_AMOUNT_PER_SIZE,
            market,
            collateralToken,
            isLong
        ));
    }
    function maxPnlFactorKey(bytes32 pnlFactorType, address market, bool isLong) internal pure returns (bytes32) {
        return keccak256(abi.encode(
            MAX_PNL_FACTOR,
            pnlFactorType,
            market,
            isLong
        ));
    }
    function minCollateralFactorForOpenInterestMultiplierKey(address market, bool isLong) internal pure returns (bytes32) {
       return keccak256(abi.encode(
           MIN_COLLATERAL_FACTOR_FOR_OPEN_INTEREST_MULTIPLIER,
           market,
           isLong
       ));
   }
   function minCollateralFactorKey(address market) internal pure returns (bytes32) {
       return keccak256(abi.encode(
           MIN_COLLATERAL_FACTOR,
           market
       ));
   }
"""


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
    pendingPnl:float  # pnl caused by open interest
    realizedPnl:float  # pnl for decreased position
    realizedProfit:float  # pnl + fee + priceImpact
    openInterestLong: float
    openInterestShort: float
    openInterestInTokensLong: float
    openInterestInTokensShort: float
    longPrice: float
    shortPrice: float
    indexPrice: float
    # positionImpactExponentFactor: float
    # positionImpactFactorPositive: float
    # positionImpactFactorNegative: float
    virtualInventoryForPositions: float  # VirtualPositionInventoryUpdated
    positionImpactPoolAmount: float  # PositionImpactPoolAmountUpdated
    maxPositiveImpactFactor: float
    maxNegativeImpactFactor: float
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
    maxPnlFactorForTraderLong: float
    maxPnlFactorForTraderShort: float
    minCollateralFactorForOpenInterestMultiplierLong: float
    minCollateralFactorForOpenInterestMultiplierShort: float
    minCollateralFactor: float
    minCollateralUsd: float
    minPositionSizeUsd: float


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


@dataclass
class Market:
    marketToken: str = ''
    indexToken: str = ''
    longToken: str = ''
    shortToken: str = ''


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
    market: str
    initialCollateralToken: str
    swapPath: List
    orderType: OrderType
    sizeDeltaUsd: float
    initialCollateralDeltaAmount: float
    triggerPrice: float
    acceptablePrice: float
    isLong: bool
    decreasePositionSwapType: DecreasePositionSwapType


@dataclass
class ExecuteOrderParams:
    order: Order = None
    swapPathMarkets: List = None
    market: Market = None
