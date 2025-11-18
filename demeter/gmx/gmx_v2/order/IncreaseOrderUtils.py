from ..position.Position import Position
from ..swap.SwapUtils import SwapUtils, SwapParams, SwapPricingType
from ..position.IncreasePositionUtils import IncreasePositionUtils
from ..position.PositionUtils import UpdatePositionParams
from .._typing import PoolConfig, GmxV2PoolStatus, ExecuteOrderParams, GmxV2Pool, PoolData


class IncreaseOrderUtils:

    @staticmethod
    def processOrder(params: ExecuteOrderParams, status: dict[GmxV2Pool, PoolData], position: Position | None):
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

        increasePositonData = IncreasePositionUtils.increasePosition(
            UpdatePositionParams(params.market, params.order, position),
            collateralIncrementAmount,
            pool_status
        )
        return increasePositonData.position
