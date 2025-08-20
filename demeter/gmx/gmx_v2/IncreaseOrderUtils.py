from .Position import Position
from .SwapUtils import SwapUtils, SwapParams, SwapPricingType
from .IncreasePositionUtils import IncreasePositionUtils
from .PositionUtils import UpdatePositionParams
from ._typing import PoolConfig, GmxV2PoolStatus, ExecuteOrderParams

PositionList = {}


class IncreaseOrderUtils:


    @staticmethod
    def processOrder(params: ExecuteOrderParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        collateralToken, collateralIncrementAmount = SwapUtils.swap(SwapParams(
            params.order.initialCollateralDeltaAmount,
            params.order.initialCollateralToken,
            params.swapPathMarkets,
            SwapPricingType.Swap
        ), pool_status, pool_config)
        positionKey = Position.getPositionKey(params.order.market, collateralToken, params.order.isLong)
        position = PositionList.get(positionKey)
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
            pool_config
        )
        PositionList[positionKey] = increasePositonData.position
