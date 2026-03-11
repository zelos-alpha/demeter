from dataclasses import dataclass
from ._typing import Market


@dataclass
class Position:
    market: str = ''
    collateralToken: str = ''
    sizeInUsd: float = 0.0
    sizeInTokens: float = 0.0
    collateralAmount: float = 0.0
    borrowingFactor: float = 0.0
    fundingFeeAmountPerSize: float = 0.0
    longTokenClaimableFundingAmountPerSize: float = 0.0
    shortTokenClaimableFundingAmountPerSize: float = 0.0
    isLong: bool = False

    @staticmethod
    def getPositionKey(_market: str, _collateralToken: str, _isLong: bool):
        return f'{_market}-{_collateralToken}-{_isLong}'
