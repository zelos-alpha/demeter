from _decimal import Decimal
from datetime import datetime
from typing import Dict, List

import pandas as pd

from .. import MarketInfo, DECIMAL_0, DemeterError, TokenInfo
from ..broker import Market, BaseAction, MarketStatus, MarketBalance

DEFAULT_DATA_PATH = "./data"


class AaveV3Market(Market):
    def __init__(
        self,
        market_info: MarketInfo,
        data: pd.DataFrame = None,
    ):
        super().__init__(market_info=market_info, data=data)

    def __str__(self):
        pass

    @property
    def market_info(self) -> MarketInfo:
        return self._market_info

    @property
    def data(self):
        """
        data got from uniswap pool
        :return:
        :rtype:
        """
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

    @property
    def tokens(self) -> List[TokenInfo]:
        pass

    @property
    def supplies(self):
        pass

    @property
    def borrows(self):
        pass

    # region for subclass to override
    def check_asset(self):
        pass

    def update(self):
        """
        update status various in markets. eg. liquidity fees of uniswap
        :return:
        :rtype:
        """
        pass

    @property
    def market_status(self):
        return self._market_status

    def set_market_status(self, timestamp: datetime, data: pd.Series | MarketStatus, price: pd.Series):
        """
        set up market status, such as liquidity, price
        :param timestamp: current timestamp
        :type timestamp: datetime
        :param data: market status
        :type data: pd.Series | MarketStatus
        """
        if isinstance(data, MarketStatus):
            self._market_status = data
        else:
            self._market_status = MarketStatus(timestamp)
        self._price_status = price

    def get_market_balance(self, prices: pd.Series | Dict[str, Decimal]) -> MarketBalance:
        """
        get market asset balance
        :param prices: current price of each token
        :type prices: pd.Series | Dict[str, Decimal]
        :return:
        :rtype:
        """
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

    def formatted_str(self):
        return ""

    # endregion

    def supply(self):
        pass

    def withdraw(self):
        pass

    def borrow(self):
        pass

    def repay(self):
        pass

    def _liquidate(self):
        pass
