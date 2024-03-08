import json
import os
import token
from _decimal import Decimal
from datetime import date, timedelta
from typing import Dict, List, Set

import pandas as pd

from . import helper
from ._typing import DeribitOptionMarketDescription, DeribitTokenConfig, DeribitMarketStatus
from .helper import round_decimal

from .. import DemeterError, TokenInfo
from .._typing import DECIMAL_0, UnitDecimal, ChainType
from ..broker import Market, MarketInfo, write_func
from ..utils import get_formatted_predefined, STYLE, get_formatted_from_dict
from ..utils.application import require, float_param_formatter, to_decimal

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

    TOKEN_CONFIGS = {ETH: DeribitTokenConfig(Decimal(0.0003), 0), BTC: DeribitTokenConfig(Decimal(0.0003), -1)}
    MAX_FEE_RATE = 0.125

    def __str__(self):
        return json.dumps(self.description()._asdict())

    def description(self):
        """
        Get a brief description of this market
        """
        return DeribitOptionMarketDescription(type(self).__name__, self._market_info.name, 0)

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
            day_df = day_df[day_df["state"] == "open"]
            day_df.drop(columns=["state", "actual_time"], inplace=True)
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

    def __get_price(self, token_prices: pd.Series) -> Decimal:
        """
        a shortcut to get underlying token price of this market
        """
        return token_prices[self.token.name]

    def __get_trade_amount(self, amount: Decimal):
        if amount < self.token_config.min_amount:
            return self.token_config.min_amount
        return round_decimal(amount, self.token_config.min_decimal)

    @write_func
    @float_param_formatter
    def buy(self, amount: Decimal, price_in_token: Decimal | float | None = None, price_in_usd: Decimal | float | None = None):
        """
        if price is not none, will set at that price
        or else will buy according to bids

        buy order price should in min_price and max_price
        """

        # match order
        # calc fee
        # add position
        # modify balance

        pass

    @write_func
    @float_param_formatter
    def sell(self, amount: Decimal, price_in_token: Decimal | float | None = None, price_in_usd: Decimal | float | None = None):

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

    def get_market_balance(self, prices: pd.Series | Dict[str, Decimal]) -> MarketBalance:
        """
        Get market asset balance, such as current positions, net values

        :param prices: current price of each token
        :type prices: pd.Series | Dict[str, Decimal]
        :return: Balance in this market includes net value, position value
        :rtype: MarketBalance
        """
        return MarketBalance(DECIMAL_0)

    # endregion
