import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Generic, NamedTuple, List, Dict, TypeVar

import pandas as pd

from .._typing import DemeterError, TokenInfo

T = TypeVar("T")


class Rule(NamedTuple):
    """
    Rule properties
    """

    agg: str | None
    fillna_method: str | None
    fillna_value: int | None


# @dataclass
# class RowData:
#     """
#     Row properties
#     """
#
#     timestamp: datetime = None
#     row_id: int = None


class MarketTypeEnum(Enum):
    uniswap = 1
    aave_v3 = 2


class MarketInfo(NamedTuple):
    """
    MarketInfo properties
    """

    name: str  # uni_market
    type: MarketTypeEnum = MarketTypeEnum.uniswap

    def __str__(self):
        return f"{self.name}({self.type.name})"

    def __repr__(self):
        return f"{self.name}({self.type.name})"


class AssetDescription(NamedTuple):
    name: str
    value: float


class Asset(object):
    """
    Wallet of broker, manage balance of an asset.
    It will prevent excess usage on asset.
    """

    def __init__(self, token: TokenInfo, init_amount=Decimal(0)):
        """
        initialization of Asset
        :param token: token info
        :param init_amount: initialization amount, default 0
        """
        self.token_info = token
        self.name = token.name
        self.decimal = token.decimal
        self.balance = init_amount

    def __str__(self):
        """
        return Asset info
        :return: Asset info with name && balance
        """
        return json.dumps(self.description()._asdict())

    def __repr__(self):
        """
        return Asset info
        :return: Asset info with name && balance
        """
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
                raise AssertionError(f"insufficient balance, balance is {self.balance}{self.name}, " f"but sub amount is {amount}{self.name}")
            else:
                self.balance -= amount

        return self

    def amount_in_wei(self):
        """
        return balance ** decimal

        :return: self.balance * 10 ** self.decimal
        """
        return self.balance * Decimal(10**self.decimal)

    def description(self) -> AssetDescription:
        return AssetDescription(self.name, float(self.balance))


class ActionTypeEnum(Enum):
    """
    Trade types

    * add_liquidity,
    * remove_liquidity,
    * buy,
    * sell,
    * collect_fee
    """

    uni_lp_add_liquidity = "add_liquidity"
    uni_lp_remove_liquidity = "remove_liquidity"
    uni_lp_buy = "buy"
    uni_lp_sell = "sell"
    uni_lp_collect = "collect"
    aave_supply = "supply"
    aave_withdraw = "withdraw"
    aave_borrow = "borrow"
    aave_repay = "repay"
    aave_liquidation = "liquidation"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


@dataclass
class BaseAction(object):
    """
    Parent class of broker actions,

    :param market: market
    :type market: MarketInfo
    :param action_type: action type
    :type action_type: ActionTypeEnum
    :param timestamp: action time
    :type timestamp: datetime

    """

    market: MarketInfo
    action_type: ActionTypeEnum = field(default=False, init=False)
    timestamp: datetime = field(default=False, init=False)

    def get_output_str(self):
        return str(self)

    def set_type(self):
        pass


@dataclass
class MarketBalance:
    """
    MarketBalance properties

    :type net_value: Decimal
    """

    net_value: Decimal


@dataclass
class AccountStatusCommon:
    """
    AccountStatusCommon properties

    :type timestamp: datetime
    :type net_value: Decimal, default 0
    """

    timestamp: datetime
    net_value: Decimal = Decimal(0)


@dataclass
class MarketStatus:
    """
    MarketStatus properties

    :type timestamp: datetime
    """

    timestamp: datetime | None
    data: pd.Series = None


T = TypeVar("T")


class MarketDict(Generic[T]):
    """
    Market Dict with get/set function
    """

    def __init__(self):
        self.data: Dict[MarketInfo, T] = {}
        self._default: MarketInfo | None = None

    def __getitem__(self, item) -> T:
        return self.data[item]

    def __setitem__(self, key: MarketInfo, value: T):
        if len(self.data) == 0:
            self._default = key
        self.data[key] = value
        setattr(self, key.name, value)

    @property
    def default(self) -> T:
        """
        get default value in MarketDict
        :return:
        """
        return self.data[self._default]

    def get_default_key(self):
        """
        get default key
        :return:
        """
        return self._default

    def set_default_key(self, value: MarketInfo):
        """
        set default key
        :param value:
        :return:
        """
        self._default = value

    def items(self) -> (List[MarketInfo], List[T]):
        """
        get dict items
        :return:
        """
        return self.data.items()

    def keys(self) -> List[MarketInfo]:
        """
        get dict keys
        :return:
        """
        return self.data.keys()

    def values(self) -> List[T]:
        """
        get dict values
        :return:
        """
        return self.data.values()

    def __contains__(self, item):
        """
        check if item in dict
        :param item:
        :return:
        """
        return item in self.data

    def __len__(self):
        """
        len of dict
        :return:
        """
        return len(self.data)


class AssetDict(Generic[T]):
    def __init__(self):
        """
        init AssetDict
        """
        self.data: Dict[TokenInfo, T] = {}

    def __getitem__(self, item) -> T:
        """
        get item magic method
        :param item:
        :return:
        """
        return self.data[item]

    def __setitem__(self, key: TokenInfo, value: T):
        """
        set item magic method
        :param key:
        :param value:
        :return:
        """
        self.data[key] = value
        setattr(self, key.name, value)

    def items(self) -> (List[TokenInfo], List[T]):
        """
        get items from dict
        :return:
        """
        return self.data.items()

    def keys(self) -> List[TokenInfo]:
        """
        get keys from dict
        :return:
        """
        return self.data.keys()

    def values(self) -> List[T]:
        """
        get values from dict
        :return:
        """
        return self.data.values()

    def __contains__(self, item):
        """
        check if item in dict
        :param item:
        :return:
        """
        return item in self.data

    def __len__(self):
        """
        length of dict
        :return:
        """
        return len(self.data)


@dataclass
class AccountStatus(AccountStatusCommon):
    """
    Account Status
    :param asset_balances: balance of asset
    :param market_status:
    """

    asset_balances: AssetDict[Decimal] = field(default_factory=AssetDict)
    market_status: MarketDict[MarketBalance] = field(default_factory=MarketDict)

    def to_array(self) -> List:
        """
        market_status value to list
        :return:
        """
        result = [self.net_value]
        for balance in self.asset_balances.values():
            result.append(balance)
        for market, status in self.market_status.items():
            for k, v in vars(status).items():
                result.append(v)
        return result

    def get_names(self) -> List:
        """
        get market_status market name
        :return:
        """
        result = ["net_value"]
        for asset in self.asset_balances.keys():
            result.append(asset.name)
        for market, status in self.market_status.items():
            base_name = market.name
            for k, v in vars(status).items():
                result.append(f"{base_name}_{k}")
        return result

    @staticmethod
    def to_dataframe(status_list: []) -> pd.DataFrame:
        """
        status list convert to dataframe
        :param status_list:
        :return:
        """
        index = [i.timestamp for i in status_list]
        if len(index) > 0:
            return pd.DataFrame(columns=status_list[0].get_names(), index=index, data=map(lambda d: d.to_array(), status_list))
        else:
            return pd.DataFrame()


class PositionManager:
    def __init__(self):
        self.positions: Dict[str, Decimal] = {}
        self.keys: List[T] = []

    def add(self, stock: T, amount: Decimal) -> Decimal:
        key = str(stock)
        if key not in self.positions:
            self.positions[key] = Decimal(0)
            self.keys.append(stock)
        self.positions[key] += amount
        return self.positions[key]

    def substract(self, stock: T, amount: Decimal) -> Decimal:
        key = str(stock)
        if key not in self.positions:
            raise DemeterError(f"{stock} not in position")
        if self.positions[key] < amount:
            raise DemeterError(f"insufficient amount for {key}")
        self.positions[key] -= amount
        return self.positions[key]

    def get(self, stock: T) -> Decimal:
        key = str(stock)
        if key not in self.positions:
            raise DemeterError(f"{key} not in position")
        return self.positions[key]

    def has(self, stock: T) -> bool:
        key = str(stock)
        return key in self.positions


@dataclass
class RowData:
    timestamp: datetime
    row_id: int
    prices: pd.Series
    market_status: MarketDict[pd.Series] = MarketDict()
