from demeter import TokenInfo, DemeterError
from .._typing import DecreasePositionSwapType, PoolData
from .PositionUtils import UpdatePositionParams, DecreasePositionCollateralValues
from ..swap.SwapUtils import SwapUtils, SwapParams, SwapPricingType


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
                SwapParams(
                    amountIn=profitAmount,
                    tokenIn=pnlToken,
                    swapPathMarkets=swapPathMarkets,
                    swapPricingType=SwapPricingType.Swap,
                ),
                {pool_data.market: pool_data},
            )
            return True, swapOutputAmount
        else:
            return False, 0

    @staticmethod
    def swapWithdrawnCollateralToPnlToken(
        params: UpdatePositionParams,
        values: DecreasePositionCollateralValues,
        pool_data: PoolData,
    ) -> DecreasePositionCollateralValues:
        if (
            values.output.outputAmount > 0
            and params.order.decreasePositionSwapType == DecreasePositionSwapType.SwapCollateralTokenToPnlToken
        ):
            swapPathMarkets = [params.market]
            tokenOut, swapOutputAmount, _ = SwapUtils.swap(
                SwapParams(
                    values.output.outputAmount, params.position.collateralToken, swapPathMarkets, SwapPricingType.Swap
                ),
                {pool_data.market: pool_data},
            )
            if tokenOut != values.output.secondaryOutputToken:
                raise DemeterError("InvalidOutputToken")
            values.output.outputToken = tokenOut
            values.output.outputAmount = values.output.secondaryOutputAmount + swapOutputAmount
            values.output.secondaryOutputAmount = 0
        return values
