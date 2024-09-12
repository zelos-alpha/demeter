import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, List, Union, Tuple

from demeter import MarketStatus, BaseAction
from demeter._typing import MarketDescription, DemeterError
from demeter.broker import MarketBalance, ActionTypeEnum
from demeter.utils.console_text import get_action_str, ForColorEnum


@dataclass
class DeribitOptionDescription(MarketDescription):
    """
    Designed to generate json description for aave market

    :param type: market type
    :type type: str
    :param name: market name
    :type name: str
    :param position_count: count of positions
    :type position_count: int

    """

    token: str
    positions: List[str]
    """count of position"""


@dataclass
class InstrumentStatus:
    """
    Property of an instrument(order)

    :param: state: status of an instrument(open, closed)
    :type state: str | None
    :param: type: order type, CALL/PUT
    :type type: str | None
    :param: strike_price: strike price
    :type strike_price: int | None
    :param: t: Time remaining until expiration
    :type t: float | None
    :param: expiry_time: expiration time
    :type expiry_time: datetime | None
    :param: vega: greeks, vega
    :type vega: float | None
    :param: theta: greeks, theta
    :type theta: float | None
    :param: rho: greeks, rho
    :type rho: float | None
    :param: gamma: greeks, gamma
    :type gamma: float | None
    :param: delta: greeks, delta
    :type delta: float | None
    :param: underlying_price: underlying price for implied volatility calculations, if token is eth, the unit is eth
    :type underlying_price: float | None
    :param: settlement_price: The settlement price for the instrument, if token is eth, the unit is eth
    :type settlement_price: float | None
    :param: mark_price: The mark price for the instrument, if token is eth, the unit is eth
    :type mark_price: float | None
    :param: mark_iv: implied volatility for mark price
    :type mark_iv: float | None
    :param: last_price: The price for the last trade, if token is eth, the unit is eth
    :type last_price: float | None
    :param: interest_rate: Interest rate used in implied volatility calculations
    :type interest_rate:  float | None
    :param: bid_iv:  implied volatility for best bid
    :type bid_iv: float | None
    :param: best_bid_price: The current best bid price, null if there aren't any bids, if token is eth, the unit is eth
    :type best_bid_price: float | None
    :param: best_bid_amount: It represents the requested order size of all best bids
    :type best_bid_amount: float | None
    :param: ask_iv: implied volatility for best ask
    :type ask_iv: float | None
    :param: best_ask_price: The current best ask price, null if there aren't any asks, if token is eth, the unit is eth
    :type best_ask_price: float | None
    :param: best_ask_amount: It represents the requested order size of all best asks
    :type best_ask_amount: float | None
    :param: asks: List of asks, in price and amount
    :type asks: List[Tuple[float, float]] | None
    :param: bids: List of bids, in price and amount
    :type bids: List[Tuple[float, float]] | None
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
    """
    Config for token in deribit

    :param trade_fee_rate: fee rate for take or make order
    :type trade_fee_rate: Decimal
    :param delivery_fee_rate: fee rate for delivery when exercising
    :type delivery_fee_rate: Decimal
    :param min_trade_decimal: minimal decimal for trade
    :type min_trade_decimal: int
    :param min_fee_decimal: minimal decimal for fee
    :type min_fee_decimal: int
    """

    trade_fee_rate: Decimal
    delivery_fee_rate: Decimal
    min_trade_decimal: int  # exponent, eg: 5 in 1e5, -2 in 1e-2
    min_fee_decimal: int

    @property
    def min_amount(self):
        return Decimal(f"1e{self.min_trade_decimal}")


class OptionKind(Enum):
    """
    Option kind, call/put
    """

    put = "PUT"
    call = "CALL"


@dataclass
class OptionPosition:
    """
    Information for an option position

    :param instrument_name: instrument name
    :type instrument_name: str
    :param expiry_time: expiry time
    :type expiry_time: datetime
    :param strike_price: strike price, if token is eth, the unit is eth
    :type strike_price: int
    :param type: option type
    :type type: OptionKind
    :param amount: amount of a instrument
    :type amount: Decimal
    :param avg_buy_price: average buy price, if token is eth, the unit is eth
    :type avg_buy_price: Decimal
    :param buy_amount: total amount brought
    :type buy_amount: Decimal
    :param avg_sell_price: average sell price, if token is eth, the unit is eth
    :type avg_sell_price: Decimal
    :param sell_amount:  total amount sold
    :type sell_amount: Decimal

    """

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
    """
    Balance of an option market

    :param puts: List of put option position
    :type puts: List[str]
    :param calls: List of call option position
    :type calls: List[str]
    :param delta: delta of current exposure
    :type delta: Decimal
    :param gamma: gamma of current exposure
    :type gamma: Decimal
    """

    balance: Decimal
    premium: Decimal
    delta: Decimal
    gamma: Decimal


class Order(NamedTuple):
    """
    Order instance when buy/sell option

    :param price: price, if token is eth, the unit is eth
    :type price: Decimal
    :param amount: amount to buy
    :type amount: Decimal
    """

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
    """
    Recording information about options trades

    :param instrument_name: instrument name
    :type instrument_name: str
    :param type: option type, call/put
    :type type: OptionKind
    :param average_price: average price, if token is eth, the unit is eth
    :type average_price: Decimal
    :param amount: amount to trade
    :type amount: Decimal
    :param total_premium: total premium of this trade
    :type total_premium: Decimal
    :param mark_price: mark price
    :type mark_price: Decimal
    :param underlying_price: underlying price
    :type underlying_price: Decimal
    :param fee: fee of this trade
    :type fee: Decimal
    :param orders: orders in price-amount,
    :type orders: List[Order]
    """

    instrument_name: str
    type: OptionKind
    average_price: Decimal
    amount: Decimal
    total_premium: Decimal
    mark_price: Decimal
    underlying_price: Decimal
    fee: Decimal
    orders: List[Order]

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.green,
            {
                "instrument_name": self.instrument_name,
                "average_price": str(self.average_price),
                "amount": str(self.amount),
                "total_premium": str(self.total_premium),
                "underlying_price": str(self.underlying_price),
            },
        )


@dataclass
class BuyAction(OptionTradeAction):
    """
    buy action
    """

    def set_type(self):
        self.action_type = ActionTypeEnum.option_buy


@dataclass
class SellAction(OptionTradeAction):
    """
    sell action
    """

    def set_type(self):
        self.action_type = ActionTypeEnum.option_sell


@dataclass
class DepositAction(BaseAction):
    token: str
    amount: Decimal

    def set_type(self):
        self.action_type = ActionTypeEnum.deribit_deposit

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.green,
            {
                "token": self.token,
                "amount": str(self.amount),
            },
        )


@dataclass
class WithdrawAction(BaseAction):
    token: str
    amount: Decimal

    def set_type(self):
        self.action_type = ActionTypeEnum.deribit_withdraw

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.green,
            {
                "token": self.token,
                "amount": str(self.amount),
            },
        )


@dataclass
class DeliverAction(BaseAction):
    """
    :param instrument_name: instrument name
    :type instrument_name: str
    :param type: option type, call/put
    :type type: OptionKind
    :param mark_price: mark price, if token is eth, the unit is eth
    :type mark_price: Decimal
    :param amount: total amount
    :type amount: Decimal
    :param total_premium: Decimal
    :type total_premium: Decimal
    :param strike_price: strike price
    :type strike_price: int
    :param underlying_price: underlying price
    :type underlying_price: Decimal
    :param deriver_amount: deriver amount
    :type deriver_amount: Decimal
    :param fee: fee
    :type fee: Decimal
    :param income_amount: income amount
    :type income_amount: Decimal
    """

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

    def set_type(self):
        self.action_type = ActionTypeEnum.option_deliver

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.green,
            {
                "instrument_name": str(self.instrument_name),
                "deriver_amount": str(self.deriver_amount),
                "total_premium": str(self.total_premium),
                "underlying_price": str(self.underlying_price),
            },
        )


@dataclass
class ExpiredAction(BaseAction):
    """
    :param instrument_name: instrument name
    :type instrument_name: str
    :param type: option type, call/put
    :type type: OptionKind
    :param mark_price: mark price
    :type mark_price: Decimal
    :param amount: total amount
    :type amount: Decimal
    :param total_premium: Decimal
    :type total_premium: Decimal
    :param strike_price: strike price
    :type strike_price: int
    :param underlying_price: underlying price
    :type underlying_price: Decimal
    """

    instrument_name: str
    type: OptionKind
    mark_price: Decimal
    amount: Decimal
    total_premium: Decimal
    strike_price: int
    underlying_price: Decimal

    def set_type(self):
        self.action_type = ActionTypeEnum.option_expire

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.green,
            {
                "instrument_name": str(self.instrument_name),
                "underlying_price": str(self.underlying_price),
                "amount": str(self.amount),
                "total_premium": str(self.total_premium),
            },
        )


class InsufficientBalanceError(DemeterError):
    def __init__(self, message):
        self.message = message


DERIBIT_OPTION_FREQ = "1h"
