from . import PoolConfig
from ._typing import ExecuteOrderParams
from .SwapUtils import SwapUtils, SwapParams, SwapPricingType
from .._typing2 import GmxV2PoolStatus


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
