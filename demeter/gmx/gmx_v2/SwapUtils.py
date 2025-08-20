from dataclasses import dataclass
from typing import List
from .MarketUtils import MarketUtils
from .SwapPricingUtils import SwapPriceUtils, GetPriceImpactUsdParams, SwapPricingType
from ._typing import PoolConfig, GmxV2PoolStatus


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
    def swap(params: SwapParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig) -> (str, float):  # done
        if params.amountIn == 0:
            return params.tokenIn, params.amountIn
        tokenOut = params.tokenIn
        outputAmount = params.amountIn
        for i, swapPathMarket in enumerate(params.swapPathMarkets):
            market = swapPathMarket[i]
            _params = _SwapParams(market, tokenOut, outputAmount)
            tokenOut, outputAmount = SwapUtils._swap(params, _params, pool_status, pool_config)
        return tokenOut, outputAmount

    @staticmethod
    def _swap(params: SwapParams, _params: _SwapParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig) -> (float, float): # done
        tokenOut = MarketUtils.getOppositeToken(_params.tokenIn, _params.market)
        tokenInPrice = pool_status.longPrice if _params.tokenIn == _params.market.longToken else pool_status.shortPrice
        tokenOutPrice = pool_status.shortPrice if _params.tokenIn == _params.market.longToken else pool_status.longPrice
        priceImpactUsd = SwapPriceUtils.getPriceImpactUsd(GetPriceImpactUsdParams(
            pool_config,
            tokenInPrice,
            tokenOutPrice,
            _params.amountIn * tokenInPrice,
            _params.amountIn * tokenInPrice,
            True,
            True
        ), pool_status)
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
        else:
            priceImpactAmount, _ = MarketUtils.applySwapImpactWithCap(tokenOutPrice, priceImpactUsd, pool_status.impactPoolAmount)
            amountIn = fees.amountAfterFees - (-priceImpactAmount)
            amountOut = amountIn * tokenInPrice / tokenOutPrice
        return tokenOut, amountOut
