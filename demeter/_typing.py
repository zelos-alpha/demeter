from decimal import Decimal
from enum import Enum
from typing import NamedTuple

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


class DemeterError(Exception):
    def __init__(self, message):
        self.message = message


class EthError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
