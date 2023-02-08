from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import NamedTuple

from .. import DemeterError, TokenInfo


@dataclass
class RowData:
    timestamp: datetime = None
    row_id: int = None


class MarketInfo(NamedTuple):
    name: str


class Asset(object):
    """
    Wallet of broker, manage balance of an asset.
    It will prevent excess usage on asset.
    """

    def __init__(self, token: TokenInfo, init_amount=Decimal(0)):
        self.token_info = token
        self.name = token.name
        self.decimal = token.decimal
        self.balance = init_amount

    def __str__(self):
        return f"{self.balance} {self.name}"

    def add(self, amount=Decimal(0)):
        """
        add amount to balance
        :param amount: amount to add
        :type amount: Decimal
        :return: entity itself
        :rtype: BrokerAsset
        """
        self.balance += amount
        return self

    def sub(self, amount=Decimal(0), allow_negative_balance=False):
        """
        subtract amount from balance. if balance is not enough, an error will be raised.

        :param amount: amount to subtract
        :type amount: Decimal
        :param allow_negative_balance: allow balance is negative
        :type allow_negative_balance: bool
        :return:
        :rtype:
        """
        base = self.balance if self.balance != Decimal(0) else Decimal(amount)

        if base == Decimal(0):  # amount and balance is both 0
            return self
        if allow_negative_balance:
            self.balance -= amount
        else:
            # if difference between amount and balance is below 0.01%, will deduct all the balance
            # That's because, the amount calculated by v3_core, has some acceptable error.
            if abs((self.balance - amount) / base) < 0.00001:
                self.balance = Decimal(0)
            elif self.balance - amount < Decimal(0):
                raise DemeterError(f"insufficient balance, balance is {self.balance}{self.name}, "
                                   f"but sub amount is {amount}{self.name}")
            else:
                self.balance -= amount

        return self

    def amount_in_wei(self):
        return self.balance * Decimal(10 ** self.decimal)


class ActionTypeEnum(Enum):
    """
    Trade types

    * add_liquidity = 1,
    * remove_liquidity = 2,
    * buy = 3,
    * sell = 4,
    * collect_fee = 5
    """
    uni_lp_add_liquidity = 1,
    uni_lp_remove_liquidity = 2,
    uni_lp_buy = 3,
    uni_lp_sell = 4,
    uni_lp_collect_fee = 5


@dataclass
class BaseAction(object):
    """
    Parent class of broker actions,

    :param trade_type: action type
    :type action_type: ActionTypeEnum
    :param timestamp: action time
    :type timestamp: datetime

    """
    market: str
    action_type: ActionTypeEnum = field(default=False, init=False)
    timestamp: datetime = field(default=False, init=False)

    def get_output_str(self):
        return str(self)


@dataclass
class MarketStatus:
    net_value: Decimal


@dataclass
class AccountStatus:
    timestamp: datetime
    net_value: Decimal
    asset_balances: {TokenInfo: Decimal}
    market_status: {MarketInfo: MarketStatus}
