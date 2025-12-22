from dataclasses import dataclass
from typing import List

from demeter import TokenInfo
from .._typing import PoolData, GmxV2Pool
from ..market.MarketUtils import MarketUtils
from ..pricing.SwapPricingUtils import SwapPriceUtils, GetPriceImpactUsdParams, SwapPricingType


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


@dataclass
class SwapResult:
    outToken: TokenInfo
    outAmount: float
    feeToken: TokenInfo
    fee: float
    priceImpactToken: TokenInfo
    priceImpact: float
    priceImpactUsd: float


class SwapUtils:

    @staticmethod
    def swap(params: SwapParams, status: dict[GmxV2Pool, PoolData]) -> tuple[TokenInfo, float, list[SwapResult]]:
        if params.amountIn == 0 or len(params.swapPathMarkets) == 0:
            return params.tokenIn, params.amountIn, []
        tokenOut = params.tokenIn
        outputAmount = params.amountIn
        swapResult: List[SwapResult] = []
        for market in params.swapPathMarkets:
            _params = _SwapParams(market, tokenOut, outputAmount)
            swapResult.append(SwapUtils._swap(params, _params, status[market]))
        return swapResult[-1].outToken, swapResult[-1].outAmount, swapResult

    @staticmethod
    def _swap(params: SwapParams, _params: _SwapParams, status: PoolData) -> SwapResult:
        tokenOut: TokenInfo = MarketUtils.getOppositeToken(_params.tokenIn, _params.market)
        tokenInPrice = (
            status.status.longPrice if _params.tokenIn == _params.market.long_token else status.status.shortPrice
        )
        tokenOutPrice = (
            status.status.shortPrice if _params.tokenIn == _params.market.long_token else status.status.longPrice
        )
        priceImpactUsd, balanceWasImproved = SwapPriceUtils.getPriceImpactUsd(
            GetPriceImpactUsdParams(
                status.config,
                tokenInPrice,
                tokenOutPrice,
                _params.amountIn * tokenInPrice,
                -_params.amountIn * tokenInPrice,
                True,
                _params.tokenIn == _params.market.long_token,
            ),
            status.status,
        )
        fees = SwapPriceUtils.getSwapFees(status.config, _params.amountIn, balanceWasImproved, params.swapPricingType)
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
            amountOut += priceImpactAmount
            priceImpactToken = tokenOut
        else:
            priceImpactAmount, _ = MarketUtils.applySwapImpactWithCap(
                tokenInPrice, priceImpactUsd, status.status.impactPoolAmount
            )
            amountIn = fees.amountAfterFees - (-priceImpactAmount)
            amountOut = amountIn * tokenInPrice / tokenOutPrice
            priceImpactToken = _params.tokenIn
        return SwapResult(
            tokenOut, amountOut, _params.tokenIn, fees.totalFee, priceImpactToken, priceImpactAmount, priceImpactUsd
        )
