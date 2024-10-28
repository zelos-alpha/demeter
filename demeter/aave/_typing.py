import pandas as pd
from _decimal import Decimal
from dataclasses import dataclass
from enum import Enum
from typing import Dict, NamedTuple, Union
from typing import TypeVar

from .. import TokenInfo, UnitDecimal
from .._typing import MarketDescription
from ..broker import MarketBalance, MarketStatus, BaseAction, ActionTypeEnum
from ..utils import console_text
from ..utils.console_text import get_action_str, ForColorEnum

T = TypeVar("T")
K = TypeVar("K")


class InterestRateMode(Enum):
    """
    Interest rate mode
    """

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

    :param token: token of this position
    :type token: TokenInfo
    """

    token: TokenInfo
    """token of this position"""

    def __str__(self):
        return self.token.name

    def __hash__(self):
        return self.token.__hash__()


@dataclass
class BorrowKey(ActionKey):
    """
    key of dict for borrow actions

    :param token: token of this position
    :type token: TokenInfo
    :param interest_rate_mode: interest rate mode
    :type interest_rate_mode: InterestRateMode
    """

    interest_rate_mode: InterestRateMode
    """interest rate mode"""

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

    :param token: token of this position
    :type token: TokenInfo
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
    """Base amount of token. Note: base amount is the amount kept in aave contract. its value is amount/liquidity_index"""
    collateral: bool
    """set this supply to collateral or not"""


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
    :param amount: Actual amount at this moment. value is amount * liquidity_index_at_this_moment, unit in token amount, e.g. 1 eth
    :type amount: Decimal
    :param apy: current apy (annual interest rate)
    :type apy: Decimal
    :param value: value at this moment. unit is usd, e.g. 1400 usd
    :type value: Decimal
    """

    token: TokenInfo
    """which token is supplied"""
    base_amount: Decimal
    """Base amount of token. Note: base amount is the amount kept in aave contract. its value is amount/liquidity_index_at_supply_moment"""
    collateral: bool
    """set this supply to collateral or not"""
    amount: Decimal
    """Actual amount at this moment. value is amount * liquidity_index_at_this_moment, unit in token amount, e.g. 1 eth"""
    apy: Decimal
    """current apy (annual interest rate)"""
    value: Decimal
    """value at this moment. unit is usd, e.g. 1400 usd"""


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
        pos_dict["base_amount"].append(console_text.format_value(v.base_amount))
        pos_dict["collateral"].append(v.collateral)
        pos_dict["amount"].append(console_text.format_value(v.amount))
        pos_dict["apy"].append(console_text.format_value(v.apy))
        pos_dict["value"].append((console_text.format_value(v.value)))
    return pd.DataFrame(pos_dict)


@dataclass
class BorrowInfo:
    """
    Basic info for borrow, designed to kept properties inside market

    :param base_amount: Base amount of token. Note: base amount is the amount kept in aave contract. its value is amount/liquidity_index
    :type base_amount: Decimal
    """

    base_amount: Decimal
    """Base amount of token. Note: base amount is the amount kept in aave contract. its value is amount/liquidity_index"""


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
    :param amount: Actual amount at this moment. value is amount * variable_borrow_index_at_this_moment, unit in token amount, e.g. 1 eth
    :type amount: Decimal
    :param apy:  current apy (annual interest rate)
    :type apy: Decimal
    :param value: value at this moment. unit is usd, e.g. 1400 usd
    :type value: Decimal
    """

    token: TokenInfo
    """which token is borrowed"""
    base_amount: Decimal
    """Base amount of token. Note: base amount is the amount kept in aave contract. its value is amount/variable_borrow_index_at_supply_moment"""
    interest_rate_mode: InterestRateMode
    """Interest rate mode"""
    amount: Decimal
    """Actual amount at this moment. value is amount * variable_borrow_index_at_this_moment, unit in token amount, e.g. 1 eth"""
    apy: Decimal
    """current apy (annual interest rate)"""
    value: Decimal
    """value at this moment. unit is usd, e.g. 1400 usd"""


def borrow_to_dataframe(supplies: Dict[BorrowKey, Borrow]) -> pd.DataFrame:
    """
    convert borrow dict to a dataframe

    """
    pos_dict = {
        "token": [],
        "base_amount": [],
        "mode": [],
        "amount": [],
        "apy": [],
        "value": [],
    }
    for k, v in supplies.items():
        pos_dict["token"].append(v.token.name)
        pos_dict["base_amount"].append(console_text.format_value(v.base_amount))
        pos_dict["mode"].append(v.interest_rate_mode.name)
        pos_dict["amount"].append(console_text.format_value(v.amount))
        pos_dict["apy"].append(console_text.format_value(v.apy))
        pos_dict["value"].append(console_text.format_value(v.value))
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
    :param current_ltv: max ltv allowed, in decimal, e.g. 0.7568
    :type current_ltv: Decimal
    :param liquidation_threshold: current liquidation threshold, in decimal, e.g.0.8
    :type liquidation_threshold: Decimal
    :param supply_apy: annual interest rate of supplies
    :type supply_apy: Decimal
    :param borrow_apy: annual interest rate of borrows
    :type borrow_apy: Decimal
    :param net_apy: total annual interest rate of all supplies/borrows
    :type net_apy: Decimal
    """

    supplies_count: int
    """count of supplies"""
    borrows_count: int
    """count of borrows"""
    borrows_value: Decimal
    """total borrow value(in usd)"""
    supplies_value: Decimal
    """total supply value(in usd)"""
    collaterals_value: Decimal
    """total collateral value in supplies(in usd)"""
    health_factor: Decimal
    """current health factor"""
    current_ltv: Decimal
    """max ltv allowed, in decimal, e.g. 0.7568"""
    liquidation_threshold: Decimal
    """current liquidation threshold, in decimal, e.g.0.8"""
    supply_apy: Decimal
    """annual interest rate of supplies"""
    borrow_apy: Decimal
    """annual interest rate of borrows"""
    net_apy: Decimal
    """total annual interest rate of all supplies/borrows"""


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
    """interest rate of supply in a second"""
    stable_borrow_rate: Decimal
    """interest rate of stable borrow in a second"""
    variable_borrow_rate: Decimal
    """interest rate of variable borrow rate in a second"""
    liquidity_index: Decimal
    """Decide supply amount at this moment. consider it's the average interest rate"""
    variable_borrow_index: Decimal
    """Decide borrow amount at this moment. consider it's the average borrow interest rate"""


@dataclass
class AaveMarketStatus(MarketStatus):
    """
    MarketStatus properties

    :param data: pool status
    :type data: Union[pd.Series, AaveTokenStatus]
    """

    data: Union[pd.Series, AaveTokenStatus] = None
    """pool status"""


class RiskParameter:
    """
    | Risk parameter of tokens,
    | It's a column description of dataframe
    | The csv is downloaded from https://www.config.fyi/,
    | Note: some attributes in csv file are excluded.
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
    :type token: str
    :param amount: amount supplied
    :type amount: UnitDecimal
    :param collateral: collateral the supply or not.
    :type collateral: bool
    :param deposit_after: total supply amount of this token after supply
    :type deposit_after: UnitDecimal
    """

    token: str
    """which token is supplied"""
    amount: UnitDecimal
    """amount supplied"""
    collateral: bool
    """collateral the supply or not."""
    deposit_after: UnitDecimal
    """total supply amount of this token after supply"""

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_supply

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.light_green,
            {
                "token": self.token,
                "amount": self.amount.to_str(),
                "collateral": str(self.collateral),
                "deposit_after": self.deposit_after.to_str(),
            },
        )


@dataclass
class WithdrawAction(BaseAction):
    """
    Describe parameters and results of withdraw transaction

    :param token: which token is supplied
    :type token: str
    :param amount: amount supplied
    :type amount: UnitDecimal
    :param deposit_after: total supply amount of this token after withdraw
    :type deposit_after: UnitDecimal
    """

    token: str
    """which token is supplied"""
    amount: UnitDecimal
    """amount supplied"""
    deposit_after: UnitDecimal
    """total supply amount of this token after withdraw"""

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_withdraw

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.light_red,
            {
                "token": self.token,
                "amount": self.amount.to_str(),
                "deposit_after": self.deposit_after.to_str(),
            },
        )


@dataclass
class BorrowAction(BaseAction):
    """
    Describe parameters and results of borrow transaction

    :param token: which token is borrowed
    :type token: str
    :param interest_rate_mode: interest rate mode
    :type interest_rate_mode: InterestRateMode
    :param amount: amount borrowed
    :type amount: UnitDecimal
    :param debt_after: total borrow amount of this token after borrow transaction
    :type debt_after: UnitDecimal
    """

    token: str
    """which token is borrowed"""
    interest_rate_mode: InterestRateMode
    """interest rate mode"""
    amount: UnitDecimal
    """amount borrowed"""
    debt_after: UnitDecimal
    """total borrow amount of this token after borrow transaction"""

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_borrow

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.green,
            {
                "token": self.token,
                "interest_rate_mode": self.interest_rate_mode.name,
                "amount": self.amount.to_str(),
                "debt_after": self.debt_after.to_str(),
            },
        )


@dataclass
class RepayAction(BaseAction):
    """
    Describe parameters and results of RepayAction transaction

    :param token: which token is borrowed
    :type token: str
    :param interest_rate_mode: interest rate mode
    :type interest_rate_mode: InterestRateMode
    :param amount: amount repaid
    :type amount: UnitDecimal
    :param debt_after: total borrow amount of this token after repay transaction
    :type debt_after: UnitDecimal
    """

    token: str
    """which token is borrowed"""
    interest_rate_mode: InterestRateMode
    """interest rate mode"""
    amount: UnitDecimal
    """amount repaid"""
    debt_after: UnitDecimal
    """total borrow amount of this token after repay transaction"""

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_repay

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.red,
            {
                "token": self.token,
                "interest_rate_mode": self.interest_rate_mode.name,
                "amount": self.amount.to_str(),
                "debt_after": self.debt_after.to_str(),
            },
        )


@dataclass
class LiquidationAction(BaseAction):
    """
    Describe parameters and results of a liquidation

    :param collateral_token: which collateral token is used in liquidation
    :type collateral_token: str
    :param debt_token:  which debt token is used in liquidation
    :type debt_token: str
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

    collateral_token: str
    """which collateral token is used in liquidation"""
    debt_token: str
    """which debt token is used in liquidation"""
    delt_to_cover: UnitDecimal
    """Debt amount to be liquidated, should be equal to variable_delt_liquidated+stable_delt_liquidated"""
    collateral_used: UnitDecimal
    """Collateral amount to subtract in liquidation"""
    variable_delt_liquidated: UnitDecimal
    """liquidated debt token amount in variable delt"""
    stable_delt_liquidated: UnitDecimal
    """liquidated debt token amount in stable delt"""
    health_factor_before: Decimal
    """health factor before liquidation"""
    health_factor_after: Decimal
    """health factor after liquidation"""
    collateral_after: UnitDecimal
    """collateral token amount after liquidation"""
    variable_debt_after: UnitDecimal
    """variable debt token amount after liquidation"""
    stable_delt_after: UnitDecimal
    """stable delt token amount after liquidation"""

    def set_type(self):
        self.action_type = ActionTypeEnum.aave_repay

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.yellow,
            {
                "collateral_token": self.collateral_token,
                "debt_token": self.debt_token,
                "delt_to_cover": self.delt_to_cover.to_str(),
                "collateral_used": self.collateral_used.to_str(),
                "liquidated": f"variable:{self.variable_delt_liquidated.to_str()} stable:{self.stable_delt_liquidated.to_str()}",
                "health_factor": f"{self.health_factor_before}->{self.health_factor_after}",
                "collateral_after": self.collateral_after.to_str(),
                "variable_debt_after": self.variable_debt_after.to_str(),
                "stable_delt_after": self.stable_delt_after.to_str(),
            },
        )


class DictCache:
    """
    A cache class in dictionary. It uses dict for storage.
    """

    def __init__(self):
        self.empty = True
        self._value: Dict[K, T] = {}

    @property
    def value(self) -> Dict[K, T]:
        """
        Get dict in this cache instance.
        """
        return self._value

    def get(self, k: K) -> T:
        """
        Get value from cache.

        :param k: key
        :type k: K
        :return: value
        :rtype: T
        """
        return self._value[k]

    def reset(self):
        """
        Reset cache instance, will set values to empty.
        """
        self._value: Dict[K, T] = {}
        self.empty = True

    def set(self, k: K, v: T):
        """
        Set value to dict

        :param k: key
        :type k: K
        :param v: value
        :type v: T
        """
        self._value[k] = v
        self.empty = False

@dataclass
class AaveDescription(MarketDescription):
    """
    Designed to generate json description for aave market

    :param type: market type
    :type type: str
    :param name: market name
    :type name: str
    :param supplies_count: count of supplies
    :type supplies_count: int
    :param borrows_count: count of borrows
    :type borrows_count: int
    """

    supplies_count: int
    """count of supplies"""
    borrows_count: int
    """count of borrows"""
