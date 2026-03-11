from decimal import Decimal
from typing import Tuple, List
from ._typing import Side
from .CoreOrderUtils import CoreOrderUtils
from .OrderBookUtils import OrderBookStorageStruct

class MarketEntry(CoreOrderUtils):

    def get_next_n_ticks(self, book_data: OrderBookStorageStruct, side: Side, start_tick: int,
                         n_ticks: int) -> Tuple[List[int], List[Decimal]]:
        return self._get_next_n_ticks(book_data, side, start_tick, n_ticks)  # todo