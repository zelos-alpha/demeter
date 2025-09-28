from dataclasses import dataclass
from .MarketUtils import MarketUtils
from .Position import Position
from ._typing import GmxV2PoolStatus, PoolConfig
from .utils import PricingUtils
from .._typing2 import GmxV2Pool


@dataclass
class GetPositionFeesParams:
    position: Position
    collateralTokenPrice: float
    forPositiveImpact: bool
    sizeDeltaUsd: float
    isLiquidation: bool


@dataclass
class PositionFundingFees:
    fundingFeeAmount: float = 0
    claimableLongTokenAmount: float = 0
    claimableShortTokenAmount: float = 0
    latestFundingFeeAmountPerSize: float = 0
    latestLongTokenClaimableFundingAmountPerSize: float = 0
    latestShortTokenClaimableFundingAmountPerSize: float = 0


@dataclass
class PositionBorrowingFees:
    borrowingFeeUsd: float = 0
    borrowingFeeAmount: float = 0
    borrowingFeeReceiverFactor: float = 0
    borrowingFeeAmountForFeeReceiver: float = 0


@dataclass
class PositionLiquidationFees:
    liquidationFeeUsd: float = 0
    liquidationFeeAmount: float = 0
    liquidationFeeReceiverFactor: float = 0
    liquidationFeeAmountForFeeReceiver: float = 0


@dataclass
class PositionFees:
    funding: PositionFundingFees = None
    borrowing: PositionBorrowingFees = None
    liquidation: PositionLiquidationFees = None
    collateralTokenPrice: float = 0
    positionFeeAmount: float = 0
    protocolFeeAmount: float = 0
    feeReceiverAmount: float = 0
    feeAmountForPool: float = 0
    positionFeeAmountForPool: float = 0
    totalCostAmountExcludingFunding: float = 0
    totalCostAmount: float = 0
    totalDiscountAmount: float = 0
    positionFeeFactor: float = 0.0004  # todo no
    positionFeeReceiverFactor: float = 0.37  # todo no


@dataclass
class GetPriceImpactUsdParams:
    isLong: bool
    usdDelta: float


@dataclass
class OpenInterestParams:
    longOpenInterest: float
    shortOpenInterest: float
    nextLongOpenInterest: float
    nextShortOpenInterest: float


class PositionPricingUtils:
    @staticmethod
    def getPriceImpactUsd(params: GetPriceImpactUsdParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        openInterestParams = PositionPricingUtils.getNextOpenInterest(params, pool_status)
        priceImpactUsd = PositionPricingUtils._getPriceImpactUsd(openInterestParams, pool_status, pool_config)
        if priceImpactUsd >= 0:
            return priceImpactUsd
        virtualInventory = pool_status.virtualInventoryForPositions
        if virtualInventory is None:
            return priceImpactUsd
        openInterestParamsForVirtualInventory = PositionPricingUtils.getNextOpenInterestForVirtualInventory(virtualInventory, params)
        priceImpactUsdForVirtualInventory = PositionPricingUtils._getPriceImpactUsd(openInterestParamsForVirtualInventory, pool_status, pool_config)
        return priceImpactUsdForVirtualInventory if priceImpactUsdForVirtualInventory < priceImpactUsd else priceImpactUsd

    @staticmethod
    def getNextOpenInterestForVirtualInventory(virtualInventory: int, params: GetPriceImpactUsdParams):
        longOpenInterest, shortOpenInterest = 0, 0
        if virtualInventory > 0:
            shortOpenInterest = virtualInventory
        else:
            longOpenInterest = (-virtualInventory)
        if params.usdDelta < 0:
            offset = (-params.usdDelta)
            longOpenInterest += offset
            shortOpenInterest += offset
        return PositionPricingUtils.getNextOpenInterestParams(params, longOpenInterest, shortOpenInterest)

    @staticmethod
    def _getPriceImpactUsd(openInterestParams: OpenInterestParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        initialDiffUsd = abs(openInterestParams.longOpenInterest - openInterestParams.shortOpenInterest)
        nextDiffUsd = abs(openInterestParams.nextLongOpenInterest - openInterestParams.nextShortOpenInterest)

        isSameSideRebalance = (openInterestParams.longOpenInterest <= openInterestParams.shortOpenInterest) == (openInterestParams.nextLongOpenInterest <= openInterestParams.nextShortOpenInterest)
        impactExponentFactor = pool_config.positionImpactExponentFactor
        if isSameSideRebalance:
            hasPositiveImpact = (nextDiffUsd < initialDiffUsd)
            impactFactor = MarketUtils.getAdjustedPositionImpactFactor(hasPositiveImpact, pool_status, pool_config)
            return PricingUtils.getPriceImpactUsdForSameSideRebalance(
                initialDiffUsd, nextDiffUsd, impactFactor, impactExponentFactor
            )
        # initialDiffUsd 659350605479346732745873570369275889 = 659350.6054793467
        # nextDiffUsd 663797116269074703175203868873936389 = 663797.1162690747
        # impactFactor 40933629729229850000000 = 4.093362972922985e-08
        # impactExponentFactor 1655417464419320500000000000000 = 1.6554174644193205
        # 175.8519499036393
        else:
            positiveImpactFactor, negativeImpactFactor = MarketUtils.getAdjustedPositionImpactFactors(pool_status, pool_config)
            return PricingUtils.getPriceImpactUsdForCrossoverRebalance(
                initialDiffUsd,
                nextDiffUsd,
                positiveImpactFactor,
                negativeImpactFactor,
                impactExponentFactor,
            )

    @staticmethod
    def getNextOpenInterest(params: GetPriceImpactUsdParams, pool_status: GmxV2PoolStatus):
        longOpenInterest = pool_status.openInterestLong
        shortOpenInterest = pool_status.openInterestShort
        return PositionPricingUtils.getNextOpenInterestParams(params, longOpenInterest, shortOpenInterest)

    @staticmethod
    def getNextOpenInterestParams(params: GetPriceImpactUsdParams, longOpenInterest: float, shortOpenInterest: float):
        nextLongOpenInterest = longOpenInterest
        nextShortOpenInterest = shortOpenInterest
        if params.isLong:
            nextLongOpenInterest = longOpenInterest + params.usdDelta
        else:
            nextShortOpenInterest = shortOpenInterest + params.usdDelta
        openInterestParams = OpenInterestParams(
            longOpenInterest,
            shortOpenInterest,
            nextLongOpenInterest,
            nextShortOpenInterest
        )
        return openInterestParams

    @staticmethod
    def getPositionFees(params: GetPositionFeesParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig, pool: GmxV2Pool) -> PositionFees:
        fees = PositionPricingUtils.getPositionFeesAfterReferral(
            forPositiveImpact=params.forPositiveImpact,
            collateralTokenPrice=params.collateralTokenPrice,
            sizeDeltaUsd=params.sizeDeltaUsd,
            pool_status=pool_status,
            pool_config=pool_config
        )

        borrowingFeeUsd = MarketUtils.getBorrowingFees(params.position, pool_status)
        fees.borrowing = PositionPricingUtils.getBorrowingFees(params.collateralTokenPrice, borrowingFeeUsd, pool_status, pool_config)

        fees.feeAmountForPool = fees.positionFeeAmountForPool + fees.borrowing.borrowingFeeAmount - fees.borrowing.borrowingFeeAmountForFeeReceiver
        fees.feeReceiverAmount += fees.borrowing.borrowingFeeAmountForFeeReceiver
        fees.funding = PositionFundingFees()
        fees.funding.latestFundingFeeAmountPerSize = MarketUtils.getFundingFeeAmountPerSize(params.position.collateralToken, params.position.isLong, pool, pool_status)
        fees.funding.latestLongTokenClaimableFundingAmountPerSize = MarketUtils.getClaimableFundingAmountPerSize(pool.long_token, params.position.isLong, pool, pool_status)
        fees.funding.latestShortTokenClaimableFundingAmountPerSize = MarketUtils.getClaimableFundingAmountPerSize(pool.short_token, params.position.isLong, pool, pool_status)
        fees.funding = PositionPricingUtils.getFundingFees(fees.funding, params.position)
        fees.totalCostAmountExcludingFunding = fees.positionFeeAmount + fees.borrowing.borrowingFeeAmount
        fees.totalCostAmount = fees.totalCostAmountExcludingFunding + fees.funding.fundingFeeAmount
        return fees

    @staticmethod
    def getPositionFeesAfterReferral(
            forPositiveImpact: bool,
            collateralTokenPrice: float,
            sizeDeltaUsd: float,
            pool_status: GmxV2PoolStatus,
            pool_config: PoolConfig) -> PositionFees:
        fees = PositionFees()
        fees.collateralTokenPrice = collateralTokenPrice
        fees.positionFeeFactor = pool_config.positionFeeFactorPositive if forPositiveImpact else pool_config.positionFeeFactorNegative
        fees.positionFeeAmount = sizeDeltaUsd * fees.positionFeeFactor / collateralTokenPrice
        fees.protocolFeeAmount = fees.positionFeeAmount
        fees.positionFeeReceiverFactor = pool_config.positionFeeReceiverFactor
        fees.feeReceiverAmount = fees.protocolFeeAmount * fees.positionFeeReceiverFactor
        fees.positionFeeAmountForPool = fees.protocolFeeAmount - fees.feeReceiverAmount
        return fees

    @staticmethod
    def getBorrowingFees(collateralTokenPrice, borrowingFeeUsd, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        # read from csv
        borrowingFeeAmount = borrowingFeeUsd / collateralTokenPrice
        borrowingFeeReceiverFactor = pool_config.borrowingFeeReceiverFactor  # todo from csv data BORROWING_FEE_RECEIVER_FACTOR
        borrowingFees = PositionBorrowingFees(
            borrowingFeeUsd=borrowingFeeUsd,
            borrowingFeeAmount=borrowingFeeAmount,
            borrowingFeeReceiverFactor=borrowingFeeReceiverFactor,
            borrowingFeeAmountForFeeReceiver=borrowingFeeAmount * borrowingFeeReceiverFactor
        )
        return borrowingFees

    @staticmethod
    def getFundingFees(fundingFees: PositionFundingFees, position: Position):
        # read from csv
        fundingFees.fundingFeeAmount = MarketUtils.getFundingAmount(
            fundingFees.latestFundingFeeAmountPerSize,
            position.fundingFeeAmountPerSize,
            position.sizeInUsd
        )
        fundingFees.claimableLongTokenAmount = MarketUtils.getFundingAmount(
            fundingFees.latestLongTokenClaimableFundingAmountPerSize,
            position.longTokenClaimableFundingAmountPerSize,
            position.sizeInUsd,
        )
        fundingFees.claimableShortTokenAmount = MarketUtils.getFundingAmount(
            fundingFees.latestShortTokenClaimableFundingAmountPerSize,
            position.shortTokenClaimableFundingAmountPerSize,
            position.sizeInUsd,
        )
        return fundingFees
