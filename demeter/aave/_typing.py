from _decimal import Decimal
from dataclasses import dataclass
from enum import Enum
from typing import Dict, NamedTuple, Union
from typing import TypeVar

import pandas as pd

from .. import TokenInfo, UnitDecimal
from ..broker import MarketBalance, MarketStatus, BaseAction, ActionTypeEnum

T = TypeVar("T")
K = TypeVar("K")


class InterestRateMode(Enum):
    variable = 1
    stable = 2

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


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
        return f"Borrow_{self.token.name}({self.interest_rate_mode.name})"

    def __repr__(self):
        return f"Borrow_{self.token.name}({self.interest_rate_mode.name})"

    def __hash__(self):
        return hash((self.token, self.interest_rate_mode))


@dataclass
class SupplyKey(ActionKey):
    def __str__(self):
        return "Supply_" + self.token.name

    def __repr__(self):
        return "Supply_" + self.token.name

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


def supply_to_dataframe(supplies: Dict[SupplyKey, Supply]) -> pd.DataFrame:
    pos_dict = {
        "token": [],
        "base_amount": [],
        "collateral": [],
        "amount": [],
        "apy": [],
        "value": [],
    }
    for k, v in supplies.items():
        pos_dict["token"].append(v.token.name)
        pos_dict["base_amount"].append(v.base_amount)
        pos_dict["collateral"].append(v.collateral)
        pos_dict["amount"].append(v.amount)
        pos_dict["apy"].append(v.apy)
        pos_dict["value"].append(v.value)
    return pd.DataFrame(pos_dict)


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


def borrow_to_dataframe(supplies: Dict[BorrowKey, Borrow]) -> pd.DataFrame:
    pos_dict = {
        "token": [],
        "base_amount": [],
        "interest_rate_mode": [],
        "amount": [],
        "apy": [],
        "value": [],
    }
    for k, v in supplies.items():
        pos_dict["token"].append(v.token.name)
        pos_dict["base_amount"].append(v.base_amount)
        pos_dict["interest_rate_mode"].append(v.interest_rate_mode.name)
        pos_dict["amount"].append(v.amount)
        pos_dict["apy"].append(v.apy)
        pos_dict["value"].append(v.value)
    return pd.DataFrame(pos_dict)


@dataclass
class AaveBalance(MarketBalance):
    supplys_count: int
    borrows_count: int

    borrows_value: Decimal
    supplies_value: Decimal
    collaterals_value: Decimal

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
class AaveMarketStatus(MarketStatus):
    """
    MarketStatus properties

    :type timestamp: datetime
    """

    data: Union[pd.Series, AaveTokenStatus] = None


# @dataclass
# class AaveV3PoolStatus:
#     """
#     current status of a pool, actuators can notify current status to broker by filling this entity
#     """
#
#     tokens: Dict[TokenInfo, AaveTokenStatus]


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


@dataclass
class SupplyAction(BaseAction):
    token: TokenInfo
    amount: UnitDecimal
    collateral: bool
    deposit_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_supply


@dataclass
class WithdrawAction(BaseAction):
    token: TokenInfo
    amount: UnitDecimal
    deposit_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_withdraw


@dataclass
class BorrowAction(BaseAction):
    token: TokenInfo
    interest_rate_mode: InterestRateMode
    amount: UnitDecimal
    debt_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_borrow


@dataclass
class RepayAction(BaseAction):
    token: TokenInfo
    interest_rate_mode: InterestRateMode
    amount: UnitDecimal
    debt_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_repay


@dataclass
class LiquidationAction(BaseAction):
    collateral_token: TokenInfo
    debt_token: TokenInfo
    delt_to_cover: UnitDecimal
    collateral_used: UnitDecimal
    variable_delt_liquidated: UnitDecimal
    stable_delt_liquidated: UnitDecimal
    health_factor_before: Decimal
    health_factor_after: Decimal
    collateral_after: UnitDecimal
    variable_debt_after: UnitDecimal
    stable_delt_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_repay


class DictCache:
    def __init__(self):
        self.empty = True
        self._data: Dict[K, T] = {}

    @property
    def data(self) -> Dict[K, T]:
        return self._data

    def reset(self):
        self._data: Dict[K, T] = {}
        self.empty = True

    def set(self, k: K, v: T):
        self._data[k] = v
        self.empty = False


class AaveMarketDescription(NamedTuple):
    type: str
    name: str
    supplies_count: int
    borrows_count: int
