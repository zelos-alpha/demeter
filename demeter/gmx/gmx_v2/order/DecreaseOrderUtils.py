from demeter.gmx.gmx_v2.position.Position import Position
from demeter.gmx.gmx_v2.position.DecreasePositionUtils import DecreasePositionUtils
from demeter.gmx.gmx_v2.position.PositionUtils import UpdatePositionParams
from demeter.gmx.gmx_v2._typing import GmxV2PoolStatus, PoolConfig, ExecuteOrderParams
from demeter.gmx._typing2 import GmxV2Pool


class DecreaseOrderUtils:

    @staticmethod
    def processOrder(params: ExecuteOrderParams, pool_status: GmxV2PoolStatus, pool_config: PoolConfig,
                     pool: GmxV2Pool, positions):
        positionKey = Position.getPositionKey(params.order.market, params.order.initialCollateralToken,
                                              params.order.isLong)
        position = positions.get(positionKey)
        decreasePosition, outputToken, outputAmount, secondaryOutputToken, secondaryOutputAmount, _, _ = DecreasePositionUtils.decreasePosition(UpdatePositionParams(
            params.market,
            params.order,
            position,
            positionKey
        ), pool_status, pool_config, pool)
        return positionKey, decreasePosition, outputToken, outputAmount, secondaryOutputToken, secondaryOutputAmount
