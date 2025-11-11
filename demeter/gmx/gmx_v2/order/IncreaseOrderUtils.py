from demeter.gmx.gmx_v2.position.Position import Position
from demeter.gmx.gmx_v2.swap.SwapUtils import SwapUtils, SwapParams, SwapPricingType
from demeter.gmx.gmx_v2.position.IncreasePositionUtils import IncreasePositionUtils
from demeter.gmx.gmx_v2.position.PositionUtils import UpdatePositionParams
from demeter.gmx.gmx_v2._typing import PoolConfig, GmxV2PoolStatus, ExecuteOrderParams
from demeter.gmx._typing2 import GmxV2Pool


class IncreaseOrderUtils:


    @staticmethod
    def processOrder(params: ExecuteOrderParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig, pool: GmxV2Pool, positions):
        collateralToken, collateralIncrementAmount = SwapUtils.swap(SwapParams(
            params.order.initialCollateralDeltaAmount,
            params.order.initialCollateralToken,
            params.swapPathMarkets,
            SwapPricingType.Swap
        ), pool_status, pool_config)
        positionKey = Position.getPositionKey(params.order.market, collateralToken, params.order.isLong)
        position = positions.get(positionKey)
        if position is None:
            # init market collateral token
            position = Position(
                market=params.order.market,
                collateralToken=collateralToken,
                isLong=params.order.isLong
            )

        increasePositonData = IncreasePositionUtils.increasePosition(
            UpdatePositionParams(
                params.market,
                params.order,
                position,
                positionKey
            ),
            collateralIncrementAmount,
            pool_status,
            pool_config,
            pool
        )
        return positionKey, increasePositonData.position
