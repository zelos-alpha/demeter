from dataclasses import dataclass

from demeter import DemeterError, TokenInfo
from .._typing import Order, GmxV2Pool, PoolData
from ..market.MarketUtils import MarketUtils, MarketPrices
from ..pricing.PositionPricingUtils import (
    PositionPricingUtils,
    GetPriceImpactUsdParams,
    PositionFees,
    GetPositionFeesParams,
)
from .Position import Position
from .BaseOrderUtils import BaseOrderUtils


@dataclass
class UpdatePositionParams:
    market: GmxV2Pool
    order: Order
    position: Position
    claimableFundingAmount: dict[TokenInfo, float] | None


@dataclass
class IsPositionLiquidatableInfo:
    remainingCollateralUsd: float = 0
    minCollateralUsd: float = 0
    minCollateralUsdForLeverage: float = 0


@dataclass
class WillPositionCollateralBeSufficientValues:
    positionSizeInUsd: float
    positionCollateralAmount: float
    realizedPnlUsd: float
    openInterestDelta: float


@dataclass
class DecreasePositionCollateralValuesOutput:
    outputToken: TokenInfo = None
    outputAmount: float = 0
    secondaryOutputToken: TokenInfo = None
    secondaryOutputAmount: float = 0


@dataclass
class DecreasePositionCollateralValues:
    executionPrice: float = 0
    remainingCollateralAmount: float = 0
    basePnlUsd: float = 0
    uncappedBasePnlUsd: float = 0
    sizeDeltaInTokens: float = 0
    priceImpactUsd: float = 0
    proportionalPendingImpactAmount: float = 0
    proportionalPendingImpactUsd: float = 0
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
    pnlToken: TokenInfo | None = None
    pnlTokenPrice: float = 0
    collateralTokenPrice: float = 0
    initialCollateralAmount: float = 0
    nextPositionSizeInUsd: float = 0
    nextPositionBorrowingFactor: float = 0


class PositionUtils:
    @staticmethod
    def getExecutionPriceForIncrease(
        params: UpdatePositionParams, prices: MarketPrices, pool_data: PoolData
    ) -> tuple[float, float, float, float, bool]:
        if params.order.sizeDeltaUsd == 0:
            return 0, 0, 0, prices.indexTokenPrice, False
        priceImpactUsd, balanceWasImproved = PositionPricingUtils.getPriceImpactUsd(
            GetPriceImpactUsdParams(isLong=params.order.isLong, usdDelta=params.order.sizeDeltaUsd), pool_data
        )
        # cap positive priceImpactUsd based on the max positive position impact factor
        # note that the positive priceImpactUsd is not capped by the position impact pool here
        # this is to prevent cases where for new markets, user A opens a position with negative
        # price impact and user B does not have any incentive to open a position to balance the pool
        # because the price impact pool is empty until user A closes
        # the positive price impact will still be capped during position decrease when the positive
        # price impact is actually paid out
        #
        # we do not call capPositiveImpactUsdByPositionImpactPool for increase as we are
        # uncertain when the impact pool state would be when the position is actually
        # closed and the impact is to be realized
        priceImpactUsd = MarketUtils.capPositiveImpactUsdByMaxPositionImpact(
            priceImpactUsd, params.order.sizeDeltaUsd, pool_data
        )

        # for long positions
        #
        # if price impact is positive, the sizeDeltaInTokens would be increased by the priceImpactAmount
        # the priceImpactAmount should be minimized
        #
        # if price impact is negative, the sizeDeltaInTokens would be decreased by the priceImpactAmount
        # the priceImpactAmount should be maximized

        # for short positions
        #
        # if price impact is positive, the sizeDeltaInTokens would be decreased by the priceImpactAmount
        # the priceImpactAmount should be minimized
        #
        # if price impact is negative, the sizeDeltaInTokens would be increased by the priceImpactAmount
        # the priceImpactAmount should be maximized
        #
        # Demeter doesn't have max and min price, and type is float instead of int
        if priceImpactUsd > 0:
            priceImpactAmount = priceImpactUsd / prices.indexTokenPrice
        else:
            priceImpactAmount = priceImpactUsd / prices.indexTokenPrice

        if params.position.isLong:
            baseSizeDeltaInTokens = params.order.sizeDeltaUsd / prices.indexTokenPrice
        else:
            baseSizeDeltaInTokens = params.order.sizeDeltaUsd / prices.indexTokenPrice

        if params.position.isLong:
            sizeDeltaInTokens = baseSizeDeltaInTokens + priceImpactAmount
        else:
            sizeDeltaInTokens = baseSizeDeltaInTokens - priceImpactAmount

        if sizeDeltaInTokens < 0:
            raise DemeterError(
                f"PriceImpactLargerThanOrderSize, priceImpactUsd: {priceImpactUsd}, sizeDeltaUsd: {params.order.sizeDeltaUsd}"
            )

        # using increase of long positions as an example
        # if price is $2000, sizeDeltaUsd is $5000, priceImpactUsd is -$1000
        # priceImpactAmount = -1000 / 2000 = -0.5
        # baseSizeDeltaInTokens = 5000 / 2000 = 2.5
        # sizeDeltaInTokens = 2.5 - 0.5 = 2
        # executionPrice = 5000 / 2 = $2500
        executionPrice = BaseOrderUtils.getExecutionPriceForIncrease(params.order.sizeDeltaUsd, sizeDeltaInTokens)
        return priceImpactUsd, priceImpactAmount, baseSizeDeltaInTokens, executionPrice, balanceWasImproved

    @staticmethod
    def getPositionPnlUsd(
        prices: MarketPrices,
        position: Position,
        sizeDeltaUsd: float,
        pool_data: PoolData,
    ) -> tuple[float, float, float]:
        market = pool_data.market
        executionPrice = prices.indexTokenPrice

        # position.sizeInUsd is the cost of the tokens, positionValue is the current worth of the tokens
        positionValue = position.sizeInTokens * executionPrice
        totalPositionPnl = positionValue - position.sizeInUsd if position.isLong else position.sizeInUsd - positionValue
        uncappedTotalPositionPnl = totalPositionPnl

        if totalPositionPnl > 0:
            pnlToken = market.long_token if position.isLong else market.short_token
            poolAmount = pool_data.status.longAmount if pnlToken == market.long_token else pool_data.status.shortAmount
            poolTokenAmount = MarketUtils.getPoolAmount(market, poolAmount)
            poolTokenPrice = prices.longTokenPrice if position.isLong else prices.shortTokenPrice
            poolTokenUsd = poolTokenAmount * poolTokenPrice
            poolPnl = MarketUtils.getPnl(prices.indexTokenPrice, position.isLong, pool_data.status)
            cappedPoolPnl = MarketUtils.getCappedPnl(position.isLong, poolPnl, poolTokenUsd, pool_data.config)
            if cappedPoolPnl != poolPnl and cappedPoolPnl > 0 and poolPnl > 0:
                totalPositionPnl = totalPositionPnl * cappedPoolPnl / poolPnl

        if position.sizeInUsd == sizeDeltaUsd:
            sizeDeltaInTokens = position.sizeInTokens
        else:
            sizeDeltaInTokens = position.sizeInTokens * sizeDeltaUsd / position.sizeInUsd

        positionPnlUsd = totalPositionPnl * sizeDeltaInTokens / position.sizeInTokens
        uncappedPositionPnlUsd = uncappedTotalPositionPnl * sizeDeltaInTokens / position.sizeInTokens
        return positionPnlUsd, uncappedPositionPnlUsd, sizeDeltaInTokens

    @staticmethod
    def willPositionCollateralBeSufficient(
        prices: MarketPrices,
        collateralToken: TokenInfo,
        isLong: bool,
        values: WillPositionCollateralBeSufficientValues,
        pool_data: PoolData,
    ):
        collateralTokenPrice = MarketUtils.getCachedTokenPrice(collateralToken, pool_data.market, prices)
        remainingCollateralUsd = values.positionCollateralAmount * collateralTokenPrice

        # deduct realized pnl if it is negative since this would be paid from
        # the position's collateral
        if values.realizedPnlUsd < 0:
            remainingCollateralUsd = remainingCollateralUsd + values.realizedPnlUsd

        if remainingCollateralUsd < 0:
            return False, remainingCollateralUsd

        # the min collateral factor will increase as the open interest for a market increases
        # this may lead to previously created limit increase orders not being executable
        #
        # the position's pnl is not factored into the remainingCollateralUsd value, since
        # factoring in a positive pnl may allow the user to manipulate price and bypass this check
        # it may be useful to factor in a negative pnl for this check, this can be added if required
        minCollateralFactor = MarketUtils.getMinCollateralFactorForOpenInterest(
            isLong, values.openInterestDelta, pool_data
        )
        minCollateralFactorForMarket = pool_data.config.minCollateralFactor
        # use the minCollateralFactor for the market if it is larger
        if minCollateralFactorForMarket > minCollateralFactor:
            minCollateralFactor = minCollateralFactorForMarket
        minCollateralUsdForLeverage = values.positionSizeInUsd * minCollateralFactor
        willBeSufficient = remainingCollateralUsd >= minCollateralUsdForLeverage
        return willBeSufficient, remainingCollateralUsd

    @staticmethod
    def getExecutionPriceForDecrease(
        params: UpdatePositionParams, indexTokenPrice: float, pool_data: PoolData
    ) -> tuple[float, float, bool]:
        sizeDeltaUsd = params.order.sizeDeltaUsd

        # note that the executionPrice is not validated against the order.acceptablePrice value
        # if the sizeDeltaUsd is zero
        # for limit orders the order.triggerPrice should still have been validated
        if sizeDeltaUsd == 0:
            # decrease order:
            #     - long: use the smaller price
            #     - short: use the larger price
            return 0, indexTokenPrice, False

        priceImpactUsd, balanceWasImproved = PositionPricingUtils.getPriceImpactUsd(
            GetPriceImpactUsdParams(isLong=params.order.isLong, usdDelta=-sizeDeltaUsd), pool_data
        )
        priceImpactUsd = MarketUtils.capPositiveImpactUsdByMaxPositionImpact(priceImpactUsd, sizeDeltaUsd, pool_data)

        executionPrice = BaseOrderUtils.getExecutionPriceForDecrease(
            indexTokenPrice,
            params.position.sizeInUsd,
            params.position.sizeInTokens,
            sizeDeltaUsd,
            priceImpactUsd,
            params.position.isLong,
        )
        return priceImpactUsd, executionPrice, balanceWasImproved

    @staticmethod
    def incrementClaimableFundingAmount(params: UpdatePositionParams, fees: PositionFees):
        # if the position has negative funding fees, distribute it to allow it to be claimable
        if fees.funding.claimableLongTokenAmount > 0:
            params.claimableFundingAmount[params.market.long_token] += fees.funding.claimableLongTokenAmount

        if fees.funding.claimableShortTokenAmount > 0:
            params.claimableFundingAmount[params.market.short_token] += fees.funding.claimableShortTokenAmount

    @staticmethod
    def isPositionLiquidatable(
        position: Position,
        prices: MarketPrices,
        shouldValidateMinCollateralUsd: bool,
        forLiquidation: bool,
        pool_data: PoolData,
    ) -> tuple[bool, str, IsPositionLiquidatableInfo]:
        market = pool_data.market
        info = IsPositionLiquidatableInfo()

        positionPnlUsd, _, _ = PositionUtils.getPositionPnlUsd(prices, position, position.sizeInUsd, pool_data)

        collateralTokenPrice = MarketUtils.getCachedTokenPrice(position.collateralToken, market, prices)

        collateralUsd = position.collateralAmount * collateralTokenPrice

        # calculate the usdDeltaForPriceImpact for fully closing the position
        usdDeltaForPriceImpact = -position.sizeInUsd

        priceImpactUsd, balanceWasImproved = PositionPricingUtils.getPriceImpactUsd(
            GetPriceImpactUsdParams(position.isLong, usdDeltaForPriceImpact), pool_data
        )

        # cap positive priceImpactUsd based on the max positive position impact factor
        priceImpactUsd = MarketUtils.capPositiveImpactUsdByMaxPositionImpact(
            priceImpactUsd, position.sizeInUsd, pool_data
        )

        priceImpactUsd += position.pendingImpactAmount * prices.indexTokenPrice

        # even if there is a large positive price impact, positions that would be liquidated
        # if the positive price impact is reduced should not be allowed to be created
        # as they would be easily liquidated if the price impact changes
        # cap the priceImpactUsd to zero to prevent these positions from being created
        if priceImpactUsd >= 0:
            priceImpactUsd = 0
        else:
            maxPriceImpactFactor = pool_data.config.maxPositionImpactFactorForLiquidation

            # if there is a large build up of open interest and a sudden large price movement
            # it may result in a large imbalance between longs and shorts
            # this could result in very large price impact temporarily
            # cap the max negative price impact to prevent cascading liquidations
            maxNegativePriceImpactUsd = -position.sizeInUsd * maxPriceImpactFactor
            if priceImpactUsd < maxNegativePriceImpactUsd:
                priceImpactUsd = maxNegativePriceImpactUsd

        getPositionFeesParams: GetPositionFeesParams = GetPositionFeesParams(
            position,  # position
            collateralTokenPrice,  # collateralTokenPrice
            balanceWasImproved,  # balanceWasImproved
            market.long_token,  # longToken
            market.short_token,  # shortToken
            position.sizeInUsd,  # sizeDeltaUsd
            # should not account for liquidation fees to determine if position should be liquidated
            False,  # isLiquidation
        )

        fees: PositionFees = PositionPricingUtils.getPositionFees(getPositionFeesParams, pool_data)

        # the totalCostAmount is in tokens, use collateralTokenPrice.min to calculate the cost in USD
        # since in PositionPricingUtils.getPositionFees the totalCostAmount in tokens was calculated
        # using collateralTokenPrice.min
        collateralCostUsd = fees.totalCostAmount * collateralTokenPrice

        # the position's pnl is counted as collateral for the liquidation check
        # as a position in profit should not be liquidated if the pnl is sufficient
        # to cover the position's fees
        info.remainingCollateralUsd = collateralUsd + positionPnlUsd + priceImpactUsd - collateralCostUsd

        if forLiquidation:
            minCollateralFactor = pool_data.config.minCollateralFactorForLiquidation
        else:
            minCollateralFactor = pool_data.config.minCollateralFactor

        # validate if (remaining collateral) / position.size is less than the min collateral factor (max leverage exceeded)
        # this validation includes the position fee to be paid when closing the position
        # i.e. if the position does not have sufficient collateral after closing fees it is considered a liquidatable position
        info.minCollateralUsdForLeverage = position.sizeInUsd * minCollateralFactor

        if shouldValidateMinCollateralUsd:
            info.minCollateralUsd = pool_data.config.minCollateralUsd
            if info.remainingCollateralUsd < info.minCollateralUsd:
                return True, "min collateral", info

        if info.remainingCollateralUsd <= 0:
            return True, "< 0", info

        if info.remainingCollateralUsd < info.minCollateralUsdForLeverage:
            return True, "min collateral for leverage", info

        return False, "", info

    @staticmethod
    def validatePosition(
        position: Position,
        prices: MarketPrices,
        shouldValidateMinPositionSize: bool,
        shouldValidateMinCollateralUsd: bool,
        pool_data: PoolData,
    ):
        if position.sizeInUsd == 0 or position.sizeInTokens == 0:
            raise DemeterError(
                f"InvalidPositionSizeValues(sizeInUsd: {position.sizeInUsd},sizeInTokens: {position.sizeInTokens})"
            )

        # validateEnabledMarket(dataStore, market.marketToken);
        # validateMarketCollateralToken(market, position.collateralToken());

        if shouldValidateMinPositionSize:
            minPositionSizeUsd = pool_data.config.minPositionSizeUsd
            if position.sizeInUsd < minPositionSizeUsd:
                raise DemeterError(
                    f"MinPositionSize(sizeInUsd: {position.sizeInUsd}, minPositionSizeUsd: {minPositionSizeUsd})"
                )

        isLiquidatable, reason, info = PositionUtils.isPositionLiquidatable(
            position,
            prices,
            shouldValidateMinCollateralUsd,
            False,
            pool_data,
        )

        if isLiquidatable:
            raise DemeterError(
                f"LiquidatablePosition(reason: {reason},remainingCollateralUsd: {info.remainingCollateralUsd},minCollateralUsd: {info.minCollateralUsd},minCollateralUsdForLeverage: {info.minCollateralUsdForLeverage})"
            )
