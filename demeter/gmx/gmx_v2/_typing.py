from dataclasses import dataclass
from decimal import Decimal


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
    longPrice: float
    shortPrice: float
    indexPrice: float



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
class MarketPoolValueInfo:
    poolValue: float = 0
    longPnl: float = 0
    shortPnl: float = 0
    netPnl: float = 0
    longTokenAmount: float = 0
    shortTokenAmount: float = 0
    longTokenUsd: float = 0
    shortTokenUsd: float = 0
    totalBorrowingFees: float = 0
    borrowingFeePoolFactor: float = 0
    impactPoolAmount: float = 0
