from demeter.gmx.gmx_v2 import PoolConfig
from demeter.gmx.gmx_v2._typing import ExecuteOrderParams
from demeter.gmx.gmx_v2.swap.SwapUtils import SwapUtils, SwapParams, SwapPricingType
from demeter.gmx._typing2 import GmxV2PoolStatus


class SwapOrderUtils:

    @staticmethod
    def processOrder(params: ExecuteOrderParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        outputToken, outputAmount = SwapUtils.swap(SwapParams(
            amountIn=params.order.initialCollateralDeltaAmount,
            tokenIn=params.order.initialCollateralToken,
            swapPathMarkets=params.swapPathMarkets,
            swapPricingType=SwapPricingType.Swap
        ), pool_status, pool_config)
        return outputToken, outputAmount
