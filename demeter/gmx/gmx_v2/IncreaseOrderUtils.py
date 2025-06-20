from .ExecuteOrderUtils import ExecuteOrderParams
from .Position import Position
from .SwapUtils import SwapUtils, SwapParams, SwapPricingType
from .IncreasePositionUtils import IncreasePositionUtils
from .PositionUtils import UpdatePositionParams

PositionList = {}


class IncreaseOrderUtils:


    @staticmethod
    def processOrder(params: ExecuteOrderParams):
        collateralToken, collateralIncrementAmount = SwapUtils.swap(SwapParams(
            params.order.initialCollateralDeltaAmount(),
            params.order.initialCollateralToken(),
            params.swapPathMarkets,
            SwapPricingType.Swap
        ))
        positionKey = Position.getPositionKey(params.order.market(), collateralToken, params.order.isLong())
        position = PositionList.get(positionKey)
        if position is None:
            # init market collateral token
            position = {}
            position['market'] = params.order.market()
            position['collateralToken'] = collateralToken
            position['isLong'] = params.order.isLong()

        increasePositonData = IncreasePositionUtils.increasePosition(
            UpdatePositionParams(
                params.market,
                params.order,
                position,
                positionKey
            ),
            collateralIncrementAmount
        )
        PositionList[positionKey] = increasePositonData.position
