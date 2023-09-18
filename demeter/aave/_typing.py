from _decimal import Decimal
from dataclasses import dataclass
from enum import Enum
from typing import Dict

from .. import TokenInfo
from ..broker import MarketBalance, MarketStatus


class InterestRateMode(Enum):
    variable = 1
    stable = 2


@dataclass
class ActionKey:
    token: TokenInfo

    def __str__(self):
        return self.token.name

    def __hash__(self):
        return self.token.__hash__()


@dataclass
class BorrowKey(ActionKey):
    interest_rate_mode: InterestRateMode

    def __str__(self):
        return f"{self.token.name}({self.interest_rate_mode.name})"

    def __repr__(self):
        return f"{self.token.name}({self.interest_rate_mode.name})"

    def __hash__(self):
        return hash((self.token, self.interest_rate_mode))


@dataclass
class SupplyKey(ActionKey):
    def __str__(self):
        return self.token.name

    def __repr__(self):
        return self.token.name

    def __hash__(self):
        return self.token.__hash__()


@dataclass
class SupplyInfo:
    base_amount: Decimal
    collateral: bool


@dataclass
class Supply:
    token: TokenInfo
    base_amount: Decimal
    collateral: bool
    amount: Decimal
    apy: Decimal
    value: Decimal


@dataclass
class BorrowInfo:
    base_amount: Decimal


@dataclass
class Borrow:
    token: TokenInfo
    base_amount: Decimal
    interest_rate_mode: InterestRateMode
    amount: Decimal
    apy: Decimal
    value: Decimal


@dataclass
class AaveBalance(MarketBalance):
    supplys: Dict[SupplyKey, Supply]
    borrows: Dict[BorrowKey, Borrow]

    borrow_balance: Decimal
    supply_balance: Decimal
    collateral_balance: Decimal

    health_factor: Decimal
    current_ltv: Decimal
    liquidation_threshold: Decimal

    supply_apy: Decimal
    borrow_apy: Decimal
    net_apy: Decimal


@dataclass
class AaveTokenStatus:
    liquidity_rate: Decimal
    stable_borrow_rate: Decimal
    variable_borrow_rate: Decimal
    liquidity_index: Decimal
    variable_borrow_index: Decimal


@dataclass
class AaveV3PoolStatus(MarketStatus):
    """
    current status of a pool, actuators can notify current status to broker by filling this entity
    """

    tokens: Dict[TokenInfo, AaveTokenStatus]


class RiskParameter:
    symbol: str
    canCollateral: bool
    LTV: float
    liqThereshold: float
    liqBonus: float
    reserveFactor: float
    canBorrow: bool
    optimalUtilization: float
    canBorrowStable: bool
    debtCeiling: float
    supplyCap: float
    borrowCap: float
    eModeLtv: float
    eModeLiquidationThereshold: float
    eModeLiquidationBonus: float
    borrowableInIsolation: float
