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


Decimal_1 = Decimal(1)


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
        dec = self.quantize(Decimal_1) if (self == self.to_integral() and self < 1e+29) else self.normalize()
        return "{:{}} {}".format(dec, self.output_format, self.unit)


class EvaluatorEnum(Enum):
    ALL = 0
    ANNUALIZED_RETURNS = 1
    BENCHMARK_RETURNS = 2
    MAX_DRAEDOWN = 3

    def __str__(self):
        return self.name


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





class PositionInfo(NamedTuple):
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
class AccountStatus: # TODO 干掉, 用DepositBalance代替
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
    base_balance: UnitDecimal
    quote_balance: UnitDecimal
    base_uncollected: UnitDecimal
    quote_uncollected: UnitDecimal
    base_in_position: UnitDecimal
    quote_in_position: UnitDecimal
    net_value: UnitDecimal
    price: UnitDecimal

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
    data for each bar. Strategy.on_bar() would know which property to use

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





class DemeterError(Exception):
    def __init__(self, message):
        self.message = message


class EthError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
