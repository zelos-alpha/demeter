from decimal import Decimal

from ._typing import BaseAction
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
        self.data: Lines = data
        self.broker: Broker = None
        self._record_action_callback = None
        self.data_path: str = data_path

    @property
    def net_value(self) -> Decimal:
        return Decimal(0)

    def record_action(self, action: BaseAction):
        if self._record_action_callback is not None:
            self._record_action_callback(action)
