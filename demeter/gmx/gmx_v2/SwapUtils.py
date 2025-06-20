from dataclasses import dataclass
from typing import List
from .MarketUtils import MarketUtils
from .SwapPricingUtils import SwapPriceUtils, GetPriceImpactUsdParams, SwapPricingType


@dataclass
class Market:
    marketToken: str
    indexToken: str
    longToken: str
    shortToken: str


@dataclass
class SwapParams:
    amountIn: float
    tokenIn: str
    swapPathMarkets: List
    swapPricingType: SwapPricingType


@dataclass
class _SwapParams:
    market: Market
    tokenIn: str
    amountIn: float


class SwapUtils:

    @staticmethod
    def swap(params: SwapParams) -> (str, float):
        if params.amountIn == 0:
            return params.tokenIn, params.amountIn
        tokenOut = params.tokenIn
        outputAmount = params.amountIn
        for i, swapPathMarket in enumerate(params.swapPathMarkets):
            market = swapPathMarket[i]
            nextIndex = i + 1
            if nextIndex < len(params.swapPathMarkets):
                receiver = params.swapPathMarkets[nextIndex].marketToken
            else:
                receiver = params.receiver
            _params = _SwapParams(market, tokenOut, outputAmount, receiver)
            tokenOut, outputAmount = SwapUtils._swap(params, _params)
        return tokenOut, outputAmount

    @staticmethod
    def _swap(params: SwapParams, _params: _SwapParams) -> (float, float):
        tokenOut = MarketUtils.getOppositeToken(_params.tokenIn, _params.market)
        tokenInPrice = 0  # todo read from csv
        tokenOutPrice = 0  # todo read from csv
        priceImpactUsd = SwapPriceUtils.getPriceImpactUsd(GetPriceImpactUsdParams(
            pool_config,
            tokenInPrice,
            tokenOutPrice,
            _params.amountIn * tokenInPrice,
            _params.amountIn * tokenInPrice,
            True,
            True
        ))  # todo
        fees = SwapPriceUtils.getSwapFees(
            pool_config,
            _params.amountIn,
            priceImpactUsd > 0,
            params.swapPricingType
        )
        if priceImpactUsd > 0:
            amountIn = fees.amountAfterFees
            priceImpactAmount, cappedDiffUsd = MarketUtils.applySwapImpactWithCap(tokenOutPrice, priceImpactUsd, pool_status.impactPoolAmount)
            if cappedDiffUsd != 0:
                tokenInPriceImpactAmount, _ = MarketUtils.applySwapImpactWithCap(tokenOutPrice, cappedDiffUsd, pool_status.impactPoolAmount)
                amountIn += tokenInPriceImpactAmount
            amountOut = amountIn * tokenInPrice / tokenOutPrice
            poolAmountOut = amountOut
        else:
            priceImpactAmount, _ = MarketUtils.applySwapImpactWithCap(tokenOutPrice, priceImpactUsd, pool_status.impactPoolAmount)
            amountIn = fees.amountAfterFees - (-priceImpactAmount)
            amountOut = amountIn * tokenInPrice / tokenOutPrice
            poolAmountOut = amountOut
        if _params.receiver != _params.market.marketToken:
            # todo receiver 是另一个market则转给新marekt
            pass
        # todo emit swap info
        return tokenOut, amountOut
