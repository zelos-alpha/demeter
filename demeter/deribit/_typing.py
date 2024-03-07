from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, List


class DeribitOptionMarketDescription(NamedTuple):
    """
    Designed to generate json description for aave market

    :param type: market type
    :type type: str
    :param name: market name
    :type name: str
    :param position_count: count of positions
    :type position_count: int

    """

    type: str
    """market type"""
    name: str
    """market name"""
    position_count: int
    """count of position"""


@dataclass
class Orderbook:
    """
    all the price is in unit of underlying token!
    """

    instrument_name: str
    time: datetime
    actual_time: datetime
    state: str
    type: str
    k: float
    t: float
    exec_time: datetime
    vega: float
    theta: float
    rho: float
    gamma: float
    delta: float
    underlying_price: float
    settlement_price: float
    min_price: float
    max_price: float
    mark_price: float
    mark_iv: float
    last_price: float
    interest_rate: float
    bid_iv: float
    best_bid_price: float
    best_bid_amount: float
    ask_iv: float
    best_ask_price: float
    best_ask_amount: float
    asks: List[List[float, float]]  # price and amount
    bids: List[List[float, float]]


class DeribitTokenConfig(NamedTuple):
    fee_amount: Decimal
    min_decimal: int  # exponent, eg: 5 in 1e5, -2 in 1e-2

    @property
    def min_amount(self):
        return Decimal(f"1e{self.min_decimal}")


class OptionKind(Enum):
    Put = "P"
    Call = "C"


@dataclass
class OptionPosition:
    instrument_name: str
    amount: Decimal
