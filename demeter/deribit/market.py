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

    TOKEN_CONFIGS = {ETH: DeribitTokenConfig(Decimal(0.0003), 0), BTC: DeribitTokenConfig(Decimal(0.0003), -1)}
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
            day_df.drop(columns=["actual_time"], inplace=True)
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

    @float_param_formatter
    def get_fee_rate(self, trade_value: float | Decimal) -> Decimal:
        """
        https://www.deribit.com/kb/fees
        """
        return min(self.token_config.fee_amount, DeribitOptionMarket.MAX_FEE_RATE * trade_value)

    def __get_extern_underlying_price(self, token_prices: pd.Series) -> float:
        """
        a shortcut to get underlying token price of this market
        """
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

        buy order price should in min_price and max_price
        """

        # match order
        # calc fee
        # add position
        # modify balance
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

        if price_in_token is not None:
            # to prevent error in decimal
            match_bid = list[filter(lambda x: 0.995 * price_in_token < x[0] < 1.005 * price_in_token, instrument.bids)]
            if len(match_bid) < 1:
                raise DemeterError(
                    f"{instrument_name} doesn't have a order in price {price_in_token} {self.token.name}"
                )
            price_in_token = match_bid[0][0]
            available_amount = match_bid[0][1]
        else:
            available_amount = sum([x[1] for x in instrument.bids])
        if amount < available_amount:
            raise DemeterError(
                f"insufficient order to buy, required amount is {amount}, available amount is {available_amount}"
            )

        # deduct bids amount
        bids = instrument.bids
        bid_list = []
        if price_in_token is not None:
            for bid in bids:
                if price_in_token == bid[0]:
                    bid[1] -= amount
                    bid_list.append(Order(bid[0], amount))
        else:
            amount_to_deduct = amount
            for bid in bids:
                should_deduct = min(bid[1], amount_to_deduct)
                amount_to_deduct -= should_deduct
                bid[1] -= should_deduct
                bid_list.append(Order(bid[0], should_deduct))
                if bid[1] > 0:
                    break

        total_value = sum([t.amount * t.price for t in bid_list])
        self.broker.subtract_from_balance(total_value)

        instrument.bids = bids
        # add position
        average_price = Order.get_average_price(bid_list)
        if instrument_name not in self.positions.keys():
            self.positions[instrument_name] = OptionPosition(
                instrument_name, OptionKind(instrument.type), amount, average_price, amount, 0, 0
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
                amount=amount,
                value=total_value,
                mark_price=instrument.mark_price,
                underlying_price=instrument.underlying_price,
                orders=bid_list,
            )
        )
        return bid_list

    @write_func
    def sell(
        self, instrument: str, amount: Decimal, price_in_token: float | None = None, price_in_usd: float | None = None
    ):

        pass

    def check_option_expire(self):
        """
        loop all the option position,
        if expired, if option position is in the money, then exercise.
        if out of the money, then abandon
        """
        pass

    @write_func
    def _exercise(self, option_pos):
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
            net_value_instrument = position.amount * instr_status.mark_price
            net_value += net_value_instrument
            delta += float(net_value_instrument) * instr_status.delta
            gamma += float(net_value_instrument) * instr_status.gamma

        delta /= float(net_value)
        gamma /= float(net_value)

        return OptionMarketBalance(net_value, put_count, call_count, delta, gamma)

    # endregion
