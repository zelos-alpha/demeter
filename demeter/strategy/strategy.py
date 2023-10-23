from datetime import datetime
from typing import Dict, List

import pandas as pd

from .trigger import Trigger
from .. import Broker, MarketDict, AccountStatus, AssetDict, Asset, RowData
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

    def on_bar(self, row_data: RowData):
        """
        called after triggers on each row, at this time, fees and account status are not updated yet. you can add some actions here

        :param row_data: row data, include columns load from data, converted data( price, volumn, and timestamp, index), indicators(such as ma)
        :type row_data: Union[{MarketInfo:MarketStatus}, pd.Series]
        :param price: current price of all tokens
        :type price: pd.Series
        """
        pass

    def after_bar(self, row_data: RowData):
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

    def _add_column(self, market: MarketInfo | Market, name: str, column_data: pd.Series):
        """
        add a column to data in a market

        :param name: column name, like sma
        :type name: str
        :param market: which market to update
        :type market: MarketInfo
        :param column_data: One data column, it should have the same timestamp index with market.data
        :type column_data: pd.Series
        """
        if not isinstance(column_data.index, pd.core.indexes.datetimes.DatetimeIndex):
            raise DemeterError("date index must be datetime")
        if isinstance(market, MarketInfo):
            self.broker.markets[market].data[name] = column_data
        elif isinstance(market, Market):
            market.data[name] = column_data
        else:
            raise DemeterError(f"{market} is not a valid market")
