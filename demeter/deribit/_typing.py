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

    state: str | None = None
    type: str | None = None
    strike_price: int | None = None
    t: float | None = None
    expiry_time: datetime | None = None
    vega: float | None = None
    theta: float | None = None
    rho: float | None = None
    gamma: float | None = None
    delta: float | None = None
    underlying_price: float | None = None
    settlement_price: float | None = None
    mark_price: float | None = None
    mark_iv: float | None = None
    last_price: float | None = None
    interest_rate: float | None = None
    bid_iv: float | None = None
    best_bid_price: float | None = None
    best_bid_amount: float | None = None
    ask_iv: float | None = None
    best_ask_price: float | None = None
    best_ask_amount: float | None = None
    asks: List[Tuple[float, float]] | None = None  # price and amount
    bids: List[Tuple[float, float]] | None = None


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


@dataclass
class DeliverAction(BaseAction):
    instrument_name: str
    type: OptionKind
    mark_price: Decimal
    amount: Decimal
    total_premium: Decimal
    strike_price: int
    underlying_price: Decimal
    deriver_amount: Decimal
    fee: Decimal
    income_amount: Decimal


@dataclass
class ExpiredAction(BaseAction):
    instrument_name: str
    type: OptionKind
    mark_price: Decimal
    amount: Decimal
    total_premium: Decimal
    strike_price: int
    underlying_price: Decimal


DERIBIT_OPTION_FREQ = "1h"
