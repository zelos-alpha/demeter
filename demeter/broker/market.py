import logging
from decimal import Decimal

from ._typing import BaseAction, MarketStatus
from .broker import Broker
from .. import Lines

DEFAULT_DATA_PATH = "./data"


class Market:
    """
    note: only get properties are allow in this base class
    """

    def __init__(self,
                 data: Lines = None,
                 data_path=DEFAULT_DATA_PATH):
        self._data: Lines = data
        self.broker: Broker = None
        self._record_action_callback = None
        self.data_path: str = data_path
        self.logger = logging.getLogger(__name__)
        self.market_status = None

    @property
    def net_value(self) -> Decimal:
        return Decimal(0)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if isinstance(value, Lines):
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

    def set_market_status(self, data):
        self.market_status = data
    # endregion

    def get_market_status(self, *args, **kwargs) -> MarketStatus:
        pass