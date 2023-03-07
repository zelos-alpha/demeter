from typing import Dict, List

import pandas as pd

from .trigger import Trigger
from .. import Broker, MarketDict, AccountStatus, AssetDict, Asset
from .._typing import DemeterError
from ..broker import MarketInfo, RowData, BaseAction, Market


class Strategy(object):
    """
    strategy parent class, all user strategy should inherit this class
    """

    def __init__(self):
        self.broker: Broker = None
        self.data: MarketDict[pd.DataFrame] = MarketDict()
        self.markets: MarketDict[Market] = MarketDict()
        self.number_format = ".8g"
        self.prices: pd.DataFrame = None
        self.triggers: [Trigger] = []
        self.account_status: List[AccountStatus] = []
        self.assets: AssetDict[Asset] = AssetDict()
        self.actions: List[BaseAction] = []

    def initialize(self):
        """
        initialize your strategy, this will be called before self.on_bar()

        """
        pass

    def before_bar(self, row_data: MarketDict[RowData]):
        """
        called before triggers on each row, at this time, fees are not updated yet. you can add some indicator or add some actions

        :param row_data: row data, include columns load from data, converted data( price, volumn, and timestamp, index), indicators(such as ma)
        :type row_data: Union[{MarketInfo:RowData}, pd.Series]

        """

        pass

    def on_bar(self, row_data: MarketDict[RowData]):
        """
        called after triggers on each row, at this time, fees and account status are not updated yet. you can add some actions here

        :param row_data: row data, include columns load from data, converted data( price, volumn, and timestamp, index), indicators(such as ma)
        :type row_data: Union[{MarketInfo:RowData}, pd.Series]
        """
        pass

    def after_bar(self, row_data: MarketDict[RowData]):
        """
        called after fees and account status are updated on each row. you can add some statistic logic here

        :param row_data: row data, include columns load from data, converted data( price, volumn, and timestamp, index), indicators(such as ma)
        :type row_data: Union[{MarketInfo:RowData}, pd.Series]
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

        :param name: column name
        :type name: str
        :param line: data
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
