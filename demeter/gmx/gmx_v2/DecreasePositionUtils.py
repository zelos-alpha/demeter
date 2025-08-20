from .PositionUtils import UpdatePositionParams, DecreasePositionCache
from .PositionUtils import PositionUtils, WillPositionCollateralBeSufficientValues
from .DecreasePositionCollateralUtils import DecreasePositionCollateralUtils
from ._typing import GmxV2PoolStatus, PoolConfig, Market
from .._typing2 import GmxV2Pool
from .MarketUtils import MarketPrices, Price, MarketUtils


class DecreasePositionUtils:
    @staticmethod
    def decreasePosition(params: UpdatePositionParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig, pool: GmxV2Pool):
        cache = DecreasePositionCache()
        cache.prices = MarketPrices(
            indexTokenPrice=Price(min=pool_status.indexPrice, max=pool_status.indexPrice),
            longTokenPrice=Price(min=pool_status.longPrice, max=pool_status.longPrice),
            shortTokenPrice=Price(min=pool_status.shortPrice, max=pool_status.shortPrice),
        )
        market = Market(
            indexToken=pool.index_token.address,
            longToken=pool.long_token.address,
            shortToken=pool.short_token.address
        )
        if params.order.initialCollateralToken == pool.index_token.address:
            cache.collateralTokenPrice = cache.prices.indexTokenPrice
        if params.order.initialCollateralToken == pool.short_token.address:
            cache.collateralTokenPrice = cache.prices.shortTokenPrice
        if params.order.initialCollateralToken == pool.long_token.address:
            cache.collateralTokenPrice = cache.prices.longTokenPrice

        if params.order.sizeDeltaUsd < params.position.sizeInUsd:
            cache.estimatedPositionPnlUsd, _, _ = PositionUtils.getPositionPnlUsd(
                market, cache.prices,
                params.position,
                params.position.sizeInUsd,
                pool_status
            )
            cache.estimatedRealizedPnlUsd = cache.estimatedPositionPnlUsd * params.order.sizeDeltaUsd / params.position.sizeInUsd
            cache.estimatedRemainingPnlUsd = cache.estimatedPositionPnlUsd - cache.estimatedRealizedPnlUsd

        positionValues = WillPositionCollateralBeSufficientValues(
            positionSizeInUsd=params.position.sizeInUsd - params.order.sizeDeltaUsd,
            positionCollateralAmount=params.position.collateralAmount - params.order.initialCollateralDeltaAmount,
            realizedPnlUsd=cache.estimatedRealizedPnlUsd,
            openInterestDelta=-params.order.sizeDeltaUsd
        )
        willBeSufficient, estimatedRemainingCollateralUsd = PositionUtils.willPositionCollateralBeSufficient(cache.collateralTokenPrice, params.position.isLong, positionValues, pool_status)
        if not willBeSufficient:
            estimatedRemainingCollateralUsd += params.order.initialCollateralDeltaAmount * cache.collateralTokenPrice.min
            params.order.initialCollateralDeltaAmount = 0

        if estimatedRemainingCollateralUsd + cache.estimatedRemainingPnlUsd < pool_status.minCollateralUsd:
            params.order.setSizeDeltaUsd = params.position.sizeInUsd

        if params.position.sizeInUsd > params.order.sizeDeltaUsd and (params.position.sizeInUsd - params.order.sizeDeltaUsd) < pool_status.minPositionSizeUsd:
            params.order.setSizeDeltaUsd = params.position.sizeInUsd

        if params.order.sizeDeltaUsd == params.position.sizeInUsd and params.order.initialCollateralDeltaAmount > 0:
            params.order.initialCollateralDeltaAmount = 0

        cache.pnlToken = market.longToken if params.position.isLong else market.shortToken
        cache.pnlTokenPrice = cache.prices.longTokenPrice if params.position.isLong else cache.prices.shortTokenPrice

        cache.initialCollateralAmount = params.position.collateralAmount

        values, fees = DecreasePositionCollateralUtils.processCollateral(params, cache, pool_status, pool_config, pool)

        cache.nextPositionSizeInUsd = params.position.sizeInUsd - params.order.sizeDeltaUsd
        cache.nextPositionBorrowingFactor = MarketUtils.getCumulativeBorrowingFactor(params.position.isLong, pool_status)

        params.position.sizeInUsd = cache.nextPositionSizeInUsd
        params.position.sizeInTokens = params.position.sizeInTokens - values.sizeDeltaInTokens
        params.position.collateralAmount = values.remainingCollateralAmount

        if params.position.sizeInUsd == 0 or params.position.sizeInTokens == 0:
            values.output.outputAmount += params.position.collateralAmount
            params.position.sizeInUsd = 0
            params.position.sizeInTokens = 0
            params.position.collateralAmount = 0
            # todo remove position
        else:
            params.position.borrowingFactor = cache.nextPositionBorrowingFactor
            params.position.fundingFeeAmountPerSize = fees.funding.latestFundingFeeAmountPerSize
            params.position.longTokenClaimableFundingAmountPerSize = fees.funding.latestLongTokenClaimableFundingAmountPerSize
            params.position.shortTokenClaimableFundingAmountPerSize = fees.funding.latestShortTokenClaimableFundingAmountPerSize
            # todo set position

