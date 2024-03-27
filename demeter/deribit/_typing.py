from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, List, Union, Tuple

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
    strike_price: int
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
    asks: List[Tuple[float, float]]  # price and amount
    bids: List[Tuple[float, float]]


class DeribitTokenConfig(NamedTuple):
    trade_fee_rate: Decimal
    delivery_fee_rate: Decimal
    min_trade_decimal: int  # exponent, eg: 5 in 1e5, -2 in 1e-2
    min_fee_decimal: int

    @property
    def min_amount(self):
        return Decimal(f"1e{self.min_trade_decimal}")


class OptionKind(Enum):
    put = "PUT"
    call = "CALL"


@dataclass
class OptionPosition:
    instrument_name: str
    expiry_time: datetime
    strike_price: int
    type: OptionKind
    amount: Decimal
    avg_buy_price: Decimal
    buy_amount: Decimal
    avg_sell_price: Decimal
    sell_amount: Decimal


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
    delta: Decimal
    gamma: Decimal


class Order(NamedTuple):
    price: Decimal
    amount: Decimal

    @staticmethod
    def get_average_price(orders: List):
        total = sum([t.amount * Decimal(t.price) for t in orders])
        total_amount = sum([t.amount for t in orders])
        if total_amount == 0:
            return 0
        else:
            return total / total_amount


@dataclass
class OptionTradeAction(BaseAction):
    instrument_name: str
    type: OptionKind
    average_price: Decimal
    amount: Decimal
    total_premium: Decimal
    mark_price: Decimal
    underlying_price: Decimal
    fee: Decimal
    orders: List[Order]


@dataclass
class BuyAction(OptionTradeAction):

    def set_type(self):
        self.action_type = ActionTypeEnum.option_buy


@dataclass
class SellAction(OptionTradeAction):

    def set_type(self):
        self.action_type = ActionTypeEnum.option_sell
