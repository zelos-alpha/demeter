import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Callable

import pandas as pd

from ._typing import BaseAction, MarketBalance, MarketStatus, MarketInfo
from .._typing import DECIMAL_0, DemeterError

DEFAULT_DATA_PATH = "./data"


class Market:
    """
    Market is the place to invest your assets.

    But this is an abstract class, you should use subclass instead this one
    note: only get properties are allow in this base class
    """

    def __init__(self, market_info: MarketInfo, data: pd.DataFrame = None, data_path=DEFAULT_DATA_PATH):
        """
        Initialize a Market
        :param market_info: uni_market
        :param data: None or dataframe data
        :param data_path: default path for data
        """
        self._data: pd.DataFrame = data
        self._market_info: MarketInfo = market_info
        self.broker = None
        self._record_action_callback: Callable[[BaseAction], None] = None
        self.data_path: str = data_path
        self.logger = logging.getLogger(__name__)
        self._market_status: MarketStatus = MarketStatus(None, pd.Series())
        self._price_status: pd.Series | None = None
        # if some var that related to market status has changed, should set this to True, then the second set_market_status in every minute will be triggerd
        # eg: At uniswap market, when add liquidity in the head of the minute, this flag will be set to True,
        # so user liquidity will be added to total liquidity in this minute, and get more fee
        # remember set this flag to False after set_market_status
        self.has_update = False

    def __str__(self):
        return f"{self._market_info.name}:{type(self).__name__}"

    @property
    def market_info(self) -> MarketInfo:
        """
        Get market info, it is the key of a market.
        """
        return self._market_info

    @property
    def data(self)->pd.DataFrame:
        """
        Market data is download from blockchain. It's decoded from event logs. and resampled to one minute.
        Its type is dataframe, and indexed by timestamp. The whole back test process is based on its index.
        For example. if data in a day is loaded, since a day has 1440 minutes, back test will loop 1440 times
        Data can be downloaded by demeter-fetch
        :return: data
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
        self._market_status = data
        self._price_status = price
        self.has_update = False

    def get_market_balance(self, prices: pd.Series | Dict[str, Decimal]) -> MarketBalance:
        """
        Get market asset balance, such as current positions, net values
        :param prices: current price of each token
        :type prices: pd.Series | Dict[str, Decimal]
        :return: Balance in this market includes net value, position value
        :rtype: MarketBalance
        """
        return MarketBalance(DECIMAL_0)

    def formatted_str(self):
        """
        Get a colorful brief description to print in console.
        """
        return ""

    # endregion
