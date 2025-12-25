from demeter import TokenInfo
from .._typing import ExecuteOrderParams, GmxV2Pool, PoolData
from ..position import (
    DecreasePositionUtils,
    DecreasePositionResult,
    Position,
    UpdatePositionParams,
    DecreasePositionCollateralValues,
)
from ..pricing import PositionFees


class DecreaseOrderUtils:

    @staticmethod
    def processOrder(
        params: ExecuteOrderParams,
        status: dict[GmxV2Pool, PoolData],
        position: Position,
        claimableFundingAmount: dict[TokenInfo, float],
    ) -> tuple[DecreasePositionResult, DecreasePositionCollateralValues, PositionFees]:

        result, values, fees = DecreasePositionUtils.decreasePosition(
            UpdatePositionParams(
                params.market,
                params.order,
                position,
                claimableFundingAmount,
            ),
            status[params.market],
        )

        # skip transfer out tokens
        return result, values, fees
