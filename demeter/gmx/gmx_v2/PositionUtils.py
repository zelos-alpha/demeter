from dataclasses import dataclass
from .PositionPricingUtils import PositionPricingUtils, GetPriceImpactUsdParams
from .MarketUtils import MarketUtils, MarketPrices, Price
from .Position import Position
from ._typing import GmxV2PoolStatus, PoolConfig, Market, Order
from .._typing2 import GmxV2Pool


@dataclass
class UpdatePositionParams:
    market: Market
    order: Order
    position: Position
    positionKey: str


@dataclass
class WillPositionCollateralBeSufficientValues:
    positionSizeInUsd: float
    positionCollateralAmount: float
    realizedPnlUsd: float
    openInterestDelta: float


@dataclass
class DecreasePositionCollateralValuesOutput:
    outputToken: str = ''
    outputAmount: float = 0
    secondaryOutputToken: str = 0
    secondaryOutputAmount: float = 0


@dataclass
class DecreasePositionCollateralValues:
    executionPrice: float = 0
    remainingCollateralAmount: float = 0
    basePnlUsd: float = 0
    uncappedBasePnlUsd: float = 0
    sizeDeltaInTokens: float = 0
    priceImpactUsd: float = 0
    priceImpactDiffUsd: float = 0
    output: DecreasePositionCollateralValuesOutput = None


@dataclass
class GetPositionPnlUsdCache:
    positionValue: float = 0
    totalPositionPnl: float = 0
    uncappedTotalPositionPnl: float = 0
    pnlToken: str = ""
    poolTokenAmount: float = 0
    poolTokenPrice: float = 0
    poolTokenUsd: float = 0
    poolPnl: float = 0
    cappedPoolPnl: float = 0
    sizeDeltaInTokens: float = 0
    positionPnlUsd: float = 0
    uncappedPositionPnlUsd: float = 0


@dataclass
class DecreasePositionCache:
    prices: MarketPrices = None
    estimatedPositionPnlUsd: float = 0
    estimatedRealizedPnlUsd: float = 0
    estimatedRemainingPnlUsd: float = 0
    pnlToken: str = ''
    pnlTokenPrice: Price = None
    collateralTokenPrice: Price = None
    initialCollateralAmount: float = 0
    nextPositionSizeInUsd: float = 0
    nextPositionBorrowingFactor: float = 0


class PositionUtils:
    @staticmethod
    def getExecutionPriceForIncrease(params: UpdatePositionParams, indexTokenPrice: float, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        if params.order.sizeDeltaUsd == 0:
            return 0, 0, 0, indexTokenPrice
        priceImpactUsd = PositionPricingUtils.getPriceImpactUsd(
            GetPriceImpactUsdParams(
                isLong=params.order.isLong,
                usdDelta=params.order.sizeDeltaUsd
            ),
            pool_status,
            pool_config
        )
        priceImpactUsd = MarketUtils.getCappedPositionImpactUsd(indexTokenPrice, priceImpactUsd, params.order.sizeDeltaUsd, pool_status, pool_config)

        priceImpactAmount = 0
        if priceImpactUsd > 0:
            priceImpactAmount = priceImpactUsd / indexTokenPrice
        else:
            priceImpactAmount = priceImpactUsd / indexTokenPrice

        baseSizeDeltaInTokens = 0
        if params.position.isLong:
            baseSizeDeltaInTokens = params.order.sizeDeltaUsd / indexTokenPrice
        else:
            baseSizeDeltaInTokens = params.order.sizeDeltaUsd / indexTokenPrice

        sizeDeltaInTokens = 0
        if params.position.isLong:
            sizeDeltaInTokens = baseSizeDeltaInTokens + priceImpactAmount
        else:
            sizeDeltaInTokens = baseSizeDeltaInTokens - priceImpactAmount

        executionPrice = PositionUtils._getExecutionPriceForIncrease(
            params.order.sizeDeltaUsd,
            sizeDeltaInTokens,
            params.order.acceptablePrice,
            params.position.isLong
        )
        return priceImpactUsd, priceImpactAmount, sizeDeltaInTokens, executionPrice

    @staticmethod
    def _getExecutionPriceForIncrease(sizeDeltaUsd, sizeDeltaInTokens, acceptablePrice, isLong):
        executionPrice = sizeDeltaUsd / sizeDeltaInTokens
        return executionPrice
        if (isLong and executionPrice <= acceptablePrice) or (not isLong and executionPrice >= acceptablePrice):
            return executionPrice

    @staticmethod
    def getPositionPnlUsd(
            market: Market,
            prices: MarketPrices,
            position: Position,
            sizeDeltaUsd: float,
            pool_status: GmxV2PoolStatus,
            pool_config: PoolConfig
    ):
        cache = GetPositionPnlUsdCache()
        executionPrice = prices.indexTokenPrice.max
        cache.positionValue = position.sizeInTokens * executionPrice
        cache.totalPositionPnl = (cache.positionValue - position.sizeInUsd) if position.isLong else (position.sizeInUsd - cache.positionValue)
        cache.uncappedTotalPositionPnl = cache.totalPositionPnl

        if cache.totalPositionPnl > 0:
            cache.pnlToken = market.longToken if position.isLong else market.shortToken
            poolAmount = pool_status.longAmount if cache.pnlToken == market.longToken else pool_status.shortAmount
            cache.poolTokenAmount = MarketUtils.getPoolAmount(market, poolAmount)
            cache.poolTokenPrice = prices.longTokenPrice.max if position.isLong else prices.shortTokenPrice.max
            cache.poolTokenUsd = cache.poolTokenAmount * cache.poolTokenPrice
            cache.poolPnl = MarketUtils.getPnl(prices.indexTokenPrice, position.isLong, pool_status)
            cache.cappedPoolPnl = MarketUtils.getCappedPnl(position.isLong, cache.poolPnl, cache.poolTokenUsd, pool_config)
            if cache.cappedPoolPnl != cache.poolPnl and cache.cappedPoolPnl > 0 and cache.poolPnl > 0:
                cache.totalPositionPnl = cache.totalPositionPnl * cache.cappedPoolPnl / cache.poolPnl

        if position.sizeInUsd == sizeDeltaUsd:
            cache.sizeDeltaInTokens = position.sizeInTokens
        else:
            cache.sizeDeltaInTokens = position.sizeInTokens * sizeDeltaUsd / position.sizeInUsd

        cache.positionPnlUsd = cache.totalPositionPnl * cache.sizeDeltaInTokens / position.sizeInTokens
        cache.uncappedPositionPnlUsd = cache.uncappedTotalPositionPnl * cache.sizeDeltaInTokens / position.sizeInTokens
        return cache.positionPnlUsd, cache.uncappedPositionPnlUsd, cache.sizeDeltaInTokens

    @staticmethod
    def willPositionCollateralBeSufficient(collateralTokenPrice: Price, isLong: bool, values: WillPositionCollateralBeSufficientValues, pool_status: GmxV2PoolStatus):
        remainingCollateralUsd = values.positionCollateralAmount * collateralTokenPrice.min
        if values.realizedPnlUsd < 0:
            remainingCollateralUsd = remainingCollateralUsd + values.realizedPnlUsd
        if remainingCollateralUsd < 0:
            return False, remainingCollateralUsd
        minCollateralFactor = MarketUtils.getMinCollateralFactorForOpenInterest(isLong, values.openInterestDelta, pool_status)
        minCollateralFactorForMarket = pool_status.minCollateralFactor
        if minCollateralFactorForMarket > minCollateralFactor:
            minCollateralFactor = minCollateralFactorForMarket
        minCollateralUsdForLeverage = values.positionSizeInUsd * minCollateralFactor / 10 ** 30
        willBeSufficient = remainingCollateralUsd >= minCollateralUsdForLeverage
        return willBeSufficient, remainingCollateralUsd

    @staticmethod
    def _getExecutionPriceForDecrease(
            indexTokenPrice: float,
            sizeDeltaUsd: float,
            positionSizeInTokens: float,
            isLong: bool,
            priceImpactUsd: float,
            positionSizeInUsd: float,
            acceptablePrice: float):
        price = indexTokenPrice
        executionPrice = price
        if sizeDeltaUsd > 0 and positionSizeInTokens > 0:
            adjustedPriceImpactUsd = priceImpactUsd if isLong else -priceImpactUsd
            adjustment = (positionSizeInUsd * adjustedPriceImpactUsd / positionSizeInTokens) / sizeDeltaUsd
            _executionPrice = price + adjustment
            executionPrice = _executionPrice
        return executionPrice
        if (isLong and executionPrice >= acceptablePrice) or (not isLong and executionPrice <= acceptablePrice):
            return executionPrice

    @staticmethod
    def getExecutionPriceForDecrease(params: UpdatePositionParams, indexTokenPrice: Price, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        sizeDeltaUsd = params.order.sizeDeltaUsd
        if sizeDeltaUsd == 0:
            return 0, 0, indexTokenPrice
        priceImpactUsd = PositionPricingUtils.getPriceImpactUsd(GetPriceImpactUsdParams(isLong=params.order.isLong, usdDelta=-sizeDeltaUsd), pool_status, pool_config)
        priceImpactUsd = MarketUtils.getCappedPositionImpactUsd(indexTokenPrice.max, priceImpactUsd, sizeDeltaUsd, pool_status, pool_config)

        priceImpactDiffUsd = 0
        if priceImpactUsd < 0:
            maxPriceImpactFactor = MarketUtils.getMaxPositionImpactFactor(False, pool_status, pool_config)
            minPriceImpactUsd = -sizeDeltaUsd * maxPriceImpactFactor
            if priceImpactUsd < minPriceImpactUsd:
                priceImpactDiffUsd = minPriceImpactUsd - priceImpactUsd
                priceImpactUsd = minPriceImpactUsd
        executionPrice = PositionUtils._getExecutionPriceForDecrease(
            indexTokenPrice=indexTokenPrice.max,
            sizeDeltaUsd=sizeDeltaUsd,
            positionSizeInTokens=params.position.sizeInTokens,
            isLong=params.position.isLong,
            priceImpactUsd=priceImpactUsd,
            positionSizeInUsd=params.position.sizeInUsd,
            acceptablePrice=params.order.acceptablePrice
        )
        return priceImpactUsd, priceImpactDiffUsd, executionPrice
