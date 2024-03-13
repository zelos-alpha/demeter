from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, List, Union

import pandas as pd

from demeter import MarketStatus, BaseAction
from demeter.broker import MarketBalance, ActionTypeEnum


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
class InstrumentStatus:
    """
    all the price is in unit of underlying token!
    """

    actual_time: datetime
    state: str
    type: str
    strike_price: float
    t: float
    expiry_time: datetime
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
    trade_fee_rate: float
    delivery_fee_rate: float
    min_decimal: int  # exponent, eg: 5 in 1e5, -2 in 1e-2

    @property
    def min_amount(self):
        return float(Decimal(f"1e{self.min_decimal}"))


class OptionKind(Enum):
    put = "PUT"
    call = "CALL"


@dataclass
class OptionPosition:
    instrument_name: str
    expiry_time: datetime
    strike_price: float
    type: OptionKind
    amount: float
    avg_buy_price: float
    buy_amount: float
    avg_sell_price: float
    sell_amount: float


@dataclass
class DeribitMarketStatus(MarketStatus):
    """
    MarketStatus properties

    :param data: current pool status
    :type data: Union[pd.Series, UniV3PoolStatus]
    """

    data: Union[pd.DataFrame, List[InstrumentStatus]] = None


@dataclass
class OptionMarketBalance(MarketBalance):
    put_count: int
    call_count: int
    delta: float
    gamma: float


class Order(NamedTuple):
    price: float
    amount: float

    @staticmethod
    def get_average_price(orders: List):
        total = sum([t.amount * t.price for t in orders])
        total_amount = sum([t.amount for t in orders])
        if total_amount == 0:
            return 0
        else:
            return total / total_amount


@dataclass
class OptionTradeAction(BaseAction):
    instrument_name: str
    type: OptionKind
    average_price: float
    amount: float
    total_premium: float
    mark_price: float
    underlying_price: float
    fee: float
    orders: List[Order]


@dataclass
class BuyAction(OptionTradeAction):

    def set_type(self):
        self.action_type = ActionTypeEnum.option_buy


@dataclass
class SellAction(OptionTradeAction):

    def set_type(self):
        self.action_type = ActionTypeEnum.option_sell
