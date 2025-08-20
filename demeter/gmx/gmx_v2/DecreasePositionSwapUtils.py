from .PositionUtils import UpdatePositionParams
from .SwapUtils import SwapUtils, SwapParams, SwapPricingType
from ._typing import GmxV2PoolStatus, PoolConfig, DecreasePositionSwapType


class DecreasePositionSwapUtils:
    @staticmethod
    def swapProfitToCollateralToken(params: UpdatePositionParams, pnlToken: str, profitAmount: float, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        if profitAmount > 0 and params.order.decreasePositionSwapType == DecreasePositionSwapType.SwapPnlTokenToCollateralToken:
            swapPathMarkets = [params.market]
            _, swapOutputAmount = SwapUtils.swap(
                SwapParams(
                    profitAmount,
                    pnlToken,
                    swapPathMarkets,
                    SwapPricingType.Swap
                ),
                pool_status, pool_config
            )
            return True, swapOutputAmount
        else:
            return False, 0
