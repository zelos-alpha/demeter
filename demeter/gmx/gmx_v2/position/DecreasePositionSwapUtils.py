from demeter import TokenInfo, DemeterError
from demeter.gmx.gmx_v2.position.PositionUtils import UpdatePositionParams, DecreasePositionCollateralValues
from demeter.gmx.gmx_v2.swap.SwapUtils import SwapUtils, SwapParams, SwapPricingType
from demeter.gmx.gmx_v2._typing import GmxV2PoolStatus, PoolConfig, DecreasePositionSwapType, PoolData


class DecreasePositionSwapUtils:
    @staticmethod
    def swapProfitToCollateralToken(
        params: UpdatePositionParams,
        pnlToken: TokenInfo,
        profitAmount: float,
        pool_data: PoolData,
    ):
        if (
            profitAmount > 0
            and params.order.decreasePositionSwapType == DecreasePositionSwapType.SwapPnlTokenToCollateralToken
        ):
            swapPathMarkets = [params.market]
            _, swapOutputAmount, _ = SwapUtils.swap(
                SwapParams(profitAmount, pnlToken, swapPathMarkets, SwapPricingType.Swap), {pool_data.market: pool_data}
            )
            return True, swapOutputAmount
        else:
            return False, 0

    @staticmethod
    def swapWithdrawnCollateralToPnlToken(
        params: UpdatePositionParams,
        values: DecreasePositionCollateralValues,
        pool_data: PoolData,
    )->DecreasePositionCollateralValues:
        if (
            values.output.outputAmount > 0
            and params.order.decreasePositionSwapType == DecreasePositionSwapType.SwapCollateralTokenToPnlToken
        ):
            swapPathMarkets = [params.market]
            tokenOut, swapOutputAmount, _ = SwapUtils.swap(
                SwapParams(values.output.outputAmount, params.position.collateralToken, swapPathMarkets, SwapPricingType.Swap), {pool_data.market: pool_data}
            )
            if tokenOut != values.output.secondaryOutputToken:
                raise DemeterError("InvalidOutputToken")
            values.output.outputToken = tokenOut
            values.output.outputAmount = values.output.secondaryOutputAmount + swapOutputAmount
            values.output.secondaryOutputAmount = 0
        return values
