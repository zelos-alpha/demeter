from dataclasses import dataclass

from .PositionUtils import UpdatePositionParams, PositionUtils, DecreasePositionCollateralValues, DecreasePositionCache, DecreasePositionCollateralValuesOutput
from .PositionPricingUtils import GetPositionFeesParams, PositionPricingUtils, PositionFees
from .DecreasePositionSwapUtils import DecreasePositionSwapUtils
from ._typing import GmxV2PoolStatus, PoolConfig, Market, OrderType
from .._typing2 import GmxV2Pool
from .MarketUtils import MarketPrices


def isLiquidationOrder(orderType: OrderType) -> bool:
    return orderType == OrderType.Liquidation

@dataclass
class PayForCostResult:
    amountPaidInCollateralToken: float = 0
    amountPaidInSecondaryOutputToken: float = 0
    remainingCostUsd: float = 0


@dataclass
class ProcessCollateralCache:
    wasSwapped: bool = False
    swapOutputAmount: float = 0
    result: PayForCostResult = None


class DecreasePositionCollateralUtils:

    @staticmethod
    def processCollateral(params: UpdatePositionParams, cache: DecreasePositionCache, pool_status: GmxV2PoolStatus, pool_config: PoolConfig, pool: GmxV2Pool):
        collateralCache = ProcessCollateralCache()
        values = DecreasePositionCollateralValues()
        values.output = DecreasePositionCollateralValuesOutput()
        values.output.outputToken = params.position.collateralToken.address
        values.output.secondaryOutputToken = cache.pnlToken
        values.priceImpactUsd, values.priceImpactDiffUsd, values.executionPrice = PositionUtils.getExecutionPriceForDecrease(params, cache.prices.indexTokenPrice, pool_status, pool_config)
        market = Market(
            indexToken=pool.index_token.address,
            longToken=pool.long_token.address,
            shortToken=pool.short_token.address
        )
        values.basePnlUsd, values.uncappedBasePnlUsd, values.sizeDeltaInTokens = PositionUtils.getPositionPnlUsd(
            market,
            cache.prices,
            params.position,
            params.position.sizeInUsd,
            pool_status,
            pool_config
        )
        getPositionFeesParams = GetPositionFeesParams(
            position=params.position,
            collateralTokenPrice=cache.collateralTokenPrice.max,
            forPositiveImpact=values.priceImpactUsd > 0,
            sizeDeltaUsd=params.order.sizeDeltaUsd,
            isLiquidation=False
        )

        if values.basePnlUsd > 0:
            deductionAmountForPool = values.basePnlUsd / cache.pnlTokenPrice.max
            if values.output.outputToken == cache.pnlToken:
                values.output.outputAmount += deductionAmountForPool
            else:
                values.output.secondaryOutputAmount += deductionAmountForPool

        if values.priceImpactUsd > 0:
            deductionAmountForImpactPool = values.priceImpactUsd / cache.prices.indexTokenPrice.min
            deductionAmountForPool = values.priceImpactUsd / cache.pnlTokenPrice.max
            if values.output.outputToken == cache.pnlToken:
                values.output.outputAmount += deductionAmountForPool
            else:
                values.output.secondaryOutputAmount += deductionAmountForPool

        collateralCache.wasSwapped, collateralCache.swapOutputAmount = DecreasePositionSwapUtils.swapProfitToCollateralToken(params, cache.pnlToken, values.output.secondaryOutputAmount, pool_status, pool_config)
        if collateralCache.wasSwapped:
            values.output.outputAmount += collateralCache.swapOutputAmount
            values.output.secondaryOutputAmount = 0
        values.remainingCollateralAmount = params.position.collateralAmount

        fees = PositionPricingUtils.getPositionFees(getPositionFeesParams, pool_status, pool_config, pool)

        # pay for funding fees
        values, collateralCache.result = DecreasePositionCollateralUtils.payForCost(
            params,
            values,
            cache.prices,
            cache.collateralTokenPrice.min,
            fees.funding.fundingFeeAmount * cache.collateralTokenPrice.min
        )

        if collateralCache.result.remainingCostUsd > 0:
            return values, PositionFees()
            pass  # todo handleEarlyReturn

        # pay for negative pnl
        if values.basePnlUsd < 0:
            values, collateralCache.result = DecreasePositionCollateralUtils.payForCost(
                params,
                values,
                cache.prices,
                cache.collateralTokenPrice.min,
                -values.basePnlUsd
            )
            if collateralCache.result.remainingCostUsd > 0:
                return values, PositionFees()
                pass  # todo handleEarlyReturn

        # pay for fees
        values, collateralCache.result = DecreasePositionCollateralUtils.payForCost(
                params,
                values,
                cache.prices,
                cache.collateralTokenPrice.min,
                fees.totalCostAmountExcludingFunding * cache.collateralTokenPrice.min
            )

        if collateralCache.result.remainingCostUsd == 0 and collateralCache.result.amountPaidInSecondaryOutputToken == 0:
            pass
        else:
            fees = PositionFees()

        if collateralCache.result.remainingCostUsd > 0:
            return values, PositionFees()
            pass  # todo handleEarlyReturn

        # pay for negative price impact
        if values.priceImpactUsd < 0:
            values, collateralCache.result = DecreasePositionCollateralUtils.payForCost(
                params,
                values,
                cache.prices,
                cache.collateralTokenPrice.min,
                -values.priceImpactUsd
            )

            if collateralCache.result.remainingCostUsd > 0:
                return values, PositionFees()
                pass  # todo handleEarlyReturn

        # pay for price impact diff
        if values.priceImpactDiffUsd > 0:
            values, collateralCache.result = DecreasePositionCollateralUtils.payForCost(
                params,
                values,
                cache.prices,
                cache.collateralTokenPrice.min,
                values.priceImpactDiffUsd
            )
            if collateralCache.result.remainingCostUsd > 0:
                return values, PositionFees()
                pass  # todo handleEarlyReturn

        if params.order.initialCollateralDeltaAmount > 0 and values.priceImpactDiffUsd > 0:
            initialCollateralDeltaAmount = params.order.initialCollateralDeltaAmount
            priceImpactDiffAmount = values.priceImpactDiffUsd / cache.collateralTokenPrice.min
            if initialCollateralDeltaAmount > priceImpactDiffAmount:
                params.order.initialCollateralDeltaAmount = initialCollateralDeltaAmount - priceImpactDiffAmount
            else:
                params.order.initialCollateralDeltaAmount = 0

        if params.order.initialCollateralDeltaAmount > values.remainingCollateralAmount:
            params.order.initialCollateralDeltaAmount = values.remainingCollateralAmount

        if params.order.initialCollateralDeltaAmount > 0:
            values.remainingCollateralAmount -= params.order.initialCollateralDeltaAmount
            values.output.outputAmount += params.order.initialCollateralDeltaAmount

        return values, fees

    @staticmethod
    def payForCost(
        params: UpdatePositionParams,
        values: DecreasePositionCollateralValues,
        prices: MarketPrices,
        collateralTokenPrice: float,
        costUsd: float
    ) -> (DecreasePositionCollateralValues, PayForCostResult):
        result = PayForCostResult()
        if costUsd == 0:
            return values, result
        remainingCostInOutputToken = costUsd / collateralTokenPrice
        if values.output.outputAmount > 0:
            if values.output.outputAmount > remainingCostInOutputToken:
                result.amountPaidInCollateralToken += remainingCostInOutputToken
                values.output.outputAmount -= remainingCostInOutputToken
                remainingCostInOutputToken = 0
            else:
                result.amountPaidInCollateralToken += values.output.outputAmount
                remainingCostInOutputToken -= values.output.outputAmount
                values.output.outputAmount = 0
        if remainingCostInOutputToken == 0:
            return values, result
        if values.remainingCollateralAmount > 0:
            if values.remainingCollateralAmount > remainingCostInOutputToken:
                result.amountPaidInCollateralToken += remainingCostInOutputToken
                values.remainingCollateralAmount -= remainingCostInOutputToken
                remainingCostInOutputToken = 0
            else:
                result.amountPaidInCollateralToken += values.remainingCollateralAmount
                remainingCostInOutputToken -= values.remainingCollateralAmount
                values.remainingCollateralAmount = 0
        if remainingCostInOutputToken == 0:
            return values, result

        secondaryOutputTokenPrice = 0
        if values.output.secondaryOutputToken == params.market.longToken:
            secondaryOutputTokenPrice = prices.longTokenPrice.min
        if values.output.secondaryOutputToken == params.market.shortToken:
            secondaryOutputTokenPrice = prices.shortTokenPrice.min
        if values.output.secondaryOutputToken == params.market.indexToken:
            secondaryOutputTokenPrice = prices.indexTokenPrice.min

        remainingCostInSecondaryOutputToken = remainingCostInOutputToken * collateralTokenPrice / secondaryOutputTokenPrice

        if values.output.secondaryOutputAmount > 0:
            if values.output.secondaryOutputAmount > remainingCostInSecondaryOutputToken:
                result.amountPaidInSecondaryOutputToken += remainingCostInSecondaryOutputToken
                values.output.secondaryOutputAmount -= remainingCostInSecondaryOutputToken
                remainingCostInSecondaryOutputToken = 0
            else:
                result.amountPaidInSecondaryOutputToken += values.output.secondaryOutputAmount
                remainingCostInSecondaryOutputToken -= values.output.secondaryOutputAmount
                values.output.secondaryOutputAmount = 0
        result.remainingCostUsd = remainingCostInSecondaryOutputToken * secondaryOutputTokenPrice
        return values, result

    @staticmethod
    def handleEarlyReturn(values: DecreasePositionCollateralValues):
        return values, PositionFees()
