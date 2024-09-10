import logging
from decimal import Decimal
from functools import wraps
from typing import Dict, Callable

import pandas as pd

from ._typing import BaseAction, MarketBalance, MarketStatus, MarketInfo, RowData
from .._typing import DECIMAL_0, DemeterError, TokenInfo, USD

DEFAULT_DATA_PATH = "./data"


def write_func(func):
    @wraps(func)
    def wrapper_func(*args, **kwargs):
        instance = args[0]
        if not instance.is_open:
            raise DemeterError(f"{instance.market_info.name} is not open.")
        ret = func(*args, **kwargs)
        instance.has_update = True
        return ret

    return wrapper_func


class Market:
    """

    | Market is the place to invest your assets.
    | This is an abstract class, you should use subclass instead this one

    :param market_info: Key of this market.
    :type market_info: MarketInfo
    :param data: Data is used to simulate market status. usually it is downloaded from log event of ethereum, then indexed by timestamp with minute interval.
    :type data: DataFrame
    :param data_path: default folder path for data files. Each day has a corresponding csv file.
    :type data_path: str
    """

    def __init__(self, market_info: MarketInfo, data: pd.DataFrame = None, data_path=DEFAULT_DATA_PATH):
        """
        Initialize a Market

        """
        self._data: pd.DataFrame = data
        self._market_info: MarketInfo = market_info
        self.broker = None
        self._record_action_callback: Callable[[BaseAction], None] = None
        self.data_path: str = data_path
        self.logger = logging.getLogger(__name__)
        self._market_status: MarketStatus = MarketStatus(None, pd.Series())
        self._price_status: pd.Series | None = None
        # if some var that related to market status has changed, should set this to True,
        # then the second set_market_status in every minute will be triggerd
        # e.g. At uniswap market, when add liquidity in the head of the minute, this flag will be set to True,
        # so user liquidity will be added to total liquidity in this minute, and get more fee
        # remember set this flag to False after set_market_status
        self.has_update = False
        self.open: Callable[[RowData], None] = None
        # if market interval is minutely, is_open will always true,
        # or it will be false until timestamp is on its interval
        self.is_open: bool = True
        self.quote_token: TokenInfo = USD

    def __str__(self):
        return f"{self._market_info.name}:{type(self).__name__}"

    @property
    def market_info(self) -> MarketInfo:
        """
        Get market info, it is the key of a market.
        """
        return self._market_info

    @property
    def data(self) -> pd.DataFrame:
        """
        | Market data is used to simulate the status of market. For example, in uniswap market, data describe pool liquidity, price of this pool.
        | Usually data is got by demeter-fetch which can download and decode on chain event log. Data will be saved in CSV format, each day has a corresponding csv file.
        | Those csv file is indexed by timestamp, and resampled to one minute.
        | Data files will be loaded as dataframe. The whole back test process is based on minutely timestamp.

        :return: market data
        :rtype: DataFrame
        """
        return self._data

    @data.setter
    def data(self, value):
        """
        Set data and check its type
        """
        if isinstance(value, pd.DataFrame):
            self._data = value
        else:
            raise ValueError()

    def _record_action(self, action: BaseAction):
        if self._record_action_callback is not None:
            self._record_action_callback(action)

    # region for subclass to override
    def check_market(self):
        """
        check market before back test
        """
        if not isinstance(self.data, pd.DataFrame):
            raise DemeterError("data must be type of data frame")
        if not isinstance(self.data.index, pd.core.indexes.datetimes.DatetimeIndex):
            raise DemeterError("date index must be datetime")

    def update(self):
        """
        Update market in every loop. It was used for triggering market status calculation.
        """
        pass

    @property
    def market_status(self):
        """
        Get market status, such as current total liquidity, current apy, etc.
        In short, it's a row of market.data.
        """
        return self._market_status

    def set_market_status(
        self,
        data: MarketStatus,
        price: pd.Series,
    ):
        """
        Set up market status, such as liquidity, price

        :param data: market status
        :type data: Series | MarketStatus
        :param price: current price
        :type price: Series

        """
        # self._market_status = data
        self._price_status = price
        self.is_open = True if self._data is None or data.timestamp in self._data.index else False
        self.has_update = False

    def get_market_balance(self) -> MarketBalance:
        """
        Get market asset balance, such as current positions, net values

        :return: Balance in this market includes net value, position value
        :rtype: MarketBalance
        """
        return MarketBalance(DECIMAL_0)

    def formatted_str(self):
        """
        Get a colorful brief description to print in console.
        """
        return ""

    def _resample(self, freq: str):
        """
        Resample data in this market
        """
        pass

    # endregion
