from .Position import Position
from .DecreasePositionUtils import DecreasePositionUtils
from .PositionUtils import UpdatePositionParams
from ._typing import GmxV2PoolStatus, PoolConfig, ExecuteOrderParams
from .._typing2 import GmxV2Pool


class DecreaseOrderUtils:

    @staticmethod
    def processOrder(params: ExecuteOrderParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig,
                     pool: GmxV2Pool, positions):
        positionKey = Position.getPositionKey(params.order.market, params.order.initialCollateralToken,
                                              params.order.isLong)
        position = positions.get(positionKey)
        decreasePositonData = DecreasePositionUtils.decreasePosition(UpdatePositionParams(
            params.market,
            params.order,
            position,
            positionKey
        ), pool_status, pool_config, pool)
        return positionKey, decreasePositonData.position
