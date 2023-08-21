from dataclasses import dataclass
from _decimal import Decimal
from enum import Enum
from typing import Dict

from .core import AaveV3CoreLib
from .. import MarketInfo, DECIMAL_0, DemeterError, TokenInfo
from ..broker import MarketBalance


class BorrowRateType(Enum):
    variable = 1
    stable = 2


@dataclass
class Supply:
    token: TokenInfo
    pool_amount: Decimal
    is_deposit: bool
    amount: Decimal


@dataclass
class Borrow:
    token: TokenInfo
    pool_amount: Decimal
    rate_type: BorrowRateType
    amount: Decimal


@dataclass
class AaveBalance(MarketBalance):
    supplys: Dict[TokenInfo, Supply]
    borrows: Dict[TokenInfo, Borrow]
    health_factor: Decimal
    current_tlv: Decimal
    supply_apy: Decimal
    delt_apy: Decimal
