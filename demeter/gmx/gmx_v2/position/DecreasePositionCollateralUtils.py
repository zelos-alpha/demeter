from dataclasses import dataclass

from .BaseOrderUtils import BaseOrderUtils
from .DecreasePositionSwapUtils import DecreasePositionSwapUtils
from .PositionUtils import (
    UpdatePositionParams,
    PositionUtils,
    DecreasePositionCollateralValues,
    DecreasePositionCache,
    DecreasePositionCollateralValuesOutput,
)
from .._typing import PoolData
from ..market.MarketUtils import MarketPrices, MarketUtils
from ..pricing.PositionPricingUtils import GetPositionFeesParams, PositionPricingUtils, PositionFees


@dataclass
class PayForCostResult:
    amountPaidInCollateralToken: float = 0
    amountPaidInSecondaryOutputToken: float = 0
    remainingCostUsd: float = 0


@dataclass
class ProcessCollateralCache:
    isInsolventCloseAllowed: bool = False
    wasSwapped: bool = False
    swapOutputAmount: float = 0
    result: PayForCostResult = None
    balanceWasImproved: bool = False


class DecreasePositionCollateralUtils:

    @staticmethod
    def processCollateral(
        params: UpdatePositionParams,
        cache: DecreasePositionCache,
        pool_data: PoolData,
    ) -> tuple[DecreasePositionCollateralValues, PositionFees]:
        collateralCache = ProcessCollateralCache()
        values = DecreasePositionCollateralValues()
        values.output = DecreasePositionCollateralValuesOutput()

        values.output.outputToken = params.position.collateralToken
        values.output.secondaryOutputToken = cache.pnlToken

        # only allow insolvent closing if it is a liquidation or ADL order
        # isInsolventCloseAllowed is used in handleEarlyReturn to determine
        # whether the txn should revert if the remainingCostUsd is below zero
        #
        # for isInsolventCloseAllowed to be true, the sizeDeltaUsd must equal
        # the position size, otherwise there may be pending positive pnl that
        # could be used to pay for fees and the position would be undercharged
        # if the position is not fully closed
        #
        # for ADLs it may be possible that a position needs to be closed by a larger
        # size to fully pay for fees, but closing by that larger size could cause a PnlOvercorrected
        # error to be thrown in AdlHandler, this case should be rare

        # ! Do not support ADL so ignore any code related to ADL
        collateralCache.isInsolventCloseAllowed = (
            params.order.sizeDeltaUsd == params.position.sizeInUsd and BaseOrderUtils.isLiquidationOrder(params.order.orderType)
        )

        values.priceImpactUsd, values.executionPrice, collateralCache.balanceWasImproved = (
            PositionUtils.getExecutionPriceForDecrease(params, cache.prices.indexTokenPrice, pool_data)
        )

        # the totalPositionPnl is calculated based on the current indexTokenPrice instead of the executionPrice
        # since the executionPrice factors in price impact which should be accounted for separately
        # the sizeDeltaInTokens is calculated as position.sizeInTokens() * sizeDeltaUsd / position.sizeInUsd()
        # the basePnlUsd is the pnl to be realized, and is calculated as:
        # totalPositionPnl * sizeDeltaInTokens / position.sizeInTokens()
        values.basePnlUsd, values.uncappedBasePnlUsd, values.sizeDeltaInTokens = PositionUtils.getPositionPnlUsd(
            cache.prices, params.position, params.order.sizeDeltaUsd, pool_data
        )
        getPositionFeesParams = GetPositionFeesParams(
            position=params.position,
            collateralTokenPrice=cache.collateralTokenPrice,
            balanceWasImproved=collateralCache.balanceWasImproved,
            longToken=pool_data.market.long_token,
            shortToken=pool_data.market.short_token,
            sizeDeltaUsd=params.order.sizeDeltaUsd,
            isLiquidation=BaseOrderUtils.isLiquidationOrder(params.order.orderType),
        )

        # if the pnl is positive, deduct the pnl amount from the pool

        if values.basePnlUsd > 0:
            deductionAmountForPool = values.basePnlUsd / cache.pnlTokenPrice
            if values.output.outputToken == cache.pnlToken:
                values.output.outputAmount += deductionAmountForPool
            else:
                values.output.secondaryOutputAmount += deductionAmountForPool

        # order size has been enforced to be less or equal than position size (i.e. sizeDeltaUsd <= sizeInUsd)
        (values.proportionalPendingImpactAmount, values.proportionalPendingImpactUsd) = (
            DecreasePositionCollateralUtils._getProportionalPendingImpactValues(
                params.position.sizeInUsd,
                params.position.pendingImpactAmount,
                params.order.sizeDeltaUsd,
                cache.prices.indexTokenPrice,
            )
        )

        values.totalImpactUsd = values.proportionalPendingImpactUsd + values.priceImpactUsd

        if values.totalImpactUsd < 0:
            maxPriceImpactFactor = MarketUtils.getMaxPositionImpactFactor(False, pool_data)

            # convert the max price impact to the min negative value
            # e.g. if sizeDeltaUsd is 10,000 and maxPriceImpactFactor is 2%
            # then minPriceImpactUsd = -200
            minPriceImpactUsd = -params.order.sizeDeltaUsd * maxPriceImpactFactor

            # cap totalImpactUsd to the min negative value and store the difference in priceImpactDiffUsd
            # e.g. if totalImpactUsd is -500 and minPriceImpactUsd is -200
            # then set priceImpactDiffUsd to -200 - -500 = 300
            # set totalImpactUsd to -200
            if values.totalImpactUsd < minPriceImpactUsd:
                values.priceImpactDiffUsd = minPriceImpactUsd - values.totalImpactUsd
                values.totalImpactUsd = minPriceImpactUsd

        values.totalImpactUsd = MarketUtils.capPositiveImpactUsdByMaxPositionImpact(
            values.totalImpactUsd, params.order.sizeDeltaUsd, pool_data
        )

        # cap the positive totalImpactUsd by the available amount in the position impact pool
        values.totalImpactUsd = MarketUtils.capPositiveImpactUsdByPositionImpactPool(
            cache.prices, values.totalImpactUsd, pool_data
        )

        if values.totalImpactUsd > 0:
            deductionAmountForImpactPool = values.totalImpactUsd / cache.prices.indexTokenPrice
            # applyDeltaToPositionImpactPool
            deductionAmountForPool = values.totalImpactUsd / cache.pnlTokenPrice
            # applyDeltaToPoolAmount
            if values.output.outputToken == cache.pnlToken:
                values.output.outputAmount += deductionAmountForPool
            else:
                values.output.secondaryOutputAmount += deductionAmountForPool

        # swap profit to the collateral token
        # if the decreasePositionSwapType was set to NoSwap or if the swap fails due
        # to insufficient liquidity or other reasons then it is possible that
        # the profit remains in a different token from the collateral token
        collateralCache.wasSwapped, collateralCache.swapOutputAmount = (
            DecreasePositionSwapUtils.swapProfitToCollateralToken(
                params, cache.pnlToken, values.output.secondaryOutputAmount, pool_data
            )
        )
        if collateralCache.wasSwapped:
            values.output.outputAmount += collateralCache.swapOutputAmount
            values.output.secondaryOutputAmount = 0

        values.remainingCollateralAmount = params.position.collateralAmount

        fees = PositionPricingUtils.getPositionFees(getPositionFeesParams, pool_data)

        # pay for funding fees
        values, collateralCache.result = DecreasePositionCollateralUtils.payForCost(
            params,
            values,
            cache.prices,
            cache.collateralTokenPrice,
            fees.funding.fundingFeeAmount * cache.collateralTokenPrice,
        )

        if collateralCache.result.remainingCostUsd > 0:
            return values, PositionFees()  # handleEarlyReturn

        # pay for negative pnl
        if values.basePnlUsd < 0:
            values, collateralCache.result = DecreasePositionCollateralUtils.payForCost(
                params, values, cache.prices, cache.collateralTokenPrice, -values.basePnlUsd
            )
            if collateralCache.result.remainingCostUsd > 0:
                return values, PositionFees()  # handleEarlyReturn

        # pay for fees
        values, collateralCache.result = DecreasePositionCollateralUtils.payForCost(
            params,
            values,
            cache.prices,
            cache.collateralTokenPrice,
            fees.totalCostAmountExcludingFunding * cache.collateralTokenPrice,
        )
        # if fees were fully paid in the collateral token, update the pool and claimable fee amounts

        if (
            collateralCache.result.remainingCostUsd == 0
            and collateralCache.result.amountPaidInSecondaryOutputToken == 0
        ):
            pass
        else:
            fees = PositionFees()

        if collateralCache.result.remainingCostUsd > 0:
            return values, PositionFees()  # handleEarlyReturn

        # pay for negative price impact
        if values.totalImpactUsd < 0:
            values, collateralCache.result = DecreasePositionCollateralUtils.payForCost(
                params, values, cache.prices, cache.collateralTokenPrice, -values.totalImpactUsd
            )

            if collateralCache.result.remainingCostUsd > 0:
                return values, PositionFees()  # handleEarlyReturn

        # pay for price impact diff
        if values.priceImpactDiffUsd > 0:
            values, collateralCache.result = DecreasePositionCollateralUtils.payForCost(
                params, values, cache.prices, cache.collateralTokenPrice, values.priceImpactDiffUsd
            )
            if collateralCache.result.remainingCostUsd > 0:
                return values, PositionFees()  # handleEarlyReturn

        if params.order.initialCollateralDeltaAmount > 0 and values.priceImpactDiffUsd > 0:
            initialCollateralDeltaAmount = params.order.initialCollateralDeltaAmount
            priceImpactDiffAmount = values.priceImpactDiffUsd / cache.collateralTokenPrice
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
        costUsd: float,
    ) -> tuple[DecreasePositionCollateralValues, PayForCostResult]:
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

        secondaryOutputTokenPrice = MarketUtils.getCachedTokenPrice(
            values.output.secondaryOutputToken, params.market, prices
        )

        remainingCostInSecondaryOutputToken = (
            remainingCostInOutputToken * collateralTokenPrice / secondaryOutputTokenPrice
        )

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

    @staticmethod
    def _getProportionalPendingImpactValues(
        sizeInUsd: float, positionPendingImpactAmount: float, sizeDeltaUsd: float, indexTokenPrice: float
    ) -> tuple[float, float]:
        proportionalPendingImpactAmount = positionPendingImpactAmount * sizeDeltaUsd / sizeInUsd

        # minimize the positive impact, maximize the negative impact
        proportionalPendingImpactUsd = (
            proportionalPendingImpactAmount * indexTokenPrice
            if proportionalPendingImpactAmount > 0
            else proportionalPendingImpactAmount * indexTokenPrice
        )

        return proportionalPendingImpactAmount, proportionalPendingImpactUsd
