import json
import os
from _decimal import Decimal
from datetime import date, timedelta
from typing import List, Dict

import pandas as pd

from ._typing import (
    DeribitOptionMarketDescription,
    DeribitTokenConfig,
    DeribitMarketStatus,
    OptionMarketBalance,
    OptionPosition,
    OptionKind,
    BuyAction,
    InstrumentStatus,
    Order,
    SellAction,
)
from .helper import round_decimal
from .. import TokenInfo
from .._typing import ChainType, DemeterError
from ..broker import Market, MarketInfo, write_func, ActionTypeEnum
from ..utils.application import float_param_formatter

DEFAULT_DATA_PATH = "./data"

ETH = TokenInfo("eth", 18)
BTC = TokenInfo("btc", 8)


class DeribitOptionMarket(Market):
    """
    You can backtest as a taker only.
    """

    def __init__(
        self,
        market_info: MarketInfo,
        token: TokenInfo,
        data: pd.DataFrame = None,
        data_path: str = DEFAULT_DATA_PATH,
    ):
        super().__init__(market_info=market_info, data_path=data_path, data=data)
        self.token: TokenInfo = token
        self.token_config: DeribitTokenConfig = DeribitOptionMarket.TOKEN_CONFIGS[token]
        self.positions: Dict[str, OptionPosition] = {}

    TOKEN_CONFIGS = {ETH: DeribitTokenConfig(0.0003, 0.00015, 0), BTC: DeribitTokenConfig(0.0003, 0.00015, -1)}
    MAX_FEE_RATE = 0.125

    def __str__(self):
        return json.dumps(self.description()._asdict())

    def description(self):
        """
        Get a brief description of this market
        """
        return DeribitOptionMarketDescription(type(self).__name__, self._market_info.name, len(self.positions))

    def load_data(self, start_date: date, end_date: date):
        """
        Load data from folder set in data_path. Those data file should be downloaded by demeter, and meet name rule.
        Deribit-option-book-{token}-{day.strftime('%Y%m%d')}.csv

        :param chain: chain type
        :type chain: ChainType
        :param token_info_list: tokens to load
        :type token_info_list: List[TokenInfo]
        :param start_date: start day
        :type start_date: date
        :param end_date: end day, the end day will be included
        :type end_date: date
        """
        self.logger.info(f"start load files from {start_date} to {end_date}...")
        day = start_date
        df = pd.DataFrame()

        while day <= end_date:
            path = os.path.join(
                self.data_path,
                f"Deribit-option-book-{self.token.name}-{day.strftime('%Y-%m-%d')}.csv",
            )
            if not os.path.exists(path):
                raise IOError(f"resource file {path} not found")

            day_df = pd.read_csv(path, parse_dates=["time", "exec_time"], index_col=["time", "instrument_name"])
            day_df.drop(columns=["actual_time", "min_price", "max_price"], inplace=True)
            df = pd.concat([df, day_df])
            day += timedelta(days=1)

        self._data = df
        self._data = self._data.resample("1min").ffill()
        self.logger.info("data has been prepared")

    def set_market_status(
        self,
        data: DeribitMarketStatus,
        price: pd.Series,
    ):
        """
        Set up market status, such as liquidity, price

        :param data: market status
        :type data: Series | MarketStatus
        :param price: current price
        :type price: Series

        """
        super().set_market_status(data, price)
        if data.data is None:
            data.data = self._data.loc[data.timestamp]
        self._market_status = data

    # region for option market only

    def get_trade_fee(self, amount: float, total_premium: float) -> float:
        """
        https://www.deribit.com/kb/fees
        """
        return min(self.token_config.trade_fee_rate * amount, DeribitOptionMarket.MAX_FEE_RATE * total_premium)

    def get_deliver_fee(self, amount: float, total_premium: float) -> float:
        """
        https://www.deribit.com/kb/fees
        """
        return min(self.token_config.delivery_fee_rate * amount, DeribitOptionMarket.MAX_FEE_RATE * total_premium)

    def __get_extern_underlying_price(self, token_prices: pd.Series | None = None) -> float:
        """
        a shortcut to get underlying token price of this market
        """
        if token_prices is None:
            token_prices = self._price_status
        return float(token_prices[self.token.name])

    def __get_trade_amount(self, amount: float):
        if amount < self.token_config.min_amount:
            return self.token_config.min_amount
        return round_decimal(amount, self.token_config.min_decimal)

    @write_func
    def buy(
        self,
        instrument_name: str,
        amount: float,
        price_in_token: float | None = None,
        price_in_usd: float | None = None,
    ) -> List[Order]:
        """
        if price is not none, will set at that price
        or else will buy according to bids

        """
        amount, instrument, price_in_token = self._check_transaction(
            amount, instrument_name, price_in_token, price_in_usd, True
        )

        # deduct bids amount
        bids = instrument.bids
        bid_list = self._deduct_order_amount(amount, bids, price_in_token)

        # write positions back
        self.data.loc[(self._market_status.timestamp, instrument_name), "bids"] = bids

        total_premium = sum([t.amount * t.price for t in bid_list])
        fee_amount = self.get_trade_fee(amount, total_premium)
        self.broker.subtract_from_balance(self.token, total_premium + fee_amount)

        # add position
        average_price = Order.get_average_price(bid_list)
        if instrument_name not in self.positions.keys():
            self.positions[instrument_name] = OptionPosition(
                instrument_name,
                instrument.expiry_time,
                instrument.strike_price,
                OptionKind(instrument.type),
                amount,
                average_price,
                amount,
                0,
                0,
            )
        else:
            position = self.positions[instrument_name]
            position.avg_buy_price = Order.get_average_price(
                [Order(average_price, amount), Order(position.avg_buy_price, position.buy_amount)]
            )
            position.buy_amount += amount
            position.amount += amount

        self._record_action(
            BuyAction(
                market=self._market_info,
                instrument_name=instrument_name,
                type=OptionKind(instrument.type),
                average_price=average_price,
                amount=amount,
                total_premium=total_premium,
                mark_price=instrument.mark_price,
                underlying_price=instrument.underlying_price,
                fee=fee_amount,
                orders=bid_list,
            )
        )
        return bid_list

    @staticmethod
    def _find_available_orders(price, order_list) -> List:
        error = 0.005
        return list(filter(lambda x: (1 - error) * price < x[0] < (1 + error) * price, order_list))

    @write_func
    def sell(
        self,
        instrument_name: str,
        amount: Decimal,
        price_in_token: float | None = None,
        price_in_usd: float | None = None,
    ) -> List[Order]:
        amount, instrument, price_in_token = self._check_transaction(
            amount, instrument_name, price_in_token, price_in_usd, False
        )

        # deduct asks amount
        asks = instrument.asks
        ask_list = self._deduct_order_amount(amount, asks, price_in_token)

        # write positions back
        self.data.loc[(self._market_status.timestamp, instrument_name), "asks"] = asks

        total_premium = sum([t.amount * t.price for t in ask_list])
        fee = self.get_trade_fee(amount, total_premium)
        self.broker.add_to_balance(self.token, total_premium - fee)

        # subtract position
        average_price = Order.get_average_price(ask_list)
        if instrument_name not in self.positions.keys():
            raise DemeterError("No such instrument position")

        position = self.positions[instrument_name]
        position.avg_sell_price = Order.get_average_price(
            [Order(average_price, amount), Order(position.avg_sell_price, position.sell_amount)]
        )
        position.sell_amount += amount
        position.amount -= amount

        if position.amount < 0:
            del self.positions[instrument_name]

        self._record_action(
            SellAction(
                market=self._market_info,
                instrument_name=instrument_name,
                type=OptionKind(instrument.type),
                average_price=average_price,
                amount=amount,
                total_premium=total_premium,
                mark_price=instrument.mark_price,
                underlying_price=instrument.underlying_price,
                fee=fee,
                orders=ask_list,
            )
        )
        return ask_list

    def _deduct_order_amount(self, amount, orders, price_in_token):
        order_list = []
        if price_in_token is not None:
            for order in orders:
                if price_in_token == order[0]:
                    order[1] -= amount
                    order_list.append(Order(order[0], amount))
        else:
            amount_to_deduct = amount
            for order in orders:
                should_deduct = min(order[1], amount_to_deduct)
                amount_to_deduct -= should_deduct
                order[1] -= should_deduct
                order_list.append(Order(order[0], should_deduct))
                if order[1] > 0:
                    break
        return order_list

    def _check_transaction(self, amount, instrument_name, price_in_token, price_in_usd, is_buy):
        if instrument_name not in self._market_status.data.index:
            raise DemeterError(f"{instrument_name} is not in current orderbook")
        instrument: InstrumentStatus = self._market_status.data[instrument_name]
        if amount < self.token_config.min_amount:
            raise DemeterError(
                f"amount should greater than min amount {self.token_config.min_amount} {self.token.name}"
            )
        amount = self.__get_trade_amount(amount)
        if price_in_usd is not None and price_in_token is None:
            price_in_token = self.__get_extern_underlying_price(self._price_status)

        if is_buy:
            orders = instrument.bids
        else:
            orders = instrument.asks

        if price_in_token is not None:
            # to prevent error in decimal
            orders = DeribitOptionMarket._find_available_orders(price_in_token, orders)
            if len(orders) < 1:
                raise DemeterError(
                    f"{instrument_name} doesn't have a order in price {price_in_token} {self.token.name}"
                )
            price_in_token = orders[0][0]
            available_amount = orders[0][1]
        else:
            available_amount = sum([x[1] for x in orders])
        if amount < available_amount:
            raise DemeterError(
                f"insufficient order to buy, required amount is {amount}, available amount is {available_amount}"
            )

        return amount, instrument, price_in_token

    def check_option_exercise(self):
        """
        loop all the option position,
        if expired, if option position is in the money, then exercise.
        if out of the money, then abandon
        """
        for position in self.positions.values():
            if self._market_status.timestamp > position.expiry_time:
                # should
                if position.type == OptionKind.put and position.strike_price < self.__get_extern_underlying_price():
                    self._delivery_put_option(position)
                elif position.type == OptionKind.call and position.strike_price > self.__get_extern_underlying_price():
                    self._delivery_call_option(position)

        pass

    def update(self):
        self.check_option_exercise()

    @write_func
    def _delivery_put_option(self, option_pos):
        """ """
        pass

    @write_func
    def _delivery_call_option(self, option_pos):
        """ """
        pass

    def get_market_balance(self, prices: pd.Series | Dict[str, Decimal]) -> OptionMarketBalance:
        """
        Get market asset balance, such as current positions, net values

        :param prices: current price of each token
        :type prices: pd.Series | Dict[str, Decimal]
        :return: Balance in this market includes net value, position value
        :rtype: MarketBalance
        """
        put_count = len(filter(lambda x: x.type == OptionKind.put, self.positions.values()))
        call_count = len(filter(lambda x: x.type == OptionKind.call, self.positions.values()))

        net_value = Decimal(0)
        delta = gamma = 0.0
        for position in self.positions.values():
            instr_status = self.market_status.data[position.instrument_name]
            net_value_instrument = position.amount * instr_status.settlement_price
            net_value += net_value_instrument
            delta += float(net_value_instrument) * instr_status.delta
            gamma += float(net_value_instrument) * instr_status.gamma

        delta /= float(net_value)
        gamma /= float(net_value)

        return OptionMarketBalance(net_value, put_count, call_count, delta, gamma)

    # endregion
