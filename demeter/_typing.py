from enum import Enum
from typing import NamedTuple
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass, field

from .utils.application import get_formatted_str

DECIMAL_ZERO = Decimal(0)


class UnitDecimal:
    default_output_format = ".8g"

    def __init__(self, number: Decimal, unit: str, output_format: str = None):
        self.number: Decimal = number
        self.unit: str = unit
        self.output_format: str = output_format if output_format is not None else UnitDecimal.default_output_format

    def __str__(self):
        return "{:{}}{}".format(self.number, self.output_format, self.unit)


class TokenInfo(NamedTuple):
    name: str
    decimal: int


class Asset(NamedTuple):
    token: TokenInfo
    amount: Decimal


class TradeEnum(Enum):
    add_liquidity = 1,
    remove_liquidity = 2,
    buy = 3,
    sell = 4,
    collect_fee = 5


class PositionInfo(NamedTuple):
    lower_tick: int
    upper_tick: int
    liquidity: Decimal

    def __str__(self):
        return f"""tick:{self.lower_tick},{self.upper_tick}, liquidity:{format(self.liquidity, '.8g')}"""


class PositionAmount(NamedTuple):
    position: PositionInfo
    base_amount: UnitDecimal
    quote_amount: UnitDecimal


BarStatusNames = [
    "base_balance",
    "quote_balance",
    "uncollect_fee_base",
    "uncollect_fee_quote",
    "base_in_position",
    "quote_in_position",
    "capital",
    "price",
    "net_value",
    "profit_pct",
]


@dataclass
class BarStatus:
    """
    每个bar之后的统计数据
    """
    base_balance: UnitDecimal
    quote_balance: UnitDecimal
    uncollect_fee_base: UnitDecimal
    uncollect_fee_quote: UnitDecimal
    base_in_position: UnitDecimal
    quote_in_position: UnitDecimal
    capital: UnitDecimal
    price: UnitDecimal
    net_value: UnitDecimal  # 账户净值
    profit_pct: UnitDecimal  # 账户总收益率

    def get_output_str(self):
        return get_formatted_str({
            "total capital": f"{self.capital}",
            "balance": f"{self.base_balance},{self.quote_balance}",
            "uncollect fee": f"{self.uncollect_fee_base},{self.uncollect_fee_quote}",
            "in position amount": f"{self.base_in_position},{self.quote_in_position}",
            "net value": f"{self.net_value}",
            "profit pct": f"{self.profit_pct}"
        })

    def to_array(self):
        return [
            self.base_balance,
            self.quote_balance,
            self.uncollect_fee_base,
            self.uncollect_fee_quote,
            self.base_in_position,
            self.quote_in_position,
            self.capital,
            self.price,
            self.net_value,
            self.profit_pct
        ]


class RowData(object):
    def __init__(self):
        self.timestamp: datetime = None
        self.row_id: int = None
        self.netAmount0: int = None
        self.netAmount1: int = None
        self.closeTick: int = None
        self.openTick: int = None
        self.lowestTick: int = None
        self.highestTick: int = None
        self.inAmount0: int = None
        self.inAmount1: int = None
        self.currentLiquidity: Decimal = None
        self.open: Decimal = None
        self.price: Decimal = None
        self.low: Decimal = None
        self.high: Decimal = None
        self.volume0: Decimal = None
        self.volume1: Decimal = None


@dataclass
class BaseAction(object):
    trade_type: TradeEnum = field(default=False, init=False)
    timestamp: datetime = field(default=False, init=False)
    base_balance_after: UnitDecimal
    quote_balance_after: UnitDecimal

    def get_output_str(self):
        return str(self)


@dataclass
class AddLiquidityAction(BaseAction):
    base_amount_max: UnitDecimal
    quote_amount_max: UnitDecimal
    lower_quote_price: UnitDecimal
    upper_quote_price: UnitDecimal
    base_amount_actual: UnitDecimal
    quote_amount_actual: UnitDecimal
    position: PositionInfo
    trade_type = TradeEnum.add_liquidity

    def get_output_str(self):
        return f"""\033[1;31m{"Add liquidity":<20}\033[0m""" + \
               get_formatted_str({
                   "max amount": f"{self.base_amount_max},{self.quote_amount_max}",
                   "price": f"{self.lower_quote_price},{self.upper_quote_price}",
                   "position": self.position,
                   "balance": f"{self.base_balance_after}(-{self.base_amount_actual}), {self.quote_balance_after}(-{self.quote_amount_actual})"
               })


@dataclass
class CollectFeeAction(BaseAction):
    position: PositionInfo
    base_amount: UnitDecimal
    quote_amount: UnitDecimal
    trade_type = TradeEnum.collect_fee

    def get_output_str(self):
        return f"""\033[1;33m{"Collect fee":<20}\033[0m""" + \
               get_formatted_str({
                   "position": self.position,
                   "balance": f"{self.base_balance_after}(+{self.base_amount}), {self.quote_balance_after}(+{self.quote_amount})"
               })


@dataclass
class RemoveLiquidityAction(BaseAction):
    position: PositionInfo
    base_amount: UnitDecimal
    quote_amount: UnitDecimal
    trade_type = TradeEnum.remove_liquidity

    def get_output_str(self):
        return f"""\033[1;32m{"Remove liquidity":<20}\033[0m""" + \
               get_formatted_str({
                   "position": self.position,
                   "balance": f"{self.base_balance_after}(+{self.base_amount}), {self.quote_balance_after}(+{self.quote_amount})"
               })


@dataclass
class BuyAction(BaseAction):
    amount: UnitDecimal
    price: UnitDecimal
    fee: UnitDecimal
    base_change: UnitDecimal
    quote_change: UnitDecimal
    trade_type = TradeEnum.buy

    def get_output_str(self):
        return f"""\033[1;36m{"Buy":<20}\033[0m""" + \
               get_formatted_str({
                   "price": self.price,
                   "fee": self.fee,
                   "balance": f"{self.base_balance_after}(-{self.base_change}), {self.quote_balance_after}(+{self.quote_change})"
               })


@dataclass
class SellAction(BaseAction):
    amount: UnitDecimal
    price: UnitDecimal
    fee: UnitDecimal
    base_change: UnitDecimal
    quote_change: UnitDecimal
    trade_type = TradeEnum.sell

    def get_output_str(self):
        return f"""\033[1;37m{"Sell":<20}\033[0m""" + \
               get_formatted_str({
                   "price": self.price,
                   "fee": self.fee,
                   "balance": f"{self.base_balance_after}(+{self.base_change}), {self.quote_balance_after}(-{self.quote_change})"
               })


@dataclass
class EvaluatingIndicator:
    annualized_returns: UnitDecimal
    benchmark_returns: UnitDecimal

    def get_output_str(self):
        return get_formatted_str({
            "annualized_returns": self.annualized_returns,
            "benchmark_returns": self.benchmark_returns,
        })


class ZelosError(RuntimeError):
    pass
