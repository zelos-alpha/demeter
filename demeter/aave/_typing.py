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
    """Interest rate mode"""

    variable = 1
    stable = 2

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


@dataclass
class ActionKey:
    """
    Abstract key for actions(supply, borrow, etc.)
    """

    token: TokenInfo

    def __str__(self):
        return self.token.name

    def __hash__(self):
        return self.token.__hash__()


@dataclass
class BorrowKey(ActionKey):
    """
    key of dict for borrow actions
    """

    interest_rate_mode: InterestRateMode

    def __str__(self):
        return f"Borrow_{self.token.name}({self.interest_rate_mode.name})"

    def __repr__(self):
        return f"Borrow_{self.token.name}({self.interest_rate_mode.name})"

    def __hash__(self):
        return hash((self.token, self.interest_rate_mode))


@dataclass
class SupplyKey(ActionKey):
    """
    key of dict for supply actions

    """

    def __str__(self):
        return "Supply_" + self.token.name

    def __repr__(self):
        return "Supply_" + self.token.name

    def __hash__(self):
        return self.token.__hash__()


@dataclass
class SupplyInfo:
    """
    Basic info for supply, designed to kept properties inside market

    :param base_amount: Base amount of token. Note: base amount is the amount kept in aave contract. its value is amount/liquidity_index
    :type base_amount: Decimal
    :param collateral: set this supply to collateral or not
    :type collateral: bool

    """

    base_amount: Decimal
    collateral: bool


@dataclass
class Supply:
    """
    Supply info, designed to show supplies to user

    :param token: which token is supplied
    :type token: TokenInfo
    :param base_amount: Base amount of token. Note: base amount is the amount kept in aave contract. its value is amount/liquidity_index_at_supply_moment
    :type base_amount: Decimal
    :param collateral: set this supply to collateral or not
    :type collateral: bool
    :param amount: Actual amount at this moment. value is amount * liquidity_index_at_this_moment, unit in token amount, eg: 1 eth
    :type amount: Decimal
    :param apy: current apy (annual interest rate)
    :type apy: Decimal
    :param value: value at this moment. unit is usd, eg: 1400 usd
    :type value: Decimal
    """

    token: TokenInfo
    base_amount: Decimal
    collateral: bool
    amount: Decimal
    apy: Decimal
    value: Decimal


def supply_to_dataframe(supplies: Dict[SupplyKey, Supply]) -> pd.DataFrame:
    """
    convert supply dict to a dataframe
    """
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
    """
    Basic info for borrow, designed to kept properties inside market

    :param base_amount: Base amount of token. Note: base amount is the amount kept in aave contract. its value is amount/liquidity_index
    :type base_amount: Decimal
    """

    base_amount: Decimal


@dataclass
class Borrow:
    """
    borrow info, designed to show borrows to user

    :param token: which token is borrowed
    :type token: TokenInfo
    :param base_amount: Base amount of token. Note: base amount is the amount kept in aave contract. its value is amount/variable_borrow_index_at_supply_moment
    :type base_amount: Decimal
    :param interest_rate_mode: Interest rate mode
    :type interest_rate_mode: InterestRateMode
    :param amount: Actual amount at this moment. value is amount * variable_borrow_index_at_this_moment, unit in token amount, eg: 1 eth
    :type amount: Decimal
    :param apy:  current apy (annual interest rate)
    :type apy: Decimal
    :param value: value at this moment. unit is usd, eg: 1400 usd
    :type value: Decimal
    """

    token: TokenInfo
    base_amount: Decimal
    interest_rate_mode: InterestRateMode
    amount: Decimal
    apy: Decimal
    value: Decimal


def borrow_to_dataframe(supplies: Dict[BorrowKey, Borrow]) -> pd.DataFrame:
    """
    convert borrow dict to a dataframe

    """
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
    """
    Asset or position value in aave market.

    :param supplies_count: count of supplies
    :type supplies_count: int
    :param borrows_count: count of borrows
    :type borrows_count: int
    :param borrows_value: total borrow value(in usd)
    :type borrows_value: Decimal
    :param supplies_value: total supply value(in usd)
    :type supplies_value: Decimal
    :param collaterals_value: total collateral value in supplies(in usd)
    :type collaterals_value: Decimal
    :param health_factor: current health factor
    :type health_factor: Decimal
    :param current_ltv: max ltv allowed, in decimal, eg: 0.7568
    :type current_ltv: Decimal
    :param liquidation_threshold: current liquidation threshold, in decimal, eg:0.8
    :type liquidation_threshold: Decimal
    :param supply_apy: annual interest rate of supplies
    :type supply_apy: Decimal
    :param borrow_apy: annual interest rate of borrows
    :type borrow_apy: Decimal
    :param net_apy: total annual interest rate of all supplies/borrows
    :type net_apy: Decimal
    """

    supplies_count: int
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
    """
    Aave pool status of one token. Usually they are got form ReserveDataUpdated event of aave pool. Consider it's the transient interest rates

    :param liquidity_rate: interest rate of supply in a second
    :type liquidity_rate: Decimal
    :param stable_borrow_rate: interest rate of stable borrow in a second
    :type stable_borrow_rate: Decimal
    :param variable_borrow_rate: interest rate of variable borrow rate in a second
    :type variable_borrow_rate: Decimal
    :param liquidity_index: Decide supply amount at this moment. consider it's the average interest rate
    :type liquidity_index: Decimal
    :param variable_borrow_index: Decide borrow amount at this moment. consider it's the average borrow interest rate
    :type variable_borrow_index: Decimal
    """

    liquidity_rate: Decimal
    stable_borrow_rate: Decimal
    variable_borrow_rate: Decimal
    liquidity_index: Decimal
    variable_borrow_index: Decimal


@dataclass
class AaveMarketStatus(MarketStatus):
    """
    MarketStatus properties

    :param data: pool status
    :type data: Union[pd.Series, AaveTokenStatus]
    """

    data: Union[pd.Series, AaveTokenStatus] = None


class RiskParameter:
    """
    Risk parameter of tokens,
    It's a column description of dataframe
    The csv is downloaded from https://www.config.fyi/,
    Note: some attributes in csv file are excluded.
    """
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
    """
    Describe parameters and results of supply transaction

    :param token: which token is supplied
    :type token: TokenInfo
    :param amount: amount supplied
    :type amount: UnitDecimal
    :param collateral: collateral the supply or not.
    :type collateral: bool
    :param deposit_after: total supply amount of this token after supply
    :type deposit_after: UnitDecimal
    """
    token: TokenInfo
    amount: UnitDecimal
    collateral: bool
    deposit_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_supply


@dataclass
class WithdrawAction(BaseAction):
    """
    Describe parameters and results of withdraw transaction

    :param token: which token is supplied
    :type token: TokenInfo
    :param amount: amount supplied
    :type amount: UnitDecimal
    :param deposit_after: total supply amount of this token after withdraw
    :type deposit_after: UnitDecimal
    """
    token: TokenInfo
    amount: UnitDecimal
    deposit_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_withdraw


@dataclass
class BorrowAction(BaseAction):
    """
    Describe parameters and results of borrow transaction

    :param token: which token is borrowed
    :type token: TokenInfo
    :param interest_rate_mode: interest rate mode
    :type interest_rate_mode: InterestRateMode
    :param amount: amount borrowed
    :type amount: UnitDecimal
    :param debt_after: total borrow amount of this token after borrow transaction
    :type debt_after: UnitDecimal
    """
    token: TokenInfo
    interest_rate_mode: InterestRateMode
    amount: UnitDecimal
    debt_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_borrow


@dataclass
class RepayAction(BaseAction):
    """
    Describe parameters and results of RepayAction transaction

    :param token: which token is borrowed
    :type token: TokenInfo
    :param interest_rate_mode: interest rate mode
    :type interest_rate_mode: InterestRateMode
    :param amount: amount repaid
    :type amount: UnitDecimal
    :param debt_after: total borrow amount of this token after repay transaction
    :type debt_after: UnitDecimal
    """
    token: TokenInfo
    interest_rate_mode: InterestRateMode
    amount: UnitDecimal
    debt_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_repay


@dataclass
class LiquidationAction(BaseAction):
    """
    Describe parameters and results of a liquidation

    :param collateral_token: which collateral token is used in liquidation
    :type collateral_token: TokenInfo
    :param debt_token:  which debt token is used in liquidation
    :type debt_token: TokenInfo
    :param delt_to_cover: Debt amount to be liquidated, should be equal to variable_delt_liquidated+stable_delt_liquidated
    :type delt_to_cover: UnitDecimal
    :param collateral_used: Collateral amount to subtract in liquidation
    :type collateral_used: UnitDecimal
    :param variable_delt_liquidated: liquidated debt token amount in variable delt
    :type variable_delt_liquidated: UnitDecimal
    :param stable_delt_liquidated: liquidated debt token amount in stable delt
    :type stable_delt_liquidated: UnitDecimal
    :param health_factor_before: health factor before liquidation
    :type health_factor_before: UnitDecimal
    :param health_factor_after: health factor after liquidation
    :type health_factor_after: UnitDecimal
    :param collateral_after: collateral token amount after liquidation
    :type collateral_after: UnitDecimal
    :param variable_debt_after: variable debt token amount after liquidation
    :type variable_debt_after: UnitDecimal
    :param stable_delt_after: stable delt token amount after liquidation
    :type stable_delt_after: UnitDecimal
    """
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
    """
    A cache class in dictionary
    """
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
    """
    Designed to generate json description for aave market
    """
    type: str
    name: str
    supplies_count: int
    borrows_count: int
