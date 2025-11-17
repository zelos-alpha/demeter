from demeter import TokenInfo
from demeter.gmx.gmx_v2._typing import ExecuteOrderParams, PoolStatus, GmxV2Pool
from demeter.gmx.gmx_v2.swap.SwapUtils import SwapUtils, SwapParams, SwapPricingType, SwapResult


class SwapOrderUtils:

    @staticmethod
    def processOrder(
        params: ExecuteOrderParams, status: dict[GmxV2Pool, PoolStatus]
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
