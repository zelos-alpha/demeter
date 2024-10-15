import logging

from datetime import datetime

import json

from dataclasses import dataclass

from typing import NamedTuple

from decimal import Decimal
from enum import Enum


class Formats:
    # follow the document here: https://python-reference.readthedocs.io/en/latest/docs/functions/format.html
    global_num_format: str = ".8g"


# constant value for number 1
DECIMAL_0 = Decimal(0)

# constant value for number 0
DECIMAL_1 = Decimal(1)


class TimeUnitEnum(Enum):
    """
    Time unit of moving average,

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
    :param unit: unit of the number, e.g. eth
    :type unit: str
    """

    __integral = Decimal(1)

    def __new__(cls, value, unit: str = ""):
        obj = Decimal.__new__(cls, value)
        obj._unit = unit
        return obj

    def to_str(self):
        """
        Get formatted string like "12.34 eth". Decimal format is predefined by self.output_format attribute

        :return: formatted string
        :rtype: str
        """
        dec = self.quantize(DECIMAL_1) if (self == self.to_integral() and self < 1e29) else self.normalize()
        return "{:{}} {}".format(dec, Formats.global_num_format, self._unit)

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, value):
        self._unit = value


@dataclass
class TokenInfo:
    """
    Identity for a token, will be used as key for token dict.

    :param name: token symbol, will be set as unit of a token value, e.g. usdc
    :type name: str
    :param decimal: decimal of this token, e.g. 6
    :type decimal: int
    :param address: Address of token, for aave market, this attribute has to be filled to load data.
    :type decimal: str
    """

    name: str
    decimal: int
    address: str

    def __init__(self, name: str, decimal: int, address: str = ""):
        self.name = name.upper()
        self.decimal = decimal
        self.address = address.lower()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, TokenInfo):
            return self.name == other.name
        else:
            return False

    def __hash__(self):
        return self.name.__hash__()


class DemeterError(RuntimeError):
    def __init__(self, message):
        self.message = message


class DemeterWarning(RuntimeWarning):
    def __init__(self, message):
        self.message = message


class ChainType(int, Enum):
    """
    Enum for chains
    """

    ethereum = 1
    polygon = 137
    optimism = 69
    arbitrum = 42161
    celo = 42220
    bsc = 56
    base = 8453
    avalanche = 43114
    fantom = 250
    harmony = 1666600000


@dataclass
class MarketDescription:
    type: str
    """market type string"""
    name: str
    """market name"""

@dataclass
class DemeterLog:
    time: datetime
    message: str
    level: int = logging.INFO


USD = TokenInfo("USD", 0)

STABLE_COINS = [
    "USD",
    "USDT",
    "USDC",
    "DAI",
    "FDUSD",
    "PYUSD",
    "TUSD",
    "EDLC",
    "USDE",
    "FRAX",
    "USDB",
    "USDY",
    "USDJ",
    "CRVUSD",
    "EURS",
    "USDP",
    "GUSD",
    "USDX",
    "LUSD",
    "GHO",

]
