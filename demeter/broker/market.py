from decimal import Decimal

from .action_history import ActionRecorder
from .broker import Broker
from .. import Lines


class Market:
    """
    note: only get properties are allow in this base class
    """

    def __init__(self,
                 data: Lines = None,
                 ):
        self.data: Lines = data
        self.broker: Broker = None
        self.action_recorder: ActionRecorder = None

    @property
    def net_value(self) -> Decimal:
        return Decimal(0)
