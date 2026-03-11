from dataclasses import dataclass
from .Position import Position
from .PositionPricingUtils import PositionFees, GetPositionFeesParams, PositionPricingUtils
from .PositionUtils import UpdatePositionParams, PositionUtils
from ._typing import Market, Prices, Order, GmxV2PoolStatus, PoolConfig, GetNextFundingAmountPerSizeResult, GetNextFundingAmountPerSizeCache, GetNextFundingFactorPerSecondCache, FundingConfigCache, FundingRateChangeType
from .._typing2 import GmxV2Pool
from .MarketUtils import Price, MarketUtils, MarketPrices



@dataclass
class GetPositionInfoCache:
    market: Market = None
    collateralTokenPrice: Prices = None
    pendingBorrowingFeeUsd: float = 0


@dataclass
class ExecutionPriceResult:
    priceImpactUsd: float = 0
    priceImpactDiffUsd: float = 0
    executionPrice: float = 0


@dataclass
class PositionInfo:
    position: Position = None
    fees: PositionFees = None
    executionPriceResult: ExecutionPriceResult = None
    basePnlUsd: float = 0
    pnlAfterPriceImpactUsd: float = 0


class ReaderPositionUtils:

    @staticmethod
    def getPositionInfo(pending_borrowing_time, position, collateralTokenPrice, pool_status: GmxV2PoolStatus, pool_config: PoolConfig, pool: GmxV2Pool):
        market = Market(
            indexToken=pool.index_token.address,
            longToken=pool.long_token.address,
            shortToken=pool.short_token.address
        )
        prices = MarketPrices(
            indexTokenPrice=Price(min=pool_status.indexPrice, max=pool_status.indexPrice),
            longTokenPrice=Price(min=pool_status.longPrice, max=pool_status.longPrice),
            shortTokenPrice=Price(min=pool_status.shortPrice, max=pool_status.shortPrice),
        )

        positionInfo = PositionInfo()
        cache = GetPositionInfoCache()
        positionInfo.position = position
        cache.market = market
        cache.collateralTokenPrice = collateralTokenPrice
        sizeDeltaUsd = positionInfo.position.sizeInUsd

        positionInfo.executionPriceResult = ReaderPositionUtils.getExecutionPrice(
            cache.market,
            pool_status.indexPrice,
            positionInfo.position.sizeInUsd,
            positionInfo.position.sizeInTokens,
            -sizeDeltaUsd,
            positionInfo.position.isLong,
            pool_status,
            pool_config
        )

        getPositionFeesParams = GetPositionFeesParams(
            position=positionInfo.position,
            collateralTokenPrice=collateralTokenPrice,
            forPositiveImpact=positionInfo.executionPriceResult.priceImpactUsd > 0,
            sizeDeltaUsd=sizeDeltaUsd,
            isLiquidation=False
        )

        positionInfo.fees = PositionPricingUtils.getPositionFees(getPositionFeesParams, pool_status, pool_config, pool)
        cache.pendingBorrowingFeeUsd = MarketUtils.getNextBorrowingFees(pending_borrowing_time, positionInfo.position, cache.market, prices, pool_status, pool_config)
        positionInfo.fees.borrowing = PositionPricingUtils.getBorrowingFees(cache.collateralTokenPrice, cache.pendingBorrowingFeeUsd, pool_status, pool_config)

        # nextFundingAmountResult = ReaderPositionUtils.getNextFundingAmountPerSize(market, prices, pool_status)  # todo
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

        positionInfo.basePnlUsd, positionInfo.uncappedBasePnlUsd, _ = PositionUtils.getPositionPnlUsd(cache.market, prices, positionInfo.position, sizeDeltaUsd, pool_status, pool_config)
        positionInfo.pnlAfterPriceImpactUsd = positionInfo.executionPriceResult.priceImpactUsd + positionInfo.basePnlUsd

        positionInfo.fees.totalCostAmountExcludingFunding = positionInfo.fees.positionFeeAmount + positionInfo.fees.borrowing.borrowingFeeAmount - positionInfo.fees.totalDiscountAmount
        positionInfo.fees.totalCostAmount = positionInfo.fees.totalCostAmountExcludingFunding + positionInfo.fees.funding.fundingFeeAmount
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
        cache.sizeOfLargerSide = cache.longOpenInterest if cache.longOpenInterest > cache.shortOpenInterest else cache.shortOpenInterest
        result.fundingFactorPerSecond, result.longsPayShorts, result.nextSavedFundingFactorPerSecond = ReaderPositionUtils.getNextFundingFactorPerSecond()
        cache.fundingUsd = cache.sizeOfLargerSide * cache.durationInSeconds * result.fundingFactorPerSecond  # todo
        cache.fundingUsd = cache.fundingUsd / divisor
        if result.longsPayShorts:
            cache.fundingUsdForLongCollateral = cache.fundingUsd * cache.openInterest.long.longToken / cache.longOpenInterest
            cache.fundingUsdForShortCollateral = cache.fundingUsd * cache.openInterest.long.shortToken / cache.longOpenInterest
        else:
            cache.fundingUsdForLongCollateral = cache.fundingUsd * cache.openInterest.short.longToken / cache.shortOpenInterest
            cache.fundingUsdForShortCollateral = cache.fundingUsd * cache.openInterest.short.shortToken / cache.shortOpenInterest

        if result.longsPayShorts:
            result.fundingFeeAmountPerSizeDelta.long.longToken = MarketUtils.getFundingAmountPerSizeDelta(cache.fundingUsdForLongCollateral, cache.openInterest.long.longToken, prices.longTokenPrice.max)
            result.fundingFeeAmountPerSizeDelta.long.shortToken = MarketUtils.getFundingAmountPerSizeDelta(cache.fundingUsdForShortCollateral, cache.openInterest.long.shortToken, prices.shortTokenPrice.max)
            result.claimableFundingAmountPerSizeDelta.short.longToken = MarketUtils.getFundingAmountPerSizeDelta(cache.fundingUsdForLongCollateral,cache.shortOpenInterest, prices.longTokenPrice.max)
            result.claimableFundingAmountPerSizeDelta.short.shortToken = MarketUtils.getFundingAmountPerSizeDelta(cache.fundingUsdForShortCollateral, cache.shortOpenInterest, prices.shortTokenPrice.max)
        else:
            result.fundingFeeAmountPerSizeDelta.short.longToken = MarketUtils.getFundingAmountPerSizeDelta(cache.fundingUsdForLongCollateral, cache.openInterest.short.longToken, prices.longTokenPrice.max)
            result.fundingFeeAmountPerSizeDelta.short.shortToken = MarketUtils.getFundingAmountPerSizeDelta(cache.fundingUsdForShortCollateral, cache.openInterest.short.shortToken, prices.shortTokenPrice.max)
            result.claimableFundingAmountPerSizeDelta.long.longToken = MarketUtils.getFundingAmountPerSizeDelta(cache.fundingUsdForLongCollateral, cache.longOpenInterest, prices.longTokenPrice.max)
            result.claimableFundingAmountPerSizeDelta.long.shortToken = MarketUtils.getFundingAmountPerSizeDelta(cache.fundingUsdForShortCollateral, cache.longOpenInterest, prices.shortTokenPrice.max)
        return result

    @staticmethod
    def getNextFundingFactorPerSecond(longOpenInterest, shortOpenInterest, durationInSeconds, pool_config: PoolConfig):
        cache = GetNextFundingFactorPerSecondCache()
        cache.diffUsd = longOpenInterest - shortOpenInterest if longOpenInterest > shortOpenInterest else shortOpenInterest - longOpenInterest
        cache.totalOpenInterest = longOpenInterest + shortOpenInterest
        configCache = FundingConfigCache()
        configCache.fundingIncreaseFactorPerSecond = pool_config.fundingIncreaseFactorPerSecond  # todo from config
        if cache.diffUsd == 0 and configCache.fundingIncreaseFactorPerSecond == 0:
            return 0, True, 0
        cache.fundingExponentFactor = pool_config.fundingExponentFactor
        cache.diffUsdAfterExponent = cache.diffUsd ** cache.fundingExponentFactor
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
        isSkewTheSameDirectionAsFunding = (cache.savedFundingFactorPerSecond > 0 and longOpenInterest > shortOpenInterest) or (cache.savedFundingFactorPerSecond < 0 and shortOpenInterest > longOpenInterest)
        if isSkewTheSameDirectionAsFunding:
            if cache.diffUsdToOpenInterestFactor > configCache.thresholdForStableFunding:
                fundingRateChangeType = FundingRateChangeType.Increase
            elif cache.diffUsdToOpenInterestFactor < configCache.thresholdForDecreaseFunding:
                fundingRateChangeType = FundingRateChangeType.Decrease
        else:
            fundingRateChangeType = FundingRateChangeType.Increase

        if fundingRateChangeType == FundingRateChangeType.Increase:
            increaseValue = cache.diffUsdToOpenInterestFactor * configCache.fundingIncreaseFactorPerSecond * durationInSeconds
            if  longOpenInterest < shortOpenInterest:
                increaseValue = -increaseValue
            cache.nextSavedFundingFactorPerSecond = cache.savedFundingFactorPerSecond + increaseValue

        if fundingRateChangeType == FundingRateChangeType.Decrease and cache.savedFundingFactorPerSecondMagnitude != 0:
            configCache.fundingDecreaseFactorPerSecond = pool_config.fundingDecreaseFactorPerSecond
            decreaseValue = configCache.fundingDecreaseFactorPerSecond * durationInSeconds
            if cache.savedFundingFactorPerSecondMagnitude <= decreaseValue:
                cache.nextSavedFundingFactorPerSecond = cache.savedFundingFactorPerSecond / cache.savedFundingFactorPerSecondMagnitude
            else:
                sign = cache.savedFundingFactorPerSecond / cache.savedFundingFactorPerSecondMagnitude
                cache.nextSavedFundingFactorPerSecond = (cache.savedFundingFactorPerSecondMagnitude - decreaseValue) * sign

        configCache.minFundingFactorPerSecond = pool_config.minFundingFactorPerSecond
        configCache.maxFundingFactorPerSecond = pool_config.maxFundingFactorPerSecond

        cache.nextSavedFundingFactorPerSecond = ReaderPositionUtils.boundMagnitude(cache.nextSavedFundingFactorPerSecond, 0, configCache.maxFundingFactorPerSecond)
        cache.nextSavedFundingFactorPerSecondWithMinBound = ReaderPositionUtils.boundMagnitude(cache.nextSavedFundingFactorPerSecond, configCache.minFundingFactorPerSecond, configCache.maxFundingFactorPerSecond)

        return abs(cache.nextSavedFundingFactorPerSecondWithMinBound), cache.nextSavedFundingFactorPerSecondWithMinBound > 0, cache.nextSavedFundingFactorPerSecond

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
        market: Market,
        indexTokenPrice: float,
        positionSizeInUsd: float,
        positionSizeInTokens: float,
        sizeDeltaUsd: float,
        isLong: bool,
        pool_status: GmxV2PoolStatus,
        pool_config: PoolConfig
    ):
        position = Position()
        position.sizeInUsd = positionSizeInUsd
        position.sizeInTokens = positionSizeInTokens
        position.isLong = isLong

        order = Order()
        order.sizeDeltaUsd = abs(sizeDeltaUsd)
        order.isLong = isLong

        result = ExecutionPriceResult()

        params = UpdatePositionParams(
            market,
            order,
            position,
            ''
        )

        if sizeDeltaUsd > 0:
            result.priceImpactUsd, _, _, result.executionPrice = PositionUtils.getExecutionPriceForIncrease(params, indexTokenPrice, pool_status, pool_config)
        else:
            indexTokenPrice = Price(min=indexTokenPrice, max=indexTokenPrice)
            result.priceImpactUsd, result.priceImpactDiffUsd, result.executionPrice = PositionUtils.getExecutionPriceForDecrease(params, indexTokenPrice, pool_status, pool_config)

        return result
