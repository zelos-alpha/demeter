from dataclasses import dataclass
from _decimal import Decimal
from enum import Enum
from typing import Dict

from .core import AaveV3CoreLib
from .. import MarketInfo, DECIMAL_0, DemeterError, TokenInfo
from ..broker import MarketBalance, MarketStatus


class InterestRateMode(Enum):
    variable = 1
    stable = 2


@dataclass
class SupplyInfo:
    pool_amount: Decimal
    collateral: bool


@dataclass
class Supply:
    token: TokenInfo
    pool_amount: Decimal
    collateral: bool
    amount: Decimal
    apy: Decimal
    token_base_amount: Decimal


@dataclass
class BorrowInfo:
    pool_amount: Decimal
    interest_rate_mode: InterestRateMode


@dataclass
class Borrow:
    token: TokenInfo
    pool_amount: Decimal
    interest_rate_mode: InterestRateMode
    amount: Decimal
    apy: Decimal
    token_base_amount: Decimal


@dataclass
class AaveBalance(MarketBalance):
    supplys: Dict[TokenInfo, Supply]
    borrows: Dict[TokenInfo, Borrow]

    total_borrows: Decimal
    total_supplies: Decimal
    collateral: Decimal
    net_worth: Decimal

    health_factor: Decimal
    current_ltv: Decimal
    liquidation_threshold: Decimal

    supply_apy: Decimal
    delt_apy: Decimal
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
