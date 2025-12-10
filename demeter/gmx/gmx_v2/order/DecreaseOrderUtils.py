from demeter import TokenInfo
from .._typing import ExecuteOrderParams, GmxV2Pool, PoolData
from ..position.DecreasePositionUtils import DecreasePositionUtils, DecreasePositionResult
from ..position.Position import Position
from ..position.PositionUtils import UpdatePositionParams
from ..pricing import PositionFees


class DecreaseOrderUtils:

    @staticmethod
    def processOrder(
        params: ExecuteOrderParams,
        status: dict[GmxV2Pool, PoolData],
        position: Position,
        claimableFundingAmount: dict[TokenInfo, float],
    ) -> tuple[DecreasePositionResult, PositionFees]:

        result, fees = DecreasePositionUtils.decreasePosition(
            UpdatePositionParams(
                params.market,
                params.order,
                position,
                claimableFundingAmount,
            ),
            status[params.market],
        )

        # skip transfer out tokens
        return result, fees
