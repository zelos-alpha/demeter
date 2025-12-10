from demeter import TokenInfo
from .._typing import ExecuteOrderParams, PoolData, GmxV2Pool
from ..swap.SwapUtils import SwapUtils, SwapParams, SwapPricingType, SwapResult


class SwapOrderUtils:

    @staticmethod
    def processOrder(
        params: ExecuteOrderParams, status: dict[GmxV2Pool, PoolData]
    ) -> tuple[TokenInfo, float, list[SwapResult]]:
        return SwapUtils.swap(
            SwapParams(
                amountIn=params.order.initialCollateralDeltaAmount,
                tokenIn=params.order.initialCollateralToken,
                swapPathMarkets=params.swapPathMarkets,
                swapPricingType=SwapPricingType.Swap,
            ),
            status,
        )
