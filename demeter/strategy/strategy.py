from typing import List, Callable

import pandas as pd

from .trigger import Trigger
from .. import Broker, MarketDict, AccountStatus, AssetDict, Asset, RowData
from .._typing import DemeterError
from ..broker import MarketInfo, BaseAction, Market


class Strategy(object):
    """
    Parent class of strategy, all user's strategy should inherit this class
    """

    def __init__(self):
        self.broker: Broker | None = None
        self.data: MarketDict[pd.DataFrame] = MarketDict()
        self.markets: MarketDict[Market] = MarketDict()
        self.prices: pd.DataFrame | None = None
        self.triggers: [Trigger] = []
        self.account_status: List[AccountStatus] = []
        self.account_status_df: pd.DataFrame | None = None
        self.comment_last_action: Callable = lambda msg: msg
        self.assets: AssetDict[Asset] = AssetDict()
        self.actions: List[BaseAction] = []
        self.log: Callable = lambda t, msg, info: msg

    def initialize(self):
        """
        Initialize your strategy, this will be called before iteration start

        """
        pass

    def on_bar(self, row_data: RowData):
        """
        Called after triggers on each iteration, at this time, market are not updated yet(Take uniswap market for example, fee of this minute are not added to positions).

        :param row_data: data in this iteration, include current timestamp, price, all columns data, and indicators(such as simple moving average)
        :type row_data: RowData
        """
        pass

    def after_bar(self, row_data: RowData):
        """
        called after market are updated on each iteration

        :param row_data: data in this iteration, include current timestamp, price, all columns data, and indicators(such as simple moving average)
        :type row_data: RowData
        """
        pass

    def finalize(self):
        """
        this will run after all the data processed. You can access broker.account_status, broker.market.status to do some calculation

        """
        pass

    def notify(self, action: BaseAction):
        """
        Notify when an action(buy/sell) happens

        :param action:  action taken in market.
        :type action: BaseAction
        """
        pass

    def add_column(self, market: MarketInfo | Market, name: str, column_data: pd.Series):
        """
        add a column to data in a market

        :param name: column name, like sma
        :type name: str
        :param market: which market to update
        :type market:  MarketInfo | Market
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
