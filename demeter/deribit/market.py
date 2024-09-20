import json
import logging
import os
from _decimal import Decimal
from datetime import date, timedelta
from typing import List, Dict, Tuple
import copy

import pandas as pd
from orjson import orjson

from ._typing import (
    DeribitOptionDescription,
    DeribitTokenConfig,
    DeribitMarketStatus,
    OptionMarketBalance,
    OptionPosition,
    OptionKind,
    BuyAction,
    InstrumentStatus,
    Order,
    SellAction,
    ExpiredAction,
    DeliverAction,
    DERIBIT_OPTION_FREQ,
    InsufficientBalanceError,
    DepositAction,
    WithdrawAction,
)
from .helper import round_decimal, position_to_df
from .. import TokenInfo
from .._typing import DemeterError
from ..broker import Market, MarketInfo, write_func, BASE_FREQ
from ..utils import (
    float_param_formatter,
    get_formatted_predefined,
    STYLE,
    get_formatted_from_dict,
    console_text,
)

DEFAULT_DATA_PATH = "./data"
BASIC_INTERVAL = pd.Timedelta("1h")


def order_converter(array_str) -> List:
    return json.loads(array_str)


class DeribitOptionMarket(Market):
    """
    The Deribit options market can be utilized for options investment or backtesting of Greek hedging strategies.
    In this market, you can buy or sell options based on the current order book.
    Currently, this market only supports taker orders and does not support maker orders.

    :param market_info: key of this market,
    :type market_info: MarketInfo,
    :param token: token for this market, if you want to trade another token, you can initial another market,
    :type token: TokenInfo,
    :param data: hourly orderbook data of deribit option market for this token
    :type data: pd.DataFrame = None,
    :param data_path: str = path to load data,
    :type data_path: str = DEFAULT_DATA_PATH,

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
        self.decimal = self.token_config.min_fee_decimal
        self._balance_cache = None
        # In reality, Deribit is an independent account, and you need to deposit funds into Deribit in order to trade.
        self.balance = Decimal(0)
        self.quote_token = token

    MAX_FEE_RATE = Decimal("0.125")
    ETH = TokenInfo("eth", 18)
    BTC = TokenInfo("btc", 8)
    TOKEN_CONFIGS = {
        ETH: DeribitTokenConfig(
            trade_fee_rate=Decimal("0.0003"),
            delivery_fee_rate=Decimal("0.00015"),
            min_trade_decimal=0,
            min_fee_decimal=-6,
        ),
        BTC: DeribitTokenConfig(
            trade_fee_rate=Decimal("0.0003"),
            delivery_fee_rate=Decimal("0.00015"),
            min_trade_decimal=-1,
            min_fee_decimal=-8,
        ),
    }

    def __str__(self):
        from demeter.utils import orjson_default

        return orjson.dumps(self.description, default=orjson_default).decode()

    @property
    def description(self):
        """
        Get a brief description of this market
        """
        return DeribitOptionDescription(
            type(self).__name__, self._market_info.name, self.token.name, list(self.positions.keys())
        )

    def load_pkl_data(self, path):
        if not os.path.exists(path):
            raise DemeterError(f"{path} doesn't exist")
        self.logger.info(f"start load files in {path}")
        self._data = pd.read_pickle(path)
        self.logger.info("data has been prepared")

    def load_data(self, start_date: date, end_date: date):
        """
        Load data from folder set in data_path. Those data file should be downloaded by demeter, and meet name rule.
        Deribit-option-book-{token}-{day.strftime('%Y%m%d')}.csv
        data can be downloaded from dropbox: https://www.dropbox.com/scl/fo/kwk5kgiseu5rvccjscd0f/ANswtRLzpCxOc6cMTH0oRlE?rlkey=ai071f9695uz287lt8k0bci5e&dl=0

        :param start_date: start day
        :type start_date: date
        :param end_date: end day, the end day will be included
        :type end_date: date
        """
        self.logger.info(f"start load files from {start_date} to {end_date}...")
        day = start_date
        df = pd.DataFrame()
        from tqdm import tqdm

        with tqdm(total=(end_date - start_date).days + 1, ncols=150) as pbar:
            while day <= end_date:
                path = os.path.join(
                    self.data_path,
                    f"Deribit-option-book-{self.token.name}-{day.strftime('%Y%m%d')}.csv",
                )
                if not os.path.exists(path):
                    logging.warning(f"resource file {path} not found")
                    day += timedelta(days=1)
                    pbar.update()
                    continue

                day_df = pd.read_csv(
                    str(path),
                    parse_dates=["time", "expiry_time"],
                    index_col=["time", "instrument_name"],
                    converters={"asks": order_converter, "bids": order_converter},
                )
                day_df.drop(columns=["actual_time", "min_price", "max_price"], inplace=True)
                df = pd.concat([df, day_df])
                day += timedelta(days=1)
                pbar.update()

        self._data = df
        self.logger.info("data has been prepared")

    @float_param_formatter
    def deposit(self, amount: Decimal | float) -> Decimal:
        """
        Add token amount to wallet of deribit, token is quote token in this market.
        :param amount: balance, e.g. 1.2345
        :type amount: Decimal | float
        :return: new balance
        :rtype: Decimal
        """
        self.broker.subtract_from_balance(self.token, amount)
        self._add_to_balance(amount)
        self._record_action(
            DepositAction(
                market=self._market_info,
                token=self.token.name,
                amount=amount,
            )
        )

    def _add_to_balance(self, amount: Decimal | float) -> Decimal:
        self.balance += amount
        return self.balance

    @float_param_formatter
    def withdraw(self, amount: Decimal | float) -> Decimal:
        """
        | Sub token amount to wallet of deribit, token is quote token in this market.

        :param amount: Decimal or float type
        :type amount:  Decimal | float
        :return: new balance
        :rtype: Decimal
        """
        new_balance = self._subtract_from_balance(amount)
        # Actually, withdraw fee should be charged, but the amount is depended on network condition
        # https://www.deribit.com/kb/fees
        self.broker.add_to_balance(self.token, amount)
        self._record_action(
            WithdrawAction(
                market=self._market_info,
                token=self.token.name,
                amount=amount,
            )
        )
        return new_balance

    def _subtract_from_balance(self, amount: Decimal | float) -> Decimal:
        left_over = self.balance - amount
        if left_over < Decimal(0):
            raise InsufficientBalanceError(f"Not enough balance, balance is {self.balance}, amount to sub is {amount}")
        self.balance = left_over
        return left_over

    def check_market(self):
        """
        check market before back test
        """
        if not isinstance(self.data, pd.DataFrame):
            raise DemeterError("data must be type of data frame")

    def set_market_status(
        self,
        data: DeribitMarketStatus,
        price: pd.Series,
    ):
        """
        Set up market status, such as liquidity, price

        :param data: market status
        :type data: Series | DeribitMarketStatus
        :param price: current price of all relative token, based in usd
        :type price: Series

        """
        super().set_market_status(data, price)
        if data.data is None:
            tmr_idx = data.timestamp.floor(DERIBIT_OPTION_FREQ)
            if tmr_idx in self._data.index:
                data.data = self._data.loc[tmr_idx]
            else:
                data.data = pd.DataFrame(columns=self._data.columns)
                if self._is_open():
                    logging.warning(f"Deribit data in {data.timestamp} doesn't exist")
        self._market_status = data

    # region for option market only

    def get_trade_fee(self, amount: Decimal, total_premium: Decimal) -> Decimal:
        """
        Calculate trade fee, according to https://www.deribit.com/kb/fees

        :param amount: instrument amount
        :type amount: Decimal
        :param total_premium: total value of instruments
        :type total_premium: Decimal
        """
        return round_decimal(
            min(
                self.token_config.trade_fee_rate * amount,
                DeribitOptionMarket.MAX_FEE_RATE * total_premium,
            ),
            self.decimal,
        )

    def get_deliver_fee(self, amount: Decimal, total_premium: Decimal):
        """
        Calculate fee of deliver when exercising, according to https://www.deribit.com/kb/fees

        :param amount: instrument amount
        :type amount: Decimal
        :param total_premium: total value of instruments
        :type total_premium: Decimal
        """
        return round_decimal(
            min(
                self.token_config.delivery_fee_rate * amount,
                DeribitOptionMarket.MAX_FEE_RATE * total_premium,
            ),
            self.decimal,
        )

    def get_price_from_data(self) -> pd.Series:
        """
        Get hourly underlying price.
        """
        if self._data is None:
            raise DemeterError("data is empty")
        price = []
        for hour, hour_df in self._data.groupby(level=0):
            price.append({"time": hour, self.token.name: hour_df.iloc[0]["underlying_price"]})
        price_df = pd.DataFrame(price)
        price_df.set_index(["time"], inplace=True)
        # expend to the end of the day
        price_df.loc[price_df.tail(1).index[0].ceil("1d")] = 0
        price_df = price_df.resample(BASE_FREQ).ffill()
        return price_df.drop(price_df.index[-1])

    def __get_trade_amount(self, amount: Decimal):
        """
        Round trade amount, and ensure amount is above dust amount

        :param amount: option amount to buy/sell
        :param amount: Decimal
        """
        if amount < self.token_config.min_amount:
            return self.token_config.min_amount
        return round_decimal(amount, self.token_config.min_trade_decimal)

    def formatted_str(self):
        """
        Return a brief description of this market in pretty format. Used for print in console.
        """
        value = get_formatted_predefined(f"{self.market_info.name}({type(self).__name__})", STYLE["header3"]) + "\n"
        token_dict = {"token": self.token.name}
        value += get_formatted_from_dict(token_dict) + "\n"
        balance: OptionMarketBalance = self.get_market_balance()
        value += (
            get_formatted_from_dict(
                {
                    "delta": console_text.format_value(balance.delta),
                    "gamma": console_text.format_value(balance.gamma),
                }
            )
            + "\n"
        )
        value += get_formatted_predefined("Positions", STYLE["key"]) + "\n"
        supply_df = position_to_df(self.positions)
        value += supply_df.to_string() + "\n" if len(supply_df.index) > 0 else "Empty DataFrame\n"

        return value

    @float_param_formatter
    def estimate_cost(
        self,
        instrument_name: str,
        amount: float | Decimal,
        type: str = "buy",  # buy or sell
        price_in_token: float | Decimal | None = None,
    ):
        amount = self.__get_trade_amount(amount)
        row = self.data.loc[(self._market_status.timestamp, instrument_name)]
        order_list = row.asks if type == "buy" else row.bids
        order_list = copy.deepcopy(order_list)
        used_order = self._deduct_order_amount(amount, order_list, price_in_token)

        total_premium = Decimal(sum([Decimal(t.amount) * Decimal(t.price) for t in used_order]))
        fee_amount = self.get_trade_fee(amount, total_premium)
        return total_premium + fee_amount

    @write_func
    @float_param_formatter
    def buy(
        self,
        instrument_name: str,
        amount: float | Decimal,
        price_in_token: float | Decimal | None = None,
        price_in_usd: float | Decimal | None = None,
        max_mark_price_multiple: float | Decimal | None = None,
    ) -> Tuple[List[Order], Decimal]:
        """
        Buy option.
        if price is not none, will buy at specific price
        or else will buy according to bids

        :param instrument_name: instrument name
        :type instrument_name: str,
        :param amount: amount to buy,
        :type amount: float | Decimal,
        :param price_in_token: price, based in token,
        :type price_in_token: float | Decimal | None = None,
        :param price_in_usd: price, based in usd,
        :type price_in_usd: float | Decimal | None = None,
        :param max_mark_price_multiple: times to mark_price, if order price is greater than mark_price * max_allowed, will not buy at this price


        """
        amount, instrument, price_in_token = self._check_transaction(
            instrument_name, amount, price_in_token, price_in_usd, True, max_mark_price_multiple
        )

        # this actually pass reference of the array, so asks array will be updated in _deduct_order_amount.
        # so when orders are deducted, asks order number will be changed.
        if max_mark_price_multiple is not None:
            asks = list(
                filter(lambda x: x[0] < max_mark_price_multiple * Decimal(instrument.mark_price), instrument.asks)
            )
        else:
            asks = instrument.asks
        # deduct bids amount
        ask_list = self._deduct_order_amount(amount, asks, price_in_token)

        total_premium = Decimal(sum([Decimal(t.amount) * Decimal(t.price) for t in ask_list]))
        fee_amount = self.get_trade_fee(amount, total_premium)
        self._subtract_from_balance(total_premium + fee_amount)

        # add position
        average_price = Order.get_average_price(ask_list)
        if instrument_name not in self.positions.keys():
            self.positions[instrument_name] = OptionPosition(
                instrument_name=instrument_name,
                expiry_time=instrument.expiry_time,
                strike_price=instrument.strike_price,
                type=OptionKind(instrument.type),
                amount=amount,
                avg_buy_price=average_price,
                buy_amount=amount,
                avg_sell_price=Decimal(0),
                sell_amount=Decimal(0),
            )
        else:
            position = self.positions[instrument_name]
            position.avg_buy_price = Order.get_average_price(
                [
                    Order(average_price, amount),
                    Order(position.avg_buy_price, position.buy_amount),
                ]
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
                mark_price=Decimal(str(instrument.mark_price)),
                underlying_price=Decimal(str(instrument.underlying_price)),
                fee=fee_amount,
                orders=ask_list,
            )
        )
        return ask_list, fee_amount

    @staticmethod
    def _find_available_orders(price, order_list) -> List:
        error = Decimal("0.001")
        return list(filter(lambda x: (1 - error) * price < x[0] < (1 + error) * price, order_list))

    @write_func
    @float_param_formatter
    def sell(
        self,
        instrument_name: str,
        amount: float | Decimal,
        price_in_token: float | Decimal | None = None,
        price_in_usd: float | Decimal | None = None,
        max_mark_price_multiple: float | Decimal | None = None,
    ) -> Tuple[List[Order], Decimal]:
        """
        Sell option.
        if price is not none, will sell at specific price
        or else will sell according to asks

        :param instrument_name: instrument name
        :type instrument_name: str,
        :param amount: amount to buy,
        :type amount: float | Decimal,
        :param price_in_token: price, based in token,
        :type price_in_token: float | Decimal | None = None,
        :param price_in_usd: price, based in usd,
        :type price_in_usd: float | Decimal | None = None,
        :param max_mark_price_multiple: times to mark_price, if order price is greater than mark_price * max_allowed, will not buy at this price

        """
        amount, instrument, price_in_token = self._check_transaction(
            instrument_name, amount, price_in_token, price_in_usd, False, max_mark_price_multiple
        )

        # deduct  amount
        if max_mark_price_multiple is not None:
            bids = list(
                filter(lambda x: x[0] > max_mark_price_multiple / Decimal(instrument.mark_price), instrument.bids)
            )
        else:
            bids = instrument.bids

        bid_list = self._deduct_order_amount(amount, bids, price_in_token)

        # write positions back
        # if self.data is not None:
        #     self.data.loc[(self._market_status.timestamp, instrument_name), "bids"] = bids

        total_premium = Decimal(sum([Decimal(t.amount) * Decimal(t.price) for t in bid_list]))
        fee = self.get_trade_fee(amount, total_premium)
        self._add_to_balance(total_premium - fee)

        # subtract position
        average_price = Order.get_average_price(bid_list)
        if instrument_name not in self.positions.keys():
            raise DemeterError("No such instrument position")

        position = self.positions[instrument_name]
        position.avg_sell_price = Order.get_average_price(
            [
                Order(average_price, amount),
                Order(position.avg_sell_price, position.sell_amount),
            ]
        )
        position.sell_amount += amount
        position.amount -= amount

        if position.amount <= Decimal(0):
            del self.positions[instrument_name]

        self._record_action(
            SellAction(
                market=self._market_info,
                instrument_name=instrument_name,
                type=OptionKind(instrument.type),
                average_price=average_price,
                amount=amount,
                total_premium=total_premium,
                mark_price=Decimal(str(instrument.mark_price)),
                underlying_price=Decimal(str(instrument.underlying_price)),
                fee=fee,
                orders=bid_list,
            )
        )
        return bid_list, fee

    def _deduct_order_amount(self, amount, orders, price_in_token) -> List[Order]:
        """
        subtract amount from asks/bids. e.g. if bid1 is run out, will deduct bid2. etc.
        """
        order_list = []
        if price_in_token is not None:
            for order in orders:
                if price_in_token == Decimal(str(order[0])):
                    order[1] -= amount
                    order_list.append(Order(price_in_token, amount))
        else:
            amount_to_deduct = amount
            for order in orders:
                if order[1] == 0 or order[1] == Decimal(0):
                    continue
                should_deduct = min(Decimal(str(order[1])), amount_to_deduct)
                amount_to_deduct -= should_deduct
                order[1] -= float(should_deduct)
                order_list.append(Order(Decimal(str(order[0])), should_deduct))
                if order[1] > 0 or amount_to_deduct == Decimal(0):
                    break
        return order_list

    def _check_transaction(
        self, instrument_name, amount, price_in_token, price_in_usd, is_buy, max_mark_price_multiple=None
    ) -> Tuple[Decimal, InstrumentStatus, Decimal]:
        """
        | Check transaction,
        | - ensure instrument exists
        | - ensure instrument is open
        | - ensure there are enough amount
        | - ensure price is in asks/bids

        :param max_mark_price_multiple: times to mark_price, if order price is greater than mark_price * max_allowed, will not buy beyond price
        """
        if instrument_name not in self._market_status.data.index:
            raise DemeterError(f"{instrument_name} is not in current orderbook")
        instrument: InstrumentStatus = self._market_status.data.loc[instrument_name]
        if instrument.state != "open":
            raise DemeterError(f"state of {instrument_name} is not open")
        if amount < self.token_config.min_amount:
            raise DemeterError(
                f"amount should greater than min amount {self.token_config.min_amount} {self.token.name}"
            )
        amount = self.__get_trade_amount(amount)
        if price_in_usd is not None and price_in_token is None:
            price_in_token = price_in_usd / instrument.underlying_price

        if is_buy:
            if max_mark_price_multiple is not None:
                max_price = max_mark_price_multiple * Decimal(instrument.mark_price)
                available_orders = list(filter(lambda x: x[0] < max_price, instrument.asks))
            else:
                available_orders = instrument.asks
        else:
            if max_mark_price_multiple is not None:
                min_price = max_mark_price_multiple / Decimal(instrument.mark_price)
                available_orders = list(filter(lambda x: x[0] > min_price, instrument.bids))
            else:
                available_orders = instrument.bids

        if price_in_token is not None:
            # to prevent error in decimal
            available_orders = DeribitOptionMarket._find_available_orders(price_in_token, available_orders)

            if len(available_orders) < 1:
                raise DemeterError(
                    f"{instrument_name} doesn't have a order in price {price_in_token} {self.token.name}"
                )
            price_in_token = Decimal(str(available_orders[0][0]))
            available_amount = Decimal(available_orders[0][1])
        else:
            available_amount = sum([Decimal(x[1]) for x in available_orders])
        if amount > available_amount:
            raise DemeterError(
                f"insufficient order to buy {instrument_name}, required amount is {amount}, "
                f"available amount is {available_amount}"
            )

        return amount, instrument, price_in_token

    def update(self):
        """
        Trigger update of this market
        """
        if self._is_open():
            self.check_option_exercise()

    def _is_open(self):
        """
        ensure this market is writable. e.g. deribit option market only has data at the hour,
        but uniswap data is minutely. so at the rest 59 minutes, deribit option market is readonly.
        which means, you can read status, but you can not buy or sell options.
        """
        return self._market_status.timestamp == self._market_status.timestamp.floor(DERIBIT_OPTION_FREQ)

    def get_market_balance(self) -> OptionMarketBalance:
        """
        Get market asset balance, such as current positions, net values

        :return: Balance in this market includes net value, position value
        :rtype: MarketBalance
        """
        if self._is_open():
            total_premium = Decimal(0)
            delta = gamma = Decimal(0)
            for position in self.positions.values():
                # data may missing due to unstable collect server
                if position.instrument_name not in self.market_status.data.index:
                    continue
                instr_status = self.market_status.data.loc[position.instrument_name]
                instrument_premium = position.amount * round_decimal(instr_status.mark_price, self.decimal)
                total_premium += instrument_premium
                delta += instrument_premium * round_decimal(instr_status.delta, self.decimal)
                gamma += instrument_premium * round_decimal(instr_status.gamma, self.decimal)

            delta = Decimal(0) if total_premium == Decimal(0) else delta / total_premium
            gamma = Decimal(0) if total_premium == Decimal(0) else gamma / total_premium
            equity = self.balance + total_premium
            self._balance_cache = OptionMarketBalance(equity, self.balance, total_premium, delta, gamma)
        return self._balance_cache

    # region exercise
    def check_option_exercise(self):
        """
        | loop all the option position,
        | if expired, if option position is in the money, then exercise.
        | if out of the money, then abandon
        """
        key_to_remove = []
        for pos_key, position in self.positions.items():
            if self._market_status.timestamp >= position.expiry_time:
                # should not happen
                if position.instrument_name in self._market_status.data.index:
                    instrument: InstrumentStatus = self.market_status.data.loc[position.instrument_name]
                else:
                    logging.warning(f"{position.instrument_name} is not in current orderbook")
                    instrument = InstrumentStatus(mark_price=0, underlying_price=self._price_status[self.token.name])

                deliver_amount = deliver_fee = None
                if position.type == OptionKind.put and position.strike_price > instrument.underlying_price:
                    deliver_amount, deliver_fee = self._deliver_option(position, instrument, False)
                elif position.type == OptionKind.call and position.strike_price < instrument.underlying_price:
                    deliver_amount, deliver_fee = self._deliver_option(position, instrument, True)
                if deliver_amount is not None:
                    self._record_action(
                        DeliverAction(
                            market=self._market_info,
                            instrument_name=pos_key,
                            type=position.type,
                            mark_price=round_decimal(instrument.mark_price, self.decimal),
                            amount=position.amount,
                            total_premium=position.amount * round_decimal(instrument.mark_price, self.decimal),
                            strike_price=position.strike_price,
                            underlying_price=round_decimal(instrument.underlying_price, self.decimal),
                            deriver_amount=deliver_amount,
                            fee=deliver_fee,
                            income_amount=deliver_amount - deliver_fee,
                        )
                    )
                key_to_remove.append(pos_key)

        for pos_key in key_to_remove:
            position = self.positions[pos_key]
            if pos_key in self.market_status.data.index:
                instrument: InstrumentStatus = self.market_status.data.loc[position.instrument_name]
            else:
                instrument = InstrumentStatus(mark_price=0, underlying_price=self._price_status[self.token.name])
            self._record_action(
                ExpiredAction(
                    market=self._market_info,
                    instrument_name=pos_key,
                    type=position.type,
                    mark_price=round_decimal(instrument.mark_price, self.decimal),
                    amount=position.amount,
                    total_premium=position.amount * round_decimal(instrument.mark_price, self.decimal),
                    strike_price=position.strike_price,
                    underlying_price=round_decimal(instrument.underlying_price, self.decimal),
                )
            )
            del self.positions[pos_key]

    def _deliver_option(
        self, option_pos, instrument: InstrumentStatus, is_call
    ) -> Tuple[Decimal | None, Decimal | None]:
        """
        deliver option
        """
        fee = self.get_deliver_fee(
            option_pos.amount,
            option_pos.amount * round_decimal(instrument.mark_price, self.decimal),
        )
        if is_call:
            price_diff = instrument.underlying_price - option_pos.strike_price
        else:
            price_diff = option_pos.strike_price - instrument.underlying_price

        balance_to_add = round_decimal(
            option_pos.amount * Decimal(price_diff / instrument.underlying_price),
            self.decimal,
        )
        if balance_to_add <= fee:
            return None, None
        self._add_to_balance(balance_to_add - fee)
        return balance_to_add, fee

    # endregion

    # endregion

    def _resample(self, freq: str):
        interval_delta = pd.Timedelta(freq)
        if interval_delta <= BASIC_INTERVAL:
            return
        else:
            self._data = self._data.groupby(level=1).resample(freq, level=0).first().swaplevel(1, 0)
