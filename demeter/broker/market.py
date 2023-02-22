import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict

import pandas as pd

from ._typing import BaseAction, MarketBalance, MarketStatus, MarketInfo
from .._typing import DECIMAL_0, DemeterError

DEFAULT_DATA_PATH = "./data"


class Market:
    """
    note: only get properties are allow in this base class
    """

    def __init__(self,
                 market_info: MarketInfo,
                 data: pd.DataFrame = None,
                 data_path=DEFAULT_DATA_PATH):
        self._data: pd.DataFrame = data
        self._market_info: MarketInfo = market_info
        self.broker = None
        self._record_action_callback = lambda x: x
        self.data_path: str = data_path
        self.logger = logging.getLogger(__name__)
        self._market_status = MarketStatus(None)

    def __str__(self):
        return f"{self._market_info.name}:{type(self).__name__}"

    @property
    def market_info(self) -> MarketInfo:
        return self._market_info

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if isinstance(value, pd.DataFrame):
            self._data = value
        else:
            raise ValueError()

    def record_action(self, action: BaseAction):
        if self._record_action_callback is not None:
            self._record_action_callback(action)

    # region for subclass to override
    def check_asset(self):
        pass

    def update(self):
        pass

    @property
    def market_status(self):
        return self._market_status

    def set_market_status(self, timestamp: datetime, data: pd.Series | MarketStatus):
        if isinstance(data, MarketStatus):
            self._market_status = data
        else:
            self._market_status = MarketStatus(timestamp)

    def get_market_balance(self, prices: pd.Series | Dict[str, Decimal]) -> MarketBalance:
        return MarketBalance(DECIMAL_0)

    def check_before_test(self):
        """
        do some check for this market before back test start
        :return:
        :rtype:
        """
        if not isinstance(self.data, pd.DataFrame):
            raise DemeterError("data must be type of data frame")
        if not isinstance(self.data.index, pd.core.indexes.datetimes.DatetimeIndex):
            raise DemeterError("date index must be datetime")
    # endregion
