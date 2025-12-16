from dataclasses import dataclass
from ..position.Position import Position
from ..pricing.PositionPricingUtils import PositionFees, GetPositionFeesParams, PositionPricingUtils
from ..position.PositionUtils import UpdatePositionParams, PositionUtils
from .._typing import (
    Prices,
    Order,
    GmxV2PoolStatus,
    PoolConfig,
    GetNextFundingAmountPerSizeResult,
    GetNextFundingAmountPerSizeCache,
    GetNextFundingFactorPerSecondCache,
    FundingConfigCache,
    FundingRateChangeType,
    GmxV2Pool,
    PoolData,
)
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
    ):

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
        # TODO borrow fees
        # pendingBorrowingFeeUsd = MarketUtils.getNextBorrowingFees(
        #     pending_borrowing_time, positionInfo.position, cache.market, prices, pool_status, pool_config
        # )
        # positionInfo.fees.borrowing = PositionPricingUtils.getBorrowingFees(
        #     cache.collateralTokenPrice, pendingBorrowingFeeUsd, pool_status, pool_config
        # )
        # TODO funding fees
        # nextFundingAmountResult = ReaderPositionUtils.getNextFundingAmountPerSize(market, prices, pool_status)
        # positionInfo.fees.funding.latestFundingFeeAmountPerSize = MarketUtils.getFundingFeeAmountPerSize(positionInfo.position.collateralToken, positionInfo.position.isLong, pool, pool_status)
        # positionInfo.fees.funding.latestLongTokenClaimableFundingAmountPerSize = MarketUtils.getClaimableFundingAmountPerSize(cache.market.longToken, positionInfo.position.isLong, pool, pool_status)
        # positionInfo.fees.funding.latestShortTokenClaimableFundingAmountPerSize = MarketUtils.getClaimableFundingAmountPerSize(cache.market.shortToken, positionInfo.position.isLong, pool, pool_status)
        #
        # multiplier = 2 if cache.market.longToken == cache.market.shortToken else 1
        #
        # if positionInfo.position.isLong:
        #     positionInfo.fees.funding.latestLongTokenClaimableFundingAmountPerSize += nextFundingAmountResult.claimableFundingAmountPerSizeDelta.long.longToken * multiplier
        #     positionInfo.fees.funding.latestShortTokenClaimableFundingAmountPerSize += nextFundingAmountResult.claimableFundingAmountPerSizeDelta.long.shortToken * multiplier
        #     if positionInfo.position.collateralToken == cache.market.longToken:
        #         positionInfo.fees.funding.latestFundingFeeAmountPerSize += nextFundingAmountResult.fundingFeeAmountPerSizeDelta.long.longToken * multiplier
        #     else:
        #         positionInfo.fees.funding.latestFundingFeeAmountPerSize += nextFundingAmountResult.fundingFeeAmountPerSizeDelta.long.shortToken * multiplier
        # else:
        #     positionInfo.fees.funding.latestLongTokenClaimableFundingAmountPerSize += nextFundingAmountResult.claimableFundingAmountPerSizeDelta.short.longToken * multiplier
        #     positionInfo.fees.funding.latestShortTokenClaimableFundingAmountPerSize += nextFundingAmountResult.claimableFundingAmountPerSizeDelta.short.shortToken * multiplier
        #     if positionInfo.position.collateralToken == cache.market.longToken:
        #         positionInfo.fees.funding.latestFundingFeeAmountPerSize += nextFundingAmountResult.fundingFeeAmountPerSizeDelta.short.longToken * multiplier
        #     else:
        #         positionInfo.fees.funding.latestFundingFeeAmountPerSize += nextFundingAmountResult.fundingFeeAmountPerSizeDelta.short.shortToken * multiplier
        #
        # positionInfo.fees.funding = PositionPricingUtils.getFundingFees(positionInfo.fees.funding, positionInfo.position)

        positionInfo.basePnlUsd, positionInfo.uncappedBasePnlUsd, _ = PositionUtils.getPositionPnlUsd(
            prices, positionInfo.position, sizeDeltaUsd, pool_data
        )
        positionInfo.pnlAfterPriceImpactUsd = positionInfo.executionPriceResult.priceImpactUsd + positionInfo.basePnlUsd

        positionInfo.fees.totalCostAmountExcludingFunding = (
            positionInfo.fees.positionFeeAmount
            + positionInfo.fees.borrowing.borrowingFeeAmount
            - positionInfo.fees.totalDiscountAmount
        )
        positionInfo.fees.totalCostAmount = (
            positionInfo.fees.totalCostAmountExcludingFunding + positionInfo.fees.funding.fundingFeeAmount
        )
        return positionInfo

    @staticmethod
    def getNextFundingAmountPerSize(market, prices, pool_status: GmxV2PoolStatus):
        result = GetNextFundingAmountPerSizeResult()
        cache = GetNextFundingAmountPerSizeCache()
        divisor = 2 if market.longToken == market.shortToken else 1
        cache.longOpenInterest = MarketUtils.getOpenInterest(market, True, pool_status)
        cache.shortOpenInterest = MarketUtils.getOpenInterest(market, False, pool_status)
        if cache.longOpenInterest == 0 or cache.shortOpenInterest == 0:
            return result
        cache.durationInSeconds = 0  # getSecondsSinceFundingUpdated()  # todo 传进来
        cache.sizeOfLargerSide = (
            cache.longOpenInterest if cache.longOpenInterest > cache.shortOpenInterest else cache.shortOpenInterest
        )
        result.fundingFactorPerSecond, result.longsPayShorts, result.nextSavedFundingFactorPerSecond = (
            ReaderPositionUtils.getNextFundingFactorPerSecond()
        )
        cache.fundingUsd = cache.sizeOfLargerSide * cache.durationInSeconds * result.fundingFactorPerSecond  # todo
        cache.fundingUsd = cache.fundingUsd / divisor
        if result.longsPayShorts:
            cache.fundingUsdForLongCollateral = (
                cache.fundingUsd * cache.openInterest.long.longToken / cache.longOpenInterest
            )
            cache.fundingUsdForShortCollateral = (
                cache.fundingUsd * cache.openInterest.long.shortToken / cache.longOpenInterest
            )
        else:
            cache.fundingUsdForLongCollateral = (
                cache.fundingUsd * cache.openInterest.short.longToken / cache.shortOpenInterest
            )
            cache.fundingUsdForShortCollateral = (
                cache.fundingUsd * cache.openInterest.short.shortToken / cache.shortOpenInterest
            )

        if result.longsPayShorts:
            result.fundingFeeAmountPerSizeDelta.long.longToken = MarketUtils.getFundingAmountPerSizeDelta(
                cache.fundingUsdForLongCollateral, cache.openInterest.long.longToken, prices.longTokenPrice.max
            )
            result.fundingFeeAmountPerSizeDelta.long.shortToken = MarketUtils.getFundingAmountPerSizeDelta(
                cache.fundingUsdForShortCollateral, cache.openInterest.long.shortToken, prices.shortTokenPrice.max
            )
            result.claimableFundingAmountPerSizeDelta.short.longToken = MarketUtils.getFundingAmountPerSizeDelta(
                cache.fundingUsdForLongCollateral, cache.shortOpenInterest, prices.longTokenPrice.max
            )
            result.claimableFundingAmountPerSizeDelta.short.shortToken = MarketUtils.getFundingAmountPerSizeDelta(
                cache.fundingUsdForShortCollateral, cache.shortOpenInterest, prices.shortTokenPrice.max
            )
        else:
            result.fundingFeeAmountPerSizeDelta.short.longToken = MarketUtils.getFundingAmountPerSizeDelta(
                cache.fundingUsdForLongCollateral, cache.openInterest.short.longToken, prices.longTokenPrice.max
            )
            result.fundingFeeAmountPerSizeDelta.short.shortToken = MarketUtils.getFundingAmountPerSizeDelta(
                cache.fundingUsdForShortCollateral, cache.openInterest.short.shortToken, prices.shortTokenPrice.max
            )
            result.claimableFundingAmountPerSizeDelta.long.longToken = MarketUtils.getFundingAmountPerSizeDelta(
                cache.fundingUsdForLongCollateral, cache.longOpenInterest, prices.longTokenPrice.max
            )
            result.claimableFundingAmountPerSizeDelta.long.shortToken = MarketUtils.getFundingAmountPerSizeDelta(
                cache.fundingUsdForShortCollateral, cache.longOpenInterest, prices.shortTokenPrice.max
            )
        return result

    @staticmethod
    def getNextFundingFactorPerSecond(longOpenInterest, shortOpenInterest, durationInSeconds, pool_config: PoolConfig):
        cache = GetNextFundingFactorPerSecondCache()
        cache.diffUsd = (
            longOpenInterest - shortOpenInterest
            if longOpenInterest > shortOpenInterest
            else shortOpenInterest - longOpenInterest
        )
        cache.totalOpenInterest = longOpenInterest + shortOpenInterest
        configCache = FundingConfigCache()
        configCache.fundingIncreaseFactorPerSecond = pool_config.fundingIncreaseFactorPerSecond  # todo from config
        if cache.diffUsd == 0 and configCache.fundingIncreaseFactorPerSecond == 0:
            return 0, True, 0
        cache.fundingExponentFactor = pool_config.fundingExponentFactor
        cache.diffUsdAfterExponent = cache.diffUsd**cache.fundingExponentFactor
        cache.diffUsdToOpenInterestFactor = cache.diffUsdAfterExponent / cache.totalOpenInterest
        if configCache.fundingIncreaseFactorPerSecond == 0:
            cache.fundingFactor = pool_config.fundingFactor
            maxFundingFactorPerSecond = pool_config.maxFundingFactorPerSecond
            fundingFactorPerSecond = cache.diffUsdToOpenInterestFactor * cache.fundingFactor
            if fundingFactorPerSecond > maxFundingFactorPerSecond:
                fundingFactorPerSecond = maxFundingFactorPerSecond
                return fundingFactorPerSecond, longOpenInterest > shortOpenInterest, 0
        cache.savedFundingFactorPerSecond = getSavedFundingFactorPerSecond()  # todo
        cache.savedFundingFactorPerSecondMagnitude = abs(cache.savedFundingFactorPerSecond)
        configCache.thresholdForStableFunding = pool_config.thresholdForStableFunding
        configCache.thresholdForDecreaseFunding = pool_config.thresholdForDecreaseFunding
        cache.nextSavedFundingFactorPerSecond = cache.savedFundingFactorPerSecond
        fundingRateChangeType = FundingRateChangeType.NoChange
        isSkewTheSameDirectionAsFunding = (
            cache.savedFundingFactorPerSecond > 0 and longOpenInterest > shortOpenInterest
        ) or (cache.savedFundingFactorPerSecond < 0 and shortOpenInterest > longOpenInterest)
        if isSkewTheSameDirectionAsFunding:
            if cache.diffUsdToOpenInterestFactor > configCache.thresholdForStableFunding:
                fundingRateChangeType = FundingRateChangeType.Increase
            elif cache.diffUsdToOpenInterestFactor < configCache.thresholdForDecreaseFunding:
                fundingRateChangeType = FundingRateChangeType.Decrease
        else:
            fundingRateChangeType = FundingRateChangeType.Increase

        if fundingRateChangeType == FundingRateChangeType.Increase:
            increaseValue = (
                cache.diffUsdToOpenInterestFactor * configCache.fundingIncreaseFactorPerSecond * durationInSeconds
            )
            if longOpenInterest < shortOpenInterest:
                increaseValue = -increaseValue
            cache.nextSavedFundingFactorPerSecond = cache.savedFundingFactorPerSecond + increaseValue

        if fundingRateChangeType == FundingRateChangeType.Decrease and cache.savedFundingFactorPerSecondMagnitude != 0:
            configCache.fundingDecreaseFactorPerSecond = pool_config.fundingDecreaseFactorPerSecond
            decreaseValue = configCache.fundingDecreaseFactorPerSecond * durationInSeconds
            if cache.savedFundingFactorPerSecondMagnitude <= decreaseValue:
                cache.nextSavedFundingFactorPerSecond = (
                    cache.savedFundingFactorPerSecond / cache.savedFundingFactorPerSecondMagnitude
                )
            else:
                sign = cache.savedFundingFactorPerSecond / cache.savedFundingFactorPerSecondMagnitude
                cache.nextSavedFundingFactorPerSecond = (
                    cache.savedFundingFactorPerSecondMagnitude - decreaseValue
                ) * sign

        configCache.minFundingFactorPerSecond = pool_config.minFundingFactorPerSecond
        configCache.maxFundingFactorPerSecond = pool_config.maxFundingFactorPerSecond

        cache.nextSavedFundingFactorPerSecond = ReaderPositionUtils.boundMagnitude(
            cache.nextSavedFundingFactorPerSecond, 0, configCache.maxFundingFactorPerSecond
        )
        cache.nextSavedFundingFactorPerSecondWithMinBound = ReaderPositionUtils.boundMagnitude(
            cache.nextSavedFundingFactorPerSecond,
            configCache.minFundingFactorPerSecond,
            configCache.maxFundingFactorPerSecond,
        )

        return (
            abs(cache.nextSavedFundingFactorPerSecondWithMinBound),
            cache.nextSavedFundingFactorPerSecondWithMinBound > 0,
            cache.nextSavedFundingFactorPerSecond,
        )

    @staticmethod
    def boundMagnitude(_value, min, max):
        magnitude = abs(_value)
        if magnitude < min:
            magnitude = min
        if magnitude > max:
            magnitude = max
        sign = _value / abs(_value)
        return magnitude * sign

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
                acceptablePrice=99999999999999999999 if shouldExecutionPriceBeSmaller else 0,
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
