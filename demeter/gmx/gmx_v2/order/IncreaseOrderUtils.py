from demeter import TokenInfo
from .._typing import ExecuteOrderParams, GmxV2Pool, PoolData
from ..position.IncreasePositionUtils import IncreasePositionUtils
from ..position.Position import Position
from ..position.PositionUtils import UpdatePositionParams
from ..pricing import PositionFees
from ..swap.SwapUtils import SwapUtils, SwapParams, SwapPricingType


class IncreaseOrderUtils:

    @staticmethod
    def processOrder(
        params: ExecuteOrderParams,
        status: dict[GmxV2Pool, PoolData],
        position: Position | None,
        claimableFundingAmount: dict[TokenInfo, float],
    ) -> tuple[Position, PositionFees]:
        pool_status: PoolData = status[params.market]
        collateralToken, collateralIncrementAmount, _ = SwapUtils.swap(
            SwapParams(
                params.order.initialCollateralDeltaAmount,
                params.order.initialCollateralToken,
                params.swapPathMarkets,
                SwapPricingType.Swap,
            ),
            status,
        )

        if position is None:
            position = Position(params.market, params.order.initialCollateralToken, params.order.isLong)

        increasePositonData, fees = IncreasePositionUtils.increasePosition(
            UpdatePositionParams(params.market, params.order, position, claimableFundingAmount),
            collateralIncrementAmount,
            pool_status,
        )
        return increasePositonData.position, fees
