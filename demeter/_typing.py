from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import NamedTuple

from .utils.application import get_formatted_str

DECIMAL_ZERO = Decimal(0)


class TimeUnitEnum(Enum):
    """
    time unit for moving average,

    * minute
    * hour
    * day
    """
    minute = 1
    hour = 60
    day = 60 * 24


class UnitDecimal(Decimal):
    """
    Decimal with unit, such a 1 eth.

    It's inherit from Decimal, but considering performance issues, calculate function is not override,
    so if you do calculate on this object, return type will be Decimal

    :param number: number to keep
    :type number: Decimal
    :param unit: unit of the number, eg: eth
    :type unit: str
    :param output_format: output format, follow the document here: https://python-reference.readthedocs.io/en/latest/docs/functions/format.html
    :type output_format: str
    """
    __integral = Decimal(1)
    default_output_format = ".8g"

    def __new__(cls, value, unit: str, output_format=None):
        obj = Decimal.__new__(cls, value)
        obj.unit = unit
        obj.output_format: str = output_format if output_format is not None else UnitDecimal.default_output_format
        return obj

    def to_str(self):
        """
        get formatted string of this decimal. format is defined in self.output_format and unit will be append.

        :return: formatted string
        :rtype: str
        """
        dec = self.quantize(self.__integral) if self == self.to_integral() else self.normalize()
        return "{:{}} {}".format(dec, self.output_format, self.unit)


class TokenInfo(NamedTuple):
    """
    token info

    :param name: token symbol, will be set as unit of a token value
    :type name: str
    :param decimal: decimal of this token
    :type decimal: int
    """
    name: str
    decimal: int


class PoolBaseInfo(object):
    """
    pool information, corresponding with definition in pool contract.

    :param token0: First token in  pool contract.
    :type token0:  TokenInfo
    :param token1: Second token in  pool contract.
    :type token1: TokenInfo
    :param fee: fee rate of this pool, should be among [0.05, 0.3, 1]
    :type fee: float
    :param base_token: which token will be considered as base token. eg: to a token pair of USDT/BTC, if you want price unit to be like 10000 usdt/btc, you should set usdt as base token, otherwise if price unit is 0.00001 btc/usdt, you should set btc as base token
    :type base_token: TokenInfo
    """

    def __init__(self, token0: TokenInfo, token1: TokenInfo, fee: float, base_token):
        self.token0 = token0
        self.token1 = token1
        self.is_token0_base = (base_token == token0)
        self.base_token = base_token
        base, quote = token0, token1 if self.is_token0_base else token1, token0
        self.price_unit = f"{base.name}/{quote.name}"
        fee = str(fee)  # keep precision
        match fee:
            case "0.05":
                self.tickSpacing = 10
            case "0.3":
                self.tickSpacing = 60
            case "1":
                self.tickSpacing = 200
            case _:
                raise DemeterError("fee should be 0.05 or 0.3 or 1")
        self.fee = Decimal(fee) * Decimal(10000)
        self.fee_rate = Decimal(fee) / Decimal(100)

    def __str__(self):
        """
        get string
        :return:
        :rtype:
        """
        return "PoolBaseInfo(Token0: {},".format(self.token0) + \
               "Token1: {},".format(self.token1) + \
               "fee: {},".format(self.fee_rate * Decimal(100)) + \
               "base token: {})".format(self.token0.name if self.is_token0_base else self.token1.name)


class Asset(NamedTuple):
    """
    asset info of a token

    :param token: token info
    :type token: TokenInfo
    :param amount: amount of this token, eg: 1.123456
    :type amount: Decimal
    """
    token: TokenInfo
    amount: Decimal


class ActionTypeEnum(Enum):
    """
    Trade types

    * add_liquidity = 1,
    * remove_liquidity = 2,
    * buy = 3,
    * sell = 4,
    * collect_fee = 5
    """
    add_liquidity = 1,
    remove_liquidity = 2,
    buy = 3,
    sell = 4,
    collect_fee = 5


class Position(NamedTuple):
    """
    position information, including tick range and liquidity. It's the immute properties of a position

    :param lower_tick: lower tick
    :type lower_tick: int
    :param upper_tick: upper tick
    :type upper_tick: int

    """
    lower_tick: int
    upper_tick: int

    def __str__(self):
        return f"""tick:{self.lower_tick},{self.upper_tick}"""


BarStatusNames = [
    "base_balance",
    "quote_balance",
    "base_uncollected",
    "quote_uncollected",
    "base_in_position",
    "quote_in_position",
    "net_value",
    "price"
]


@dataclass
class AccountStatus:
    """
    current status of broker

    :param timestamp: timestamp
    :type timestamp: datetime
    :param base_balance: balance of base token
    :type base_balance: UnitDecimal
    :param quote_balance: balance of quote token
    :type quote_balance: UnitDecimal
    :param base_uncollected: base token uncollect fee in all the positions.
    :type base_uncollected: UnitDecimal
    :param quote_uncollected: quote token uncollect fee in all the positions.
    :type quote_uncollected: UnitDecimal
    :param base_in_position: base token amount deposited in positions, calculated according to current price
    :type base_in_position: UnitDecimal
    :param quote_in_position: quote token amount deposited in positions, calculated according to current price
    :type quote_in_position: UnitDecimal
    :param net_value: all the capitals for broker, including balance,uncollected fee, deposited
    :type net_value: UnitDecimal
    :param price: current price
    :type price: UnitDecimal

    """
    timestamp: datetime
    net_value: UnitDecimal
    balance: dict[TokenInfo, UnitDecimal]
    price: dict[TokenInfo, UnitDecimal]
    uncollected: dict[PoolBaseInfo, dict[Position, dict[TokenInfo, UnitDecimal]]]
    in_position: dict[PoolBaseInfo, dict[Position, dict[TokenInfo, UnitDecimal]]]

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console
        :return: formatted string
        :rtype: str
        """
        return get_formatted_str({
            "total capital": f"{self.net_value.to_str()}",
            "balance": f"{self.base_balance.to_str()},{self.quote_balance.to_str()}",
            "uncollect fee": f"{self.base_uncollected.to_str()},{self.quote_uncollected.to_str()}",
            "in position amount": f"{self.base_in_position.to_str()},{self.quote_in_position.to_str()}"
        })

    def to_array(self):
        return [
            self.base_balance,
            self.quote_balance,
            self.base_uncollected,
            self.quote_uncollected,
            self.base_in_position,
            self.quote_in_position,
            self.net_value,
            self.price
        ]


class RowData(object):
    """
    data for each bar. Strategy.next() would know which property to use

    :param timestamp: current time of test data
    :param row_id: data index of this line, start with 0, can be used in dataframe.iloc()
    :param netAmount0: net amount of token 0
    :param netAmount1: net amount of token 1
    :param closeTick: last tick of this bar
    :param openTick: first tick of this bar
    :param lowestTick: lowest tick
    :param highestTick: highest tick
    :param inAmount0: swap in amount of token 0
    :param inAmount1: swap in amount of token 1
    :param currentLiquidity: current liquidity
    :param open: first price of this bar
    :param price: latest price of this bar
    :param low: lowest price
    :param high: highest price
    :param volume0: volume of token 0
    :param volume1: volume of token 1
    """

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
    """
    Parent class of broker actions,

    :param trade_type: action type
    :type action_type: ActionTypeEnum
    :param timestamp: action time
    :type timestamp: datetime
    :param base_balance_after: after action balance of base token
    :type base_balance_after: UnitDecimal
    :param quote_balance_after: after action balance of quote token
    :type quote_balance_after: UnitDecimal
    """
    action_type: ActionTypeEnum = field(default=False, init=False)
    timestamp: datetime = field(default=False, init=False)
    base_balance_after: UnitDecimal
    quote_balance_after: UnitDecimal

    def get_output_str(self):
        return str(self)


@dataclass
class AddLiquidityAction(BaseAction):
    """
    Add Liquidity

    :param base_amount_max: inputted base token amount, also the max amount to deposit
    :type base_amount_max: ActionTypeEnum
    :param quote_amount_max: inputted base token amount, also the max amount to deposit
    :type quote_amount_max: datetime
    :param lower_quote_price: lower price base on quote token.
    :type lower_quote_price: UnitDecimal
    :param upper_quote_price: upper price base on quote token.
    :type upper_quote_price: UnitDecimal
    :param base_amount_actual: actual used base token
    :type base_amount_actual: UnitDecimal
    :param quote_amount_actual: actual used quote token
    :type quote_amount_actual: UnitDecimal
    :param position: generated position
    :type position: Position
    :param liquidity: liquidity added
    :type liquidity: int
    """
    pool: PoolBaseInfo
    base_amount_max: UnitDecimal
    quote_amount_max: UnitDecimal
    lower_quote_price: UnitDecimal
    upper_quote_price: UnitDecimal
    base_amount_actual: UnitDecimal
    quote_amount_actual: UnitDecimal
    position: Position
    liquidity: int
    action_type = ActionTypeEnum.add_liquidity

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console
        :return: formatted string
        :rtype: str
        """
        return f"""\033[1;31m{"Add liquidity":<20}\033[0m""" + \
               get_formatted_str({
                   "pool": f"{self.pool}",
                   "max amount": f"{self.base_amount_max.to_str()},{self.quote_amount_max.to_str()}",
                   "price": f"{self.lower_quote_price.to_str()},{self.upper_quote_price.to_str()}",
                   "position": self.position,
                   "liquidity": self.liquidity,
                   "balance": f"{self.base_balance_after.to_str()}(-{self.base_amount_actual.to_str()}), "
                              f"{self.quote_balance_after.to_str()}(-{self.quote_amount_actual.to_str()})"
               })


@dataclass
class CollectFeeAction(BaseAction):
    """
    collect fee

    :param position: position to operate
    :type position: Position
    :param base_amount: fee collected in base token
    :type base_amount: UnitDecimal
    :param quote_amount: fee collected in quote token
    :type quote_amount: UnitDecimal

    """
    pool: PoolBaseInfo
    position: Position
    base_amount: UnitDecimal
    quote_amount: UnitDecimal
    action_type = ActionTypeEnum.collect_fee

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console
        :return: formatted string
        :rtype: str
        """
        return f"""\033[1;33m{"Collect fee":<20}\033[0m""" + \
               get_formatted_str({
                   "pool": f"{self.pool}",
                   "position": self.position,
                   "balance": f"{self.base_balance_after.to_str()}(+{self.base_amount.to_str()}), {self.quote_balance_after.to_str()}(+{self.quote_amount.to_str()})"
               })


@dataclass
class RemoveLiquidityAction(BaseAction):
    """
    remove position

    :param pool: pool
    :type pool: PoolBaseInfo
    :param position: position to operate
    :type position: Position
    :param base_amount: base token amount collected
    :type base_amount: UnitDecimal
    :param quote_amount: quote token amount collected
    :type quote_amount: UnitDecimal
    :param removed_liquidity: liquidity number has removed
    :type removed_liquidity: int
    :param remain_liquidity: liquidity number left in position
    :type remain_liquidity: int

    """
    pool: PoolBaseInfo
    position: Position
    base_amount: UnitDecimal
    quote_amount: UnitDecimal
    removed_liquidity: int
    remain_liquidity: int
    action_type = ActionTypeEnum.remove_liquidity

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console
        :return: formatted string
        :rtype: str
        """
        return f"""\033[1;32m{"Remove liquidity":<20}\033[0m""" + \
               get_formatted_str({
                   "pool": f"{self.pool}",
                   "position": self.position,
                   "balance": f"{self.base_balance_after.to_str()}(+0), {self.quote_balance_after.to_str()}(+0)",
                   "token_got": f"{self.base_amount.to_str()},{self.quote_amount.to_str()}",
                   "removed liquidity": self.removed_liquidity,
                   "remain liquidity": self.remain_liquidity
               })


@dataclass
class BuyAction(BaseAction):
    """
    buy token, swap from base token to quote token.

    :param amount: amount to buy(in quote token)
    :type amount: UnitDecimal
    :param price: price,
    :type price: UnitDecimal
    :param fee: fee paid (in base token)
    :type fee: UnitDecimal
    :param base_change: base token amount changed
    :type base_change: Position
    :param quote_change: quote token amount changed
    :type quote_change: UnitDecimal

    """
    pool: PoolBaseInfo
    amount: UnitDecimal
    price: UnitDecimal
    fee: UnitDecimal
    base_change: UnitDecimal
    quote_change: UnitDecimal
    action_type = ActionTypeEnum.buy

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console
        :return: formatted string
        :rtype: str
        """
        return f"""\033[1;36m{"Buy":<20}\033[0m""" + \
               get_formatted_str({
                   "pool": f"{self.pool}",
                   "price": self.price.to_str(),
                   "fee": self.fee.to_str(),
                   "balance": f"{self.base_balance_after.to_str()}(-{self.base_change.to_str()}), {self.quote_balance_after.to_str()}(+{self.quote_change.to_str()})"
               })


@dataclass
class SellAction(BaseAction):
    """
    sell token, swap from quote token to base token.

    :param amount: amount to sell(in quote token)
    :type amount: UnitDecimal
    :param price: price,
    :type price: UnitDecimal
    :param fee: fee paid (in quote token)
    :type fee: UnitDecimal
    :param base_change: base token amount changed
    :type base_change: Position
    :param quote_change: quote token amount changed
    :type quote_change: UnitDecimal

    """
    pool: PoolBaseInfo
    amount: UnitDecimal
    price: UnitDecimal
    fee: UnitDecimal
    base_change: UnitDecimal
    quote_change: UnitDecimal
    action_type = ActionTypeEnum.sell

    def get_output_str(self):
        return f"""\033[1;37m{"Sell":<20}\033[0m""" + \
               get_formatted_str({
                   "pool": f"{self.pool}",
                   "price": self.price.to_str(),
                   "fee": self.fee.to_str(),
                   "balance": f"{self.base_balance_after.to_str()}(+{self.base_change.to_str()}), {self.quote_balance_after.to_str()}(-{self.quote_change.to_str()})"
               })


@dataclass
class EvaluatingIndicator:
    """
    Indicator to evaluate a strategy

    :param annualized_returns: annualized returns
    :type annualized_returns: UnitDecimal
    :param benchmark_returns: benchmark returns
    :type benchmark_returns: UnitDecimal


    """
    annualized_returns: UnitDecimal
    benchmark_returns: UnitDecimal

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console
        :return: formatted string
        :rtype: str
        """
        return get_formatted_str({
            "annualized_returns": self.annualized_returns.to_str(),
            "benchmark_returns": self.benchmark_returns.to_str(),
        })


class DemeterError(RuntimeError):
    pass
