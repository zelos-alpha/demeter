from dataclasses import dataclass
from typing import List

from demeter import TokenInfo
from ..market.MarketUtils import MarketUtils
from ..pricing.SwapPricingUtils import SwapPriceUtils, GetPriceImpactUsdParams, SwapPricingType
from .._typing import PoolConfig, GmxV2PoolStatus, PoolStatus, GmxV2Pool


@dataclass
class SwapParams:
    amountIn: float
    tokenIn: TokenInfo
    swapPathMarkets: list[GmxV2Pool]
    swapPricingType: SwapPricingType


@dataclass
class _SwapParams:
    market: GmxV2Pool
    tokenIn: TokenInfo
    amountIn: float


class SwapUtils:

    @staticmethod
    def swap(params: SwapParams, status: dict[GmxV2Pool, PoolStatus]) -> tuple[TokenInfo, float]:
        if params.amountIn == 0:
            return params.tokenIn, params.amountIn
        tokenOut = params.tokenIn
        outputAmount = params.amountIn
        for market in params.swapPathMarkets:
            _params = _SwapParams(market, tokenOut, outputAmount)
            tokenOut, outputAmount = SwapUtils._swap(params, _params, status[market])
        return tokenOut, outputAmount

    @staticmethod
    def _swap(params: SwapParams, _params: _SwapParams, status: PoolStatus) -> tuple[TokenInfo, float]:
        tokenOut: TokenInfo = MarketUtils.getOppositeToken(_params.tokenIn, _params.market)
        tokenInPrice = (
            status.status.longPrice if _params.tokenIn == _params.market.long_token else status.status.shortPrice
        )
        tokenOutPrice = (
            status.status.shortPrice if _params.tokenIn == _params.market.long_token else status.status.longPrice
        )
        priceImpactUsd = SwapPriceUtils.getPriceImpactUsd(
            GetPriceImpactUsdParams(
                status.config,
                tokenInPrice,
                tokenOutPrice,
                _params.amountIn * tokenInPrice,
                -_params.amountIn * tokenInPrice,
                True,
                True,
            ),
            status.status,
        )
        fees = SwapPriceUtils.getSwapFees(status.config, _params.amountIn, priceImpactUsd > 0, params.swapPricingType)
        if priceImpactUsd > 0:
            amountIn = fees.amountAfterFees
            priceImpactAmount, cappedDiffUsd = MarketUtils.applySwapImpactWithCap(
                tokenOutPrice, priceImpactUsd, status.status.impactPoolAmount
            )
            if cappedDiffUsd != 0:
                tokenInPriceImpactAmount, _ = MarketUtils.applySwapImpactWithCap(
                    tokenOutPrice, cappedDiffUsd, status.status.impactPoolAmount
                )
                amountIn += tokenInPriceImpactAmount
            amountOut = amountIn * tokenInPrice / tokenOutPrice
        else:
            priceImpactAmount, _ = MarketUtils.applySwapImpactWithCap(
                tokenInPrice, priceImpactUsd, status.status.impactPoolAmount
            )
            amountIn = fees.amountAfterFees - (-priceImpactAmount)
            amountOut = amountIn * tokenInPrice / tokenOutPrice
        return tokenOut, amountOut
        # TODO: return fee/price impact
