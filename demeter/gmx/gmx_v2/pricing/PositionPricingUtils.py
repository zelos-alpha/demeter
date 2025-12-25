from dataclasses import dataclass

from demeter import TokenInfo
from ..market.MarketUtils import MarketUtils
from ..position.Position import Position
from .._typing import GmxV2PoolStatus, PoolConfig, GmxV2Pool, PoolData
from ..utils import PricingUtils, Calc


@dataclass
class GetPositionFeesParams:
    position: Position
    collateralTokenPrice: float
    balanceWasImproved: bool
    longToken: TokenInfo
    shortToken: TokenInfo
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
    # borrowingFeeReceiverFactor: float = 0
    # borrowingFeeAmountForFeeReceiver: float = 0


@dataclass
class PositionLiquidationFees:
    liquidationFeeUsd: float = 0
    liquidationFeeAmount: float = 0
    # liquidationFeeReceiverFactor: float = 0
    # liquidationFeeAmountForFeeReceiver: float = 0


@dataclass
class PositionFees:
    funding: PositionFundingFees = None
    borrowing: PositionBorrowingFees = None
    liquidation: PositionLiquidationFees = None
    collateralTokenPrice: float = 0
    positionFeeFactor: float = 0
    positionFeeAmount: float = 0  # just sizeDeltaUsd * positionFeeFactor
    protocolFeeAmount: float = 0  # positionFeeAmount - discountAmount
    totalCostAmountExcludingFunding: float = 0
    totalCostAmount: float = 0


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
    def getPriceImpactUsd(params: GetPriceImpactUsdParams, pool_data: PoolData) -> tuple[float, bool]:
        # TODO: latest version have USE_OPEN_INTEREST_IN_TOKENS_FOR_BALANCE, and will require index price and sizeInTokens
        # I'm not gonna add this until they are online.
        openInterestParams: OpenInterestParams = PositionPricingUtils.getNextOpenInterest(params, pool_data)
        priceImpactUsd, balanceWasImproved = PositionPricingUtils._getPriceImpactUsd(openInterestParams, pool_data)
        # the virtual price impact calculation is skipped if the price impact
        # is positive since the action is helping to balance the pool
        #
        # in case two virtual pools are unbalanced in a different direction
        # e.g. pool0 has more longs than shorts while pool1 has less longs
        # than shorts
        # not skipping the virtual price impact calculation would lead to
        # a negative price impact for any trade on either pools and would
        # disincentivise the balancing of pools
        if priceImpactUsd >= 0:
            return priceImpactUsd, balanceWasImproved
        hasVirtualInventory, virtualInventory = MarketUtils.getVirtualInventoryForPositions(
            pool_data.market.index_token, pool_data
        )
        if not hasVirtualInventory:
            return priceImpactUsd, balanceWasImproved
        openInterestParamsForVirtualInventory: OpenInterestParams = (
            PositionPricingUtils.getNextOpenInterestForVirtualInventory(params, virtualInventory)
        )
        priceImpactUsdForVirtualInventory, balanceWasImprovedForVirtualInventory = (
            PositionPricingUtils._getPriceImpactUsd(openInterestParamsForVirtualInventory, pool_data)
        )
        if priceImpactUsdForVirtualInventory < priceImpactUsd:
            return priceImpactUsdForVirtualInventory, balanceWasImprovedForVirtualInventory
        else:
            return priceImpactUsd, balanceWasImproved

    @staticmethod
    def getNextOpenInterestForVirtualInventory(
        params: GetPriceImpactUsdParams, virtualInventory: float
    ) -> OpenInterestParams:
        longOpenInterest, shortOpenInterest = 0, 0
        if virtualInventory > 0:
            shortOpenInterest = virtualInventory
        else:
            longOpenInterest = -virtualInventory
        if params.usdDelta < 0:
            offset = -params.usdDelta
            longOpenInterest += offset
            shortOpenInterest += offset
        return PositionPricingUtils.getNextOpenInterestParams(params, longOpenInterest, shortOpenInterest)

    @staticmethod
    def _getPriceImpactUsd(openInterestParams: OpenInterestParams, pool_data: PoolData) -> tuple[float, bool]:
        initialDiffUsd = Calc.diff(openInterestParams.longOpenInterest, openInterestParams.shortOpenInterest)
        nextDiffUsd = Calc.diff(openInterestParams.nextLongOpenInterest, openInterestParams.nextShortOpenInterest)

        isSameSideRebalance = (openInterestParams.longOpenInterest <= openInterestParams.shortOpenInterest) == (
            openInterestParams.nextLongOpenInterest <= openInterestParams.nextShortOpenInterest
        )
        balanceWasImproved = nextDiffUsd < initialDiffUsd

        if isSameSideRebalance:
            impactFactor = MarketUtils.getAdjustedPositionImpactFactor(balanceWasImproved, pool_data.config)
            impactExponentFactor = MarketUtils.getAdjustedPositionImpactExponentFactor(
                balanceWasImproved, pool_data.config
            )
            return (
                PricingUtils.getPriceImpactUsdForSameSideRebalance(
                    initialDiffUsd, nextDiffUsd, impactFactor, impactExponentFactor
                ),
                balanceWasImproved,
            )
        else:
            positiveImpactFactor, negativeImpactFactor = MarketUtils.getAdjustedPositionImpactFactors(pool_data.config)
            return (
                PricingUtils.getPriceImpactUsdForCrossoverRebalance(
                    initialDiffUsd,
                    nextDiffUsd,
                    positiveImpactFactor,
                    negativeImpactFactor,
                    pool_data.config.positionImpactExponentFactor_Positive,
                    pool_data.config.positionImpactExponentFactor_Negative,
                ),
                balanceWasImproved,
            )

    @staticmethod
    def getNextOpenInterest(params: GetPriceImpactUsdParams, pool_data: PoolData) -> OpenInterestParams:
        return PositionPricingUtils.getNextOpenInterestParams(
            params, pool_data.status.openInterestLong, pool_data.status.openInterestShort
        )

    @staticmethod
    def getNextOpenInterestParams(
        params: GetPriceImpactUsdParams, longOpenInterest: float, shortOpenInterest: float
    ) -> OpenInterestParams:
        nextLongOpenInterest = longOpenInterest
        nextShortOpenInterest = shortOpenInterest
        if params.isLong:
            if params.usdDelta < 0 and -params.usdDelta > longOpenInterest:
                nextLongOpenInterest = 0
            else:
                nextLongOpenInterest = longOpenInterest + params.usdDelta
        else:
            if params.usdDelta < 0 and -params.usdDelta > shortOpenInterest:
                nextShortOpenInterest = 0
            else:
                nextShortOpenInterest = shortOpenInterest + params.usdDelta
        openInterestParams = OpenInterestParams(
            longOpenInterest, shortOpenInterest, nextLongOpenInterest, nextShortOpenInterest
        )
        return openInterestParams

    @staticmethod
    def getPositionFees(params: GetPositionFeesParams, pool_data: PoolData) -> PositionFees:
        fees: PositionFees = PositionPricingUtils.getPositionFeesAfterReferral(
            collateralTokenPrice=params.collateralTokenPrice,
            balanceWasImproved=params.balanceWasImproved,
            sizeDeltaUsd=params.sizeDeltaUsd,
            pool_data=pool_data,
        )
        borrowingFeeUsd = MarketUtils.getBorrowingFees(params.position, pool_data.status)
        fees.borrowing = PositionPricingUtils.getBorrowingFees(params.collateralTokenPrice, borrowingFeeUsd)

        if params.isLiquidation:
            fees.liquidation = PositionPricingUtils.getLiquidationFees(
                params.sizeDeltaUsd, params.collateralTokenPrice, pool_data
            )

        fees.funding = PositionFundingFees()

        fees.funding.latestFundingFeeAmountPerSize = MarketUtils.getFundingFeeAmountPerSize(
            params.position.collateralToken, params.position.isLong, pool_data
        )
        fees.funding.latestLongTokenClaimableFundingAmountPerSize = MarketUtils.getClaimableFundingAmountPerSize(
            pool_data.market.long_token, params.position.isLong, pool_data
        )
        fees.funding.latestShortTokenClaimableFundingAmountPerSize = MarketUtils.getClaimableFundingAmountPerSize(
            pool_data.market.short_token, params.position.isLong, pool_data
        )
        fees.funding = PositionPricingUtils.getFundingFees(fees.funding, params.position)
        fees.totalCostAmountExcludingFunding = (
            fees.positionFeeAmount + fees.borrowing.borrowingFeeAmount + fees.liquidation.liquidationFeeAmount
        )
        fees.totalCostAmount = fees.totalCostAmountExcludingFunding + fees.funding.fundingFeeAmount
        return fees

    @staticmethod
    def getPositionFeesAfterReferral(
        collateralTokenPrice: float, balanceWasImproved: bool, sizeDeltaUsd: float, pool_data: PoolData
    ) -> PositionFees:
        fees = PositionFees()
        fees.borrowing = PositionBorrowingFees()
        fees.liquidation = PositionLiquidationFees()
        fees.collateralTokenPrice = collateralTokenPrice
        # skip referral

        # note that since it is possible to incur both positive and negative price impact values
        # and the negative price impact factor may be larger than the positive impact factor
        # it is possible for the balance to be improved overall but for the price impact to still be negative
        # in this case the fee factor for the **positive** price impact would be charged for the case when priceImpactUsd is negative and balanceWasImproved
        # a user could split the order into two, to incur a smaller fee, reducing the fee through this should not be a large issue

        fees.positionFeeFactor = (
            pool_data.config.positionFeeFactor_Positive
            if balanceWasImproved
            else pool_data.config.positionFeeFactor_Negative
        )
        fees.positionFeeAmount = sizeDeltaUsd * fees.positionFeeFactor / collateralTokenPrice

        # skip pro tiers

        # skip referralCode

        fees.protocolFeeAmount = fees.positionFeeAmount  # - fees.totalDiscountAmount

        return fees

    @staticmethod
    def getBorrowingFees(collateralTokenPrice, borrowingFeeUsd) -> PositionBorrowingFees:

        borrowingFees = PositionBorrowingFees(
            borrowingFeeUsd=borrowingFeeUsd,
            borrowingFeeAmount=borrowingFeeUsd / collateralTokenPrice,
            # borrowingFeeReceiverFactor=borrowingFeeReceiverFactor,
            # borrowingFeeAmountForFeeReceiver=borrowingFeeAmount * borrowingFeeReceiverFactor,
        )
        return borrowingFees

    @staticmethod
    def getFundingFees(fundingFees: PositionFundingFees, position: Position):
        fundingFees.fundingFeeAmount = MarketUtils.getFundingAmount(
            fundingFees.latestFundingFeeAmountPerSize, position.fundingFeeAmountPerSize, position.sizeInUsd
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

    @staticmethod
    def getLiquidationFees(
        sizeInUsd: float, collateralTokenPrice: float, pool_data: PoolData
    ) -> PositionLiquidationFees:
        liquidationFees = PositionLiquidationFees()
        liquidationFeeFactor = pool_data.config.liquidationFeeFactor
        if liquidationFeeFactor == 0:
            return liquidationFees

        liquidationFees.liquidationFeeUsd = sizeInUsd * liquidationFeeFactor
        liquidationFees.liquidationFeeAmount = liquidationFees.liquidationFeeUsd / collateralTokenPrice
        return liquidationFees
