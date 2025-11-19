from .._typing import PoolData
from ..market.MarketUtils import MarketUtils, MarketPrices
from ..position.PositionUtils import UpdatePositionParams, PositionUtils
from ..pricing.PositionPricingUtils import GetPositionFeesParams, PositionPricingUtils, PositionFees


class IncreasePositionUtils:
    @staticmethod
    def increasePosition(
        params: UpdatePositionParams,
        collateralIncrementAmount: float,
        pool_data: PoolData,
    ) -> tuple[UpdatePositionParams, PositionFees]:
        pool = params.order.market
        prices = MarketPrices(
            indexTokenPrice=pool_data.status.indexPrice,
            longTokenPrice=pool_data.status.longPrice,
            shortTokenPrice=pool_data.status.shortPrice,
        )
        collateralTokenPrice = MarketUtils.getCachedTokenPrice(params.order.initialCollateralToken, pool, prices)
        if params.position.sizeInUsd == 0:
            params.position.fundingFeeAmountPerSize = MarketUtils.getFundingFeeAmountPerSize(
                params.position.collateralToken, params.position.isLong, pool_data
            )
            params.position.longTokenClaimableFundingAmountPerSize = MarketUtils.getClaimableFundingAmountPerSize(
                pool.long_token, params.position.isLong, pool_data
            )
            params.position.shortTokenClaimableFundingAmountPerSize = MarketUtils.getClaimableFundingAmountPerSize(
                pool.short_token, params.position.isLong, pool_data
            )
        priceImpactUsd, priceImpactAmount, sizeDeltaInTokens, executionPrice, balanceWasImproved = (
            PositionUtils.getExecutionPriceForIncrease(params, prices, pool_data)
        )

        # process the collateral for the given position and order
        collateralDeltaAmount, fees = IncreasePositionUtils.processCollateral(
            params, collateralTokenPrice, collateralIncrementAmount, balanceWasImproved, pool_data
        )

        params.position.collateralAmount = params.position.collateralAmount + collateralDeltaAmount

        # Instead of applying the delta to the pool, store it using the positionKey
        # No need to flip the priceImpactAmount sign since it isn't applied to the pool, it's just stored
        params.position.pendingImpactAmount += priceImpactAmount

        nextPositionSizeInUsd = params.position.sizeInUsd + params.order.sizeDeltaUsd
        nextPositionBorrowingFactor = MarketUtils.getCumulativeBorrowingFactor(params.position.isLong, pool_data.status)

        PositionUtils.incrementClaimableFundingAmount(params, fees)

        params.position.sizeInUsd = nextPositionSizeInUsd
        params.position.sizeInTokens = params.position.sizeInTokens + sizeDeltaInTokens

        params.position.fundingFeeAmountPerSize = fees.funding.latestFundingFeeAmountPerSize
        params.position.longTokenClaimableFundingAmountPerSize = (
            fees.funding.latestLongTokenClaimableFundingAmountPerSize
        )
        params.position.shortTokenClaimableFundingAmountPerSize = (
            fees.funding.latestShortTokenClaimableFundingAmountPerSize
        )

        params.position.borrowingFactor = nextPositionBorrowingFactor

        # skip update open interest

        # skip validation

        return params, fees

    @staticmethod
    def processCollateral(
        params: UpdatePositionParams,
        collateralTokenPrice: float,
        collateralDeltaAmount: float,
        balanceWasImproved: bool,
        pool_status: PoolData,
    ) -> tuple[float, PositionFees]:
        getPositionFeesParams = GetPositionFeesParams(
            position=params.position,
            collateralTokenPrice=collateralTokenPrice,
            balanceWasImproved=balanceWasImproved,
            sizeDeltaUsd=params.order.sizeDeltaUsd,
            longToken=pool_status.market.long_token,
            shortToken=pool_status.market.short_token,
            isLiquidation=False,
        )
        fees = PositionPricingUtils.getPositionFees(getPositionFeesParams, pool_status)
        collateralDeltaAmount -= fees.totalCostAmount
        return collateralDeltaAmount, fees
