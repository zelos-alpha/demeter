from dataclasses import dataclass
from typing import NamedTuple

from demeter import TokenInfo
from .._typing import GmxV2Pool


class PositionKey(NamedTuple):
    market: GmxV2Pool
    collateral_token: TokenInfo
    is_long: bool


@dataclass
class Position:
    market: GmxV2Pool | None
    collateralToken: TokenInfo | None
    isLong: bool
    sizeInUsd: float = 0.0
    sizeInTokens: float = 0.0
    collateralAmount: float = 0.0
    pendingImpactAmount: float = 0.0
    borrowingFactor: float = 0.0
    fundingFeeAmountPerSize: float = 0.0
    longTokenClaimableFundingAmountPerSize: float = 0.0
    shortTokenClaimableFundingAmountPerSize: float = 0.0

    @staticmethod
    def getPositionKey(_market: GmxV2Pool, _collateralToken: TokenInfo, _isLong: bool) -> PositionKey:
        return PositionKey(_market, _collateralToken, _isLong)
