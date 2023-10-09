from datetime import datetime
from typing import Dict, List

import pandas as pd

from .trigger import Trigger
from .. import Broker, MarketDict, AccountStatus, AssetDict, Asset
from .._typing import DemeterError
from ..broker import MarketInfo, MarketStatus, BaseAction, Market


class Strategy(object):
    """
    strategy parent class, all user strategy should inherit this class
    """

    def __init__(self):
        self.broker: Broker | None = None
        self.data: MarketDict[pd.DataFrame] = MarketDict()
        self.markets: MarketDict[Market] = MarketDict()
        self.number_format = ".8g"
        self.prices: pd.DataFrame | None = None
        self.triggers: [Trigger] = []
        self.account_status: List[AccountStatus] = []
        self.assets: AssetDict[Asset] = AssetDict()
        self.actions: List[BaseAction] = []

    def initialize(self):
        """
        initialize your strategy, this will be called before self.on_bar()

        """
        pass

    def on_bar(self, row_data: MarketDict[MarketStatus], price: pd.Series, timestamp: datetime):
        """
        called after triggers on each row, at this time, fees and account status are not updated yet. you can add some actions here

        :param row_data: row data, include columns load from data, converted data( price, volumn, and timestamp, index), indicators(such as ma)
        :type row_data: Union[{MarketInfo:MarketStatus}, pd.Series]
        :param price: current price of all tokens
        :type price: pd.Series
        """
        pass

    def after_bar(self, row_data: MarketDict[MarketStatus], price: pd.Series, timestamp: datetime):
        """
        called after fees and account status are updated on each row. you can add some statistic logic here

        :param row_data: row data, include columns load from data, converted data( price, volumn, and timestamp, index), indicators(such as ma)
        :type row_data: Union[{MarketInfo:MarketStatus}, pd.Series]
        :param price: current price of all tokens
        :type price: pd.Series
        """
        pass

    def finalize(self):
        """
        this will run after all the data processed.

        """
        pass

    def notify(self, action: BaseAction):
        """
        notify if non-basic action happens

        :param action:  action
        :type action: BaseAction
        """
        pass

    def _add_column(self, market: MarketInfo | Market, name: str, line: pd.Series):
        """
        add a column to data

        :param name: column name, sma
        :type name: str
        :param market: market1
        :type market: MarketInfo
        :param line: data,
        2022-08-20 00:00:00            NaN
        2022-08-20 00:01:00            NaN
        2022-08-20 00:02:00            NaN
        2022-08-20 00:03:00            NaN
        2022-08-20 00:04:00            NaN
                                  ...
        2022-08-20 23:55:00    1568.069688
        2022-08-20 23:56:00    1568.036998
        2022-08-20 23:57:00    1568.004837
        2022-08-20 23:58:00    1567.990103
        2022-08-20 23:59:00    1567.975368
        Freq: T, Name: price, Length: 1440, dtype: float64
        :type line: Line
        """
        if not isinstance(line.index, pd.core.indexes.datetimes.DatetimeIndex):
            raise DemeterError("date index must be datetime")
        if isinstance(market, MarketInfo):
            self.broker.markets[market].data[name] = line
        elif isinstance(market, Market):
            market.data[name] = line
        else:
            raise DemeterError(f"{market} is not a valid market")
