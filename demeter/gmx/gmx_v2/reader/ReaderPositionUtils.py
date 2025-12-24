from dataclasses import dataclass
from ..position.Position import Position
from ..pricing.PositionPricingUtils import PositionFees, GetPositionFeesParams, PositionPricingUtils
from ..position.PositionUtils import UpdatePositionParams, PositionUtils
from .._typing import Order, PoolData
from ..market.MarketUtils import MarketUtils, MarketPrices


@dataclass
class ExecutionPriceResult:
    priceImpactUsd: float = 0
    executionPrice: float = 0
    balanceWasImproved: bool = False
    proportionalPendingImpactUsd: float = 0
    totalImpactUsd: float = 0
    priceImpactDiffUsd: float = 0


@dataclass
class PositionInfo:
    position: Position = None
    fees: PositionFees = None
    executionPriceResult: ExecutionPriceResult = None
    basePnlUsd: float = 0
    pnlAfterPriceImpactUsd: float = 0


class ReaderPositionUtils:

    @staticmethod
    def getPositionInfo(
        position: Position,
        sizeDeltaUsd: float,
        usePositionSizeAsSizeDeltaUsd: bool,
        pool_data: PoolData,
    ) -> PositionInfo:

        prices = MarketPrices(
            indexTokenPrice=pool_data.status.indexPrice,
            longTokenPrice=pool_data.status.longPrice,
            shortTokenPrice=pool_data.status.shortPrice,
        )

        positionInfo = PositionInfo()
        positionInfo.position = position
        market = pool_data.market
        collateralTokenPrice = MarketUtils.getCachedTokenPrice(positionInfo.position.collateralToken, market, prices)
        if usePositionSizeAsSizeDeltaUsd:
            sizeDeltaUsd = positionInfo.position.sizeInUsd

        positionInfo.executionPriceResult = ReaderPositionUtils.getExecutionPrice(
            prices,
            positionInfo.position.sizeInUsd,
            positionInfo.position.sizeInTokens,
            -sizeDeltaUsd,
            positionInfo.position.pendingImpactAmount,
            positionInfo.position.isLong,
            pool_data,
        )

        getPositionFeesParams = GetPositionFeesParams(
            position=positionInfo.position,
            collateralTokenPrice=collateralTokenPrice,
            balanceWasImproved=positionInfo.executionPriceResult.priceImpactUsd > 0,
            longToken=market.long_token,
            shortToken=market.short_token,
            sizeDeltaUsd=sizeDeltaUsd,
            isLiquidation=False,
        )

        positionInfo.fees = PositionPricingUtils.getPositionFees(getPositionFeesParams, pool_data)

        # borrowing and funding fees need to be overwritten with pending values otherwise they
        # would be using storage values that have not yet been updated
        pendingBorrowingFeeUsd = MarketUtils.getNextBorrowingFees(positionInfo.position, pool_data.status)
        positionInfo.fees.borrowing = PositionPricingUtils.getBorrowingFees(
            collateralTokenPrice, pendingBorrowingFeeUsd
        )
        # Funding fee
        positionInfo.fees.funding.latestFundingFeeAmountPerSize = MarketUtils.getFundingFeeAmountPerSize(
            positionInfo.position.collateralToken, positionInfo.position.isLong, pool_data
        )
        positionInfo.fees.funding.latestLongTokenClaimableFundingAmountPerSize = (
            MarketUtils.getClaimableFundingAmountPerSize(market.long_token, positionInfo.position.isLong, pool_data)
        )
        positionInfo.fees.funding.latestShortTokenClaimableFundingAmountPerSize = (
            MarketUtils.getClaimableFundingAmountPerSize(market.short_token, positionInfo.position.isLong, pool_data)
        )

        positionInfo.fees.funding = PositionPricingUtils.getFundingFees(
            positionInfo.fees.funding, positionInfo.position
        )

        positionInfo.basePnlUsd, positionInfo.uncappedBasePnlUsd, _ = PositionUtils.getPositionPnlUsd(
            prices, positionInfo.position, sizeDeltaUsd, pool_data
        )
        positionInfo.pnlAfterPriceImpactUsd = positionInfo.executionPriceResult.priceImpactUsd + positionInfo.basePnlUsd

        positionInfo.fees.totalCostAmountExcludingFunding = (
            positionInfo.fees.positionFeeAmount
            + positionInfo.fees.borrowing.borrowingFeeAmount
            # - positionInfo.fees.totalDiscountAmount
        )
        positionInfo.fees.totalCostAmount = (
            positionInfo.fees.totalCostAmountExcludingFunding + positionInfo.fees.funding.fundingFeeAmount
        )
        return positionInfo

    @staticmethod
    def getExecutionPrice(
        prices: MarketPrices,
        positionSizeInUsd: float,
        positionSizeInTokens: float,
        sizeDeltaUsd: float,
        pendingImpactAmount: float,
        isLong: bool,
        pool_data: PoolData,
    ):
        isIncrease = sizeDeltaUsd > 0
        shouldExecutionPriceBeSmaller = isLong if isIncrease else not isLong
        params = UpdatePositionParams(
            pool_data.market,
            Order(
                market=None,
                initialCollateralToken=None,
                sizeDeltaUsd=abs(sizeDeltaUsd),
                isLong=isLong,
            ),
            position=Position(
                market=None,
                collateralToken=None,
                sizeInUsd=positionSizeInUsd,
                sizeInTokens=positionSizeInTokens,
                isLong=isLong,
                pendingImpactAmount=pendingImpactAmount,
            ),
            claimableFundingAmount=None,
        )

        result = ExecutionPriceResult()

        if sizeDeltaUsd > 0:
            result.priceImpactUsd, _, _, result.executionPrice, result.balanceWasImproved = (
                PositionUtils.getExecutionPriceForIncrease(params, prices, pool_data)
            )
        else:
            # _, _, sizeDeltaInTokens = PositionUtils.getPositionPnlUsd(
            #     prices, params.position, params.order.sizeDeltaUsd, pool_data
            # )
            result.priceImpactUsd, result.executionPricem, result.balanceWasImproved = (
                # PositionUtils.getExecutionPriceForDecrease(params, prices.indexTokenPrice, sizeDeltaInTokens, pool_data)
                # not released yet.
                PositionUtils.getExecutionPriceForDecrease(params, prices.indexTokenPrice, pool_data)
            )
            result.proportionalPendingImpactUsd = ReaderPositionUtils._getProportionalPendingImpactValues(
                params.position.sizeInUsd,
                params.position.pendingImpactAmount,
                params.order.sizeDeltaUsd,
                prices.indexTokenPrice,
            )
            result.totalImpactUsd = result.proportionalPendingImpactUsd + result.priceImpactUsd

            if result.totalImpactUsd < 0:
                maxPriceImpactFactor = MarketUtils.getMaxPositionImpactFactor(False, pool_data)
                # convert the max price impact to the min negative value
                # e.g. if sizeDeltaUsd is 10,000 and maxPriceImpactFactor is 2%
                # then minPriceImpactUsd = -200
                minPriceImpactUsd = -params.order.sizeDeltaUsd * maxPriceImpactFactor

                # cap totalImpactUsd to the min negative value and store the difference in priceImpactDiffUsd
                # e.g. if totalImpactUsd is -500 and minPriceImpactUsd is -200
                # then set priceImpactDiffUsd to -200 - -500 = 300
                # set totalImpactUsd to -200
                if result.totalImpactUsd < minPriceImpactUsd:
                    result.priceImpactDiffUsd = minPriceImpactUsd - result.totalImpactUsd
                    result.totalImpactUsd = minPriceImpactUsd

                result.totalImpactUsd = MarketUtils.capPositiveImpactUsdByMaxPositionImpact(
                    result.totalImpactUsd, -sizeDeltaUsd, pool_data
                )
                result.totalImpactUsd = MarketUtils.capPositiveImpactUsdByPositionImpactPool(
                    prices, result.totalImpactUsd, pool_data
                )

        return result

    @staticmethod
    def _getProportionalPendingImpactValues(
        sizeInUsd: float,
        positionPendingImpactAmount: float,
        sizeDeltaUsd: float,
        indexTokenPrice: float,
    ) -> float:
        proportionalPendingImpactAmount = positionPendingImpactAmount * sizeDeltaUsd / sizeInUsd

        # minimize the positive impact, maximize the negative impact
        proportionalPendingImpactUsd = proportionalPendingImpactAmount * indexTokenPrice

        return proportionalPendingImpactUsd
