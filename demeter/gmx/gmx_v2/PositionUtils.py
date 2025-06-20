from dataclasses import dataclass
from typing import Dict, List, Optional
from .PositionPricingUtils import PositionPricingUtils, GetPriceImpactUsdParams
from .MarketUtils import MarketUtils


@dataclass
class UpdatePositionParams:
    market: str
    order: Dict
    position: Dict
    positionKey: str


class PositionUtils:
    @staticmethod
    def getExecutionPriceForIncrease(params, UpdatePositionParams, indexTokenPrice: Dict):
        if params.order.sizeDeltaUsd() == 0:
            return 0, 0, 0, indexTokenPrice['min']
        priceImpactUsd = PositionPricingUtils.getPriceImpactUsd(GetPriceImpactUsdParams())
        # priceImpactUsd = MarketUtils.getCappedPositionImpactUsd()  #
        priceImpactAmount = 0
        if priceImpactUsd > 0:
            priceImpactAmount = priceImpactUsd / indexTokenPrice.max
        else:
            priceImpactAmount = priceImpactUsd / indexTokenPrice.min

        baseSizeDeltaInTokens = 0
        if params.position.isLong():
            baseSizeDeltaInTokens = params.order.sizeDeltaUsd() / indexTokenPrice.max
        else:
            baseSizeDeltaInTokens = params.order.sizeDeltaUsd() / indexTokenPrice.min
        sizeDeltaInTokens = 0
        if params.position.isLong():
            sizeDeltaInTokens = baseSizeDeltaInTokens + priceImpactAmount
        else:
            sizeDeltaInTokens = baseSizeDeltaInTokens - priceImpactAmount
        executionPrice = PositionUtils._getExecutionPriceForIncrease(
            params.order.sizeDeltaUsd(),
            sizeDeltaInTokens,
            params.order.acceptablePrice(),
            params.position.isLong()
        )
        return priceImpactUsd, priceImpactAmount, sizeDeltaInTokens, executionPrice


    @staticmethod
    def _getExecutionPriceForIncrease(sizeDeltaUsd, sizeDeltaInTokens, acceptablePrice, isLong):
        executionPrice = sizeDeltaUsd / sizeDeltaInTokens
        if (isLong and executionPrice <= acceptablePrice) or (not isLong and executionPrice >= acceptablePrice):
            return executionPrice

