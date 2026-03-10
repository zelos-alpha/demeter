from ._typing import Side
from dataclasses import dataclass
from typing import List, Tuple, Dict
from decimal import Decimal


@dataclass
class Tick:
    pass


@dataclass
class TickBitmap:
    pass


@dataclass
class OrderBook:
    tick_bitmap: TickBitmap
    ticks: Dict[int, Tick]


@dataclass
class OrderBookStorageStruct:
    book_long: OrderBook
    book_short: OrderBook


class OrderBookUtils:
    def _get_book(self, book: OrderBookStorageStruct, side: Side) -> OrderBook:
        return book.book_long if side == Side.LONG else book.book_short

    def _get_next_n_ticks(self, book_data: OrderBookStorageStruct, side: Side, start_tick: int,
                         n_ticks: int) -> Tuple[List[int], List[Decimal]]:
        """
        Get next N ticks with their sizes

        Args:
            side: Side to get ticks for
            start_tick: Starting tick
            n_ticks: Number of ticks to get

        Returns:
            Tuple of (ticks, sizes)
        """
        if n_ticks == 0:
            return ([], [])

        book = self._get_book(book_data, side)
        ticks = []
        sizes = []

        # Determine starting tick
        if start_tick == side.tick_to_get_first_avail():
            start_tick, found = book.tick_bitmap.find_highest_tick() if side.sweep_tick_top_down() else book.tick_bitmap.find_lowest_tick()
            if not found:
                return ([], [])
            ticks.append(start_tick)
            n_found = 1
        else:
            n_found = 0

        # Find next ticks
        cur_tick = start_tick
        while n_found < n_ticks:
            next_tick, found = book.tick_bitmap.find_less_tick(
                cur_tick) if side.sweep_tick_top_down() else book.tick_bitmap.find_greater_tick(cur_tick)

            if not found:
                break

            ticks.append(next_tick)
            n_found += 1
            cur_tick = next_tick

        # Get sizes for each tick
        for tick in ticks:
            tick_obj = book.ticks.get(tick)
            if tick_obj:
                sizes.append(tick_obj.get_tick_sum())
            else:
                sizes.append(0)

        return ticks, sizes
