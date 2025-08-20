from .PositionUtils import UpdatePositionParams, PositionUtils
from .PositionPricingUtils import GetPositionFeesParams, PositionPricingUtils
from .MarketUtils import MarketUtils
from ._typing import PoolConfig, GmxV2PoolStatus


class IncreasePositionUtils:
    @staticmethod
    def increasePosition(params: UpdatePositionParams, collateralIncrementAmount: float, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        prices = {  # read from csv
            'indexTokenPrice': {'min': pool_status.longPrice, 'max': pool_status.longPrice},
            'longTokenPrice': {'min': pool_status.longPrice, 'max': pool_status.longPrice},
            'shortTokenPrice': {'min': pool_status.shortPrice, 'max': pool_status.shortPrice},
        }
        if params.position.sizeInUsd == 0:
            params.position.fundingFeeAmountPerSize = pool_status.fundingFeeAmountPerSizeLong if params.position.isLong else pool_status.fundingFeeAmountPerSizeShort  # todo from csv
            params.position.longTokenClaimableFundingAmountPerSize = pool_status.longTokenClaimableFundingAmountPerSizeLong if params.position.isLong else pool_status.longTokenClaimableFundingAmountPerSizeShort  # todo from csv
            params.position.shortTokenClaimableFundingAmountPerSize = pool_status.shortTokenClaimableFundingAmountPerSizeLong if params.position.isLong else pool_status.shortTokenClaimableFundingAmountPerSizeShort  # todo from csv
        priceImpactUsd, priceImpactAmount, sizeDeltaInTokens, executionPrice = PositionUtils.getExecutionPriceForIncrease(params, prices['indexTokenPrice']['max'], pool_status, pool_config)
        collateralTokenPrice = prices['shortTokenPrice']['min']  # todo not correct

        collateralDeltaAmount, fees = IncreasePositionUtils.processCollateral(params, collateralTokenPrice, collateralIncrementAmount, priceImpactUsd, pool_status)

        params.position.collateralAmount = params.position.collateralAmount + collateralDeltaAmount
        nextPositionSizeInUsd = params.position.sizeInUsd + params.order.sizeDeltaUsd
        params.position.sizeInUsd = nextPositionSizeInUsd
        params.position.sizeInTokens = params.position.sizeInTokens + sizeDeltaInTokens
        params.position.fundingFeeAmountPerSize = fees.funding.latestFundingFeeAmountPerSize
        params.position.longTokenClaimableFundingAmountPerSize = fees.funding.latestLongTokenClaimableFundingAmountPerSize
        params.position.shortTokenClaimableFundingAmountPerSize = fees.funding.latestShortTokenClaimableFundingAmountPerSize
        nextPositionBorrowingFactor = MarketUtils.getCumulativeBorrowingFactor(params.position.isLong, pool_status)  # todo read from csv
        params.position.borrowingFactor = nextPositionBorrowingFactor

        return params

    @staticmethod
    def processCollateral(params: UpdatePositionParams, collateralTokenPrice: float, collateralDeltaAmount: float, priceImpactUsd: float, pool_status: GmxV2PoolStatus):
        getPositionFeesParams = GetPositionFeesParams(
            position=params.position,
            collateralTokenPrice=collateralTokenPrice,
            forPositiveImpact=priceImpactUsd > 0,
            sizeDeltaUsd=params.order.sizeDeltaUsd,
            isLiquidation=False
        )
        fees = PositionPricingUtils.getPositionFees(getPositionFeesParams, pool_status)
        collateralDeltaAmount -= fees.totalCostAmount
        return collateralDeltaAmount, fees

