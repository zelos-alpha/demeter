from ..position.PositionUtils import UpdatePositionParams, PositionUtils
from ..pricing.PositionPricingUtils import GetPositionFeesParams, PositionPricingUtils
from ..market.MarketUtils import MarketUtils, MarketPrices, Price
from .._typing import PoolConfig, GmxV2PoolStatus, GmxV2Pool, PoolData


class IncreasePositionUtils:
    @staticmethod
    def increasePosition(
        params: UpdatePositionParams,
        collateralIncrementAmount: float,
        pool_status: PoolData,
    ):
        pool = params.order.market
        prices = MarketPrices(
            indexTokenPrice=pool_status.status.indexPrice,
            longTokenPrice=pool_status.status.longPrice,
            shortTokenPrice=pool_status.status.shortPrice,
        )
        if params.position.sizeInUsd == 0:
            params.position.fundingFeeAmountPerSize = MarketUtils.getFundingFeeAmountPerSize(
                params.position.collateralToken, params.position.isLong, pool, pool_status.status
            )
            params.position.longTokenClaimableFundingAmountPerSize = MarketUtils.getClaimableFundingAmountPerSize(
                pool.long_token, params.position.isLong, pool, pool_status.status
            )
            params.position.shortTokenClaimableFundingAmountPerSize = MarketUtils.getClaimableFundingAmountPerSize(
                pool.short_token, params.position.isLong, pool, pool_status.status
            )
        priceImpactUsd, priceImpactAmount, sizeDeltaInTokens, executionPrice, balanceWasImproved = (
            PositionUtils.getExecutionPriceForIncrease(params, prices, pool_status)
        )



        # process the collateral for the given position and order
        collateralTokenPrice = (
            prices["shortTokenPrice"]["min"]
            if params.position.collateralToken == pool.short_token
            else prices["longTokenPrice"]["min"]
        )

        collateralDeltaAmount, fees = IncreasePositionUtils.processCollateral(
            params, collateralTokenPrice, collateralIncrementAmount, priceImpactUsd, pool_status, pool_config, pool
        )

        params.position.collateralAmount = params.position.collateralAmount + collateralDeltaAmount
        nextPositionSizeInUsd = params.position.sizeInUsd + params.order.sizeDeltaUsd
        params.position.sizeInUsd = nextPositionSizeInUsd
        params.position.sizeInTokens = params.position.sizeInTokens + sizeDeltaInTokens
        params.position.fundingFeeAmountPerSize = fees.funding.latestFundingFeeAmountPerSize
        params.position.longTokenClaimableFundingAmountPerSize = (
            fees.funding.latestLongTokenClaimableFundingAmountPerSize
        )
        params.position.shortTokenClaimableFundingAmountPerSize = (
            fees.funding.latestShortTokenClaimableFundingAmountPerSize
        )
        nextPositionBorrowingFactor = MarketUtils.getCumulativeBorrowingFactor(
            params.position.isLong, pool_status
        )  # todo read from csv
        params.position.borrowingFactor = nextPositionBorrowingFactor

        return params

    @staticmethod
    def processCollateral(
        params: UpdatePositionParams,
        collateralTokenPrice: float,
        collateralDeltaAmount: float,
        priceImpactUsd: float,
        pool_status: GmxV2PoolStatus,
        pool_config: PoolConfig,
        pool: GmxV2Pool,
    ):
        getPositionFeesParams = GetPositionFeesParams(
            position=params.position,
            collateralTokenPrice=collateralTokenPrice,
            forPositiveImpact=priceImpactUsd > 0,
            sizeDeltaUsd=params.order.sizeDeltaUsd,
            isLiquidation=False,
        )
        fees = PositionPricingUtils.getPositionFees(getPositionFeesParams, pool_status, pool_config, pool)
        collateralDeltaAmount -= fees.totalCostAmount
        return collateralDeltaAmount, fees
