from dataclasses import dataclass

from demeter import DemeterError, TokenInfo
from .BaseOrderUtils import BaseOrderUtils
from .DecreasePositionSwapUtils import DecreasePositionSwapUtils
from .DecreasePositionCollateralUtils import DecreasePositionCollateralUtils

from .Position import Position
from .._typing import PoolData, OrderType, DecreasePositionSwapType
from ..market.MarketUtils import MarketPrices, MarketUtils
from ..position.PositionUtils import (
    PositionUtils,
    WillPositionCollateralBeSufficientValues,
    DecreasePositionCollateralValues,
)
from ..position.PositionUtils import UpdatePositionParams, DecreasePositionCache
from ..pricing import PositionFees


@dataclass
class DecreasePositionResult:
    outputToken: TokenInfo
    outputAmount: float
    secondaryOutputToken: TokenInfo
    secondaryOutputAmount: float
    orderSizeDeltaUsd: float
    orderInitialCollateralDeltaAmount: float
    position: Position | None


class DecreasePositionUtils:
    @staticmethod
    def decreasePosition(
        params: UpdatePositionParams,
        pool_data: PoolData,
    ) -> tuple[DecreasePositionResult, DecreasePositionCollateralValues, PositionFees]:
        pool = params.order.market
        cache: DecreasePositionCache = DecreasePositionCache()
        cache.prices = MarketPrices(
            indexTokenPrice=pool_data.status.indexPrice,
            longTokenPrice=pool_data.status.longPrice,
            shortTokenPrice=pool_data.status.shortPrice,
        )
        cache.collateralTokenPrice = MarketUtils.getCachedTokenPrice(
            params.order.initialCollateralToken, pool_data.market, cache.prices
        )
        # cap the order size to the position size
        if params.order.sizeDeltaUsd > params.position.sizeInUsd:
            if (
                params.order.orderType == OrderType.LimitDecrease
                or params.order.orderType == OrderType.StopLossDecrease
            ):
                params.order.sizeDeltaUsd = params.position.sizeInUsd
            else:
                raise DemeterError(
                    f"InvalidDecreaseOrderSize, sizeDeltaUsd: {params.order.sizeDeltaUsd}, sizeInUsd: { params.position.sizeInUsd}"
                )
        # cap the initialCollateralDeltaAmount to the position collateralAmount
        if params.order.initialCollateralDeltaAmount > params.position.collateralAmount:
            params.order.initialCollateralDeltaAmount = params.position.collateralAmount

        # if the position will be partially decreased then do a check on the
        # remaining collateral amount and update the order attributes if needed
        if params.order.sizeDeltaUsd < params.position.sizeInUsd:
            cache.estimatedPositionPnlUsd, _, _ = PositionUtils.getPositionPnlUsd(
                cache.prices, params.position, params.position.sizeInUsd, pool_data
            )
            cache.estimatedRealizedPnlUsd = (
                cache.estimatedPositionPnlUsd * params.order.sizeDeltaUsd / params.position.sizeInUsd
            )
            cache.estimatedRemainingPnlUsd = cache.estimatedPositionPnlUsd - cache.estimatedRealizedPnlUsd

            positionValues = WillPositionCollateralBeSufficientValues(
                positionSizeInUsd=params.position.sizeInUsd - params.order.sizeDeltaUsd,
                positionCollateralAmount=params.position.collateralAmount - params.order.initialCollateralDeltaAmount,
                realizedPnlUsd=cache.estimatedRealizedPnlUsd,
                openInterestDelta=-params.order.sizeDeltaUsd,
            )
            willBeSufficient, estimatedRemainingCollateralUsd = PositionUtils.willPositionCollateralBeSufficient(
                cache.prices,
                params.order.initialCollateralToken,
                params.position.isLong,
                positionValues,
                pool_data,
            )
            cache.minCollateralUsd = pool_data.config.minCollateralUsd

            # do not allow withdrawal of collateral if it would lead to the position
            # having an insufficient amount of collateral
            # this helps to prevent gaming by opening a position then reducing collateral
            # to increase the leverage of the position
            #
            # alternatively, if the estimatedRemainingCollateralUsd + estimatedRemainingPnlUsd will be less
            # than minCollateralUsd, then set the initialCollateralDeltaAmount to zero as well
            # in the subsequent check, the position size may be updated to fully close the position
            # due to the above condition, so adding the collateral back here can help avoid the position
            # being fully closed
            if (not willBeSufficient) or (
                estimatedRemainingCollateralUsd + cache.estimatedRemainingPnlUsd < cache.minCollateralUsd
            ):
                if params.order.sizeDeltaUsd == 0:
                    raise DemeterError("UnableToWithdrawCollateral")

                # the estimatedRemainingCollateralUsd subtracts the initialCollateralDeltaAmount
                # since the initialCollateralDeltaAmount will be set to zero, the initialCollateralDeltaAmount
                # should be added back to the estimatedRemainingCollateralUsd
                estimatedRemainingCollateralUsd += (
                    params.order.initialCollateralDeltaAmount * cache.collateralTokenPrice
                )
                params.order.initialCollateralDeltaAmount = 0

            # if the remaining collateral including position pnl will be below
            # the min collateral usd value, then close the position
            #
            # if the position has sufficient remaining collateral including pnl
            # then allow the position to be partially closed and the updated
            # position to remain open
            if estimatedRemainingCollateralUsd + cache.estimatedRemainingPnlUsd < cache.minCollateralUsd:
                params.order.sizeDeltaUsd = params.position.sizeInUsd

            if (
                params.position.sizeInUsd > params.order.sizeDeltaUsd
                and (params.position.sizeInUsd - params.order.sizeDeltaUsd) < pool_data.config.minPositionSizeUsd
            ):
                params.order.sizeDeltaUsd = params.position.sizeInUsd

        if params.order.sizeDeltaUsd == params.position.sizeInUsd and params.order.initialCollateralDeltaAmount > 0:
            params.order.initialCollateralDeltaAmount = 0

        cache.pnlToken = pool.long_token if params.position.isLong else pool.short_token
        cache.pnlTokenPrice = cache.prices.longTokenPrice if params.position.isLong else cache.prices.shortTokenPrice

        if (params.order.decreasePositionSwapType != DecreasePositionSwapType.NoSwap) and (
            cache.pnlToken == params.position.collateralToken
        ):
            params.order.decreasePositionSwapType = DecreasePositionSwapType.NoSwap

        if BaseOrderUtils.isLiquidationOrder(params.order.orderType):
            isLiquidatable, reason, info = PositionUtils.isPositionLiquidatable(
                params.position, cache.prices, True, True, pool_data
            )
            if not isLiquidatable:
                raise DemeterError(
                    f"PositionShouldNotBeLiquidated, {reason}, "
                    f"remainingCollateralUsd: {info.remainingCollateralUsd}, "
                    f"minCollateralUsd: {info.minCollateralUsd}, "
                    f"minCollateralUsdForLeverage: {info.minCollateralUsdForLeverage}"
                )

        cache.initialCollateralAmount = params.position.collateralAmount

        values, fees = DecreasePositionCollateralUtils.processCollateral(params, cache, pool_data)

        nextPositionSizeInUsd = params.position.sizeInUsd - params.order.sizeDeltaUsd
        nextPositionBorrowingFactor = MarketUtils.getCumulativeBorrowingFactor(params.position.isLong, pool_data.status)

        # updateTotalBorrowing

        params.position.sizeInUsd = nextPositionSizeInUsd
        params.position.sizeInTokens = params.position.sizeInTokens - values.sizeDeltaInTokens
        params.position.collateralAmount = values.remainingCollateralAmount
        params.position.pendingImpactAmount = (
            params.position.pendingImpactAmount - values.proportionalPendingImpactAmount
        )

        # incrementClaimableFundingAmount
        # applyDeltaToTotalPendingImpactAmount

        if params.position.sizeInUsd == 0 or params.position.sizeInTokens == 0:
            values.output.outputAmount += params.position.collateralAmount
            params.position.sizeInUsd = 0
            params.position.sizeInTokens = 0
            params.position.collateralAmount = 0
            position_is_empty = True
        else:
            params.position.borrowingFactor = nextPositionBorrowingFactor
            params.position.fundingFeeAmountPerSize = fees.funding.latestFundingFeeAmountPerSize
            params.position.longTokenClaimableFundingAmountPerSize = (
                fees.funding.latestLongTokenClaimableFundingAmountPerSize
            )
            params.position.shortTokenClaimableFundingAmountPerSize = (
                fees.funding.latestShortTokenClaimableFundingAmountPerSize
            )
            position_is_empty = False
        # applyDeltaToCollateralSum
        # updateOpenInterest
        # handleReferral
        if params.position.sizeInUsd != 0 or params.position.sizeInTokens != 0:
            # validate position which validates liquidation state is only called
            # if the remaining position size is not zero
            # due to this, a user can still manually close their position if
            # it is in a partially liquidatable state
            # this should not cause any issues as a liquidation is the same
            # as automatically closing a position
            # the only difference is that if the position has insufficient / negative
            # collateral a liquidation transaction should still complete
            # while a manual close transaction should revert
            PositionUtils.validatePosition(params.position, cache.prices, False, False, pool_data)

        values = DecreasePositionSwapUtils.swapWithdrawnCollateralToPnlToken(params, values, pool_data)
        return (
            DecreasePositionResult(
                outputToken=values.output.outputToken,
                outputAmount=values.output.outputAmount,
                secondaryOutputToken=values.output.secondaryOutputToken,
                secondaryOutputAmount=values.output.secondaryOutputAmount,
                orderSizeDeltaUsd=params.order.sizeDeltaUsd,
                orderInitialCollateralDeltaAmount=params.order.initialCollateralDeltaAmount,
                position=None if position_is_empty else params.position,
            ),
            values,
            fees,
        )
