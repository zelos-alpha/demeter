from decimal import Decimal
from enum import Enum
from typing import NamedTuple

DECIMAL_0 = Decimal(0)
DECIMAL_1 = Decimal(1)


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
    :type _unit: str
    :param output_format: output format, follow the document here: https://python-reference.readthedocs.io/en/latest/docs/functions/format.html
    :type output_format: str
    """

    __integral = Decimal(1)
    default_output_format = ".8g"

    def __new__(cls, value, unit: str = "", output_format=None):
        obj = Decimal.__new__(cls, value)
        obj._unit = unit
        obj.output_format: str = (
            output_format
            if output_format is not None
            else UnitDecimal.default_output_format
        )
        return obj

    def to_str(self):
        """
        get formatted string of this decimal. format is defined in self.output_format and unit will be append.

        :return: formatted string
        :rtype: str
        """
        dec = (
            self.quantize(DECIMAL_1)
            if (self == self.to_integral() and self < 1e29)
            else self.normalize()
        )
        return "{:{}} {}".format(dec, self.output_format, self._unit)

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, value):
        self._unit = value


class EvaluatorEnum(Enum):
    ALL = 0
    ANNUALIZED_RETURNS = 1
    BENCHMARK_RETURNS = 2
    MAX_DRAW_DOWN = 3

    def __str__(self):
        return self.name


class TokenInfo(NamedTuple):
    """
    token info

    :param name: token symbol, will be set as unit of a token value, eg: usdc
    :type name: str
    :param decimal: decimal of this token, eg: 6
    :type decimal: int
    """

    name: str
    decimal: int


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


class DemeterError(Exception):
    def __init__(self, message):
        self.message = message


class TradeError(Exception):
    def __init__(self, message):
        self.message = message


class EthError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
