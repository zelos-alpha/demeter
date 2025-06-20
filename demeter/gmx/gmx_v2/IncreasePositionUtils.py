from .PositionUtils import UpdatePositionParams, PositionUtils
from .PositionPricingUtils import GetPositionFeesParams, PositionPricingUtils
from .MarketUtils import MarketUtils
from typing import Dict


class IncreasePositionUtils:
    @staticmethod
    def increasePosition(params: UpdatePositionParams, collateralIncrementAmount: float):
        prices = {
            'indexTokenPrice': {'min': 0, 'max': 0},
            'longTokenPrice': {'min': 0, 'max': 0},
            'shortTokenPrice': {'min': 0, 'max': 0},
        }
        if params.position.sizeInUsd() == 0:
            params.position.setFundingFeeAmountPerSize()  # todo from csv
            params.position.setLongTokenClaimableFundingAmountPerSize()  # todo from csv
            params.position.setShortTokenClaimableFundingAmountPerSize()  # todo from csv
        priceImpactUsd, priceImpactAmount, sizeDeltaInTokens, executionPrice = PositionUtils.getExecutionPriceForIncrease(params, prices['indexTokenPrice'])
        collateralTokenPrice = prices['shortTokenPrice']
        collateralDeltaAmount, fees = IncreasePositionUtils.processCollateral(params, collateralTokenPrice, collateralIncrementAmount, priceImpactUsd)
        params.position.setCollateralAmount(params.position.collateralAmount() + collateralDeltaAmount)
        nextPositionSizeInUsd = params.position.sizeInUsd() + params.order.sizeDeltaUsd()
        params.position.setSizeInUsd(nextPositionSizeInUsd)
        params.position.setSizeInTokens(params.position.sizeInTokens() + sizeDeltaInTokens)
        params.position.setFundingFeeAmountPerSize(fees.funding.latestFundingFeeAmountPerSize)
        params.position.setLongTokenClaimableFundingAmountPerSize(fees.funding.latestLongTokenClaimableFundingAmountPerSize)
        params.position.setShortTokenClaimableFundingAmountPerSize(fees.funding.latestShortTokenClaimableFundingAmountPerSize)
        nextPositionBorrowingFactor = MarketUtils.getCumulativeBorrowingFactor()  # todo read from csv
        params.position.setBorrowingFactor(nextPositionBorrowingFactor)

        return params

    @staticmethod
    def processCollateral(params: UpdatePositionParams, collateralTokenPrice: Dict, collateralDeltaAmount: float, priceImpactUsd: float):
        getPositionFeesParams = GetPositionFeesParams()
        fees = PositionPricingUtils.getPositionFees(getPositionFeesParams)
        collateralDeltaAmount -= fees.totalCostAmount
        return collateralDeltaAmount, fees

