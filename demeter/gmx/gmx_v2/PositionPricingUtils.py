from dataclasses import dataclass
from .MarketUtils import MarketUtils

@dataclass
class GetPositionFeesParams:
    pass

@dataclass
class PositionFees:
    pass

@dataclass
class GetPriceImpactUsdParams:
    pass


class PositionPricingUtils:
    @staticmethod
    def getPriceImpactUsd(params: GetPriceImpactUsdParams):
        pass

    @staticmethod
    def getPositionFees(params: GetPositionFeesParams) -> PositionFees:
        fees = PositionFees()
        borrowingFeeUsd = MarketUtils.getBorrowingFees()
        fees.borrowing = PositionPricingUtils.getBorrowingFees(params.collateralTokenPrice, borrowingFeeUsd)
        if params.isLiquidation:
            fees.liquidation = PositionPricingUtils.getLiquidationFees(params.position.market(), params.sizeDeltaUsd, params.collateralTokenPrice)
        fees.feeAmountForPool = fees.positionFeeAmountForPool + fees.borrowing.borrowingFeeAmount - fees.borrowing.borrowingFeeAmountForFeeReceiver + fees.liquidation.liquidationFeeAmount - fees.liquidation.liquidationFeeAmountForFeeReceiver
        fees.feeReceiverAmount += fees.borrowing.borrowingFeeAmountForFeeReceiver + fees.liquidation.liquidationFeeAmountForFeeReceiver
        fees.funding.latestFundingFeeAmountPerSize = 0  # read from csv
        fees.funding.latestLongTokenClaimableFundingAmountPerSize = 0 # read from csv
        fees.funding.latestShortTokenClaimableFundingAmountPerSize = 0 # read from csv
        fees.funding = PositionPricingUtils.getFundingFees(fees.funding, params.position)
        fees.totalCostAmountExcludingFunding = fees.positionFeeAmount + fees.borrowing.borrowingFeeAmount + fees.liquidation.liquidationFeeAmount
        fees.totalCostAmount = fees.totalCostAmountExcludingFunding + fees.funding.fundingFeeAmount
        return fees

    @staticmethod
    def getBorrowingFees(collateralTokenPrice, borrowingFeeUsd):
        # read from csv
        pass

    @staticmethod
    def getLiquidationFees(market, sizeDeltaUsd, collateralTokenPrice):
        # read from csv
        pass

    @staticmethod
    def getFundingFees(funding, position):
        # read from csv
        pass