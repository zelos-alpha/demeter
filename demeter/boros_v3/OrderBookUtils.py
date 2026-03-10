# class OrderBookUtils:
#     def _get_book(self, side: Side) -> OrderBook:
#         pass  # todo
#
#     def _book_can_settle_skip_size_check(self, id: OrderId) -> bool:
#         side, tick_index, order_index = id.unpack()
#         tick = self._get_book(side).ticks[tick_index]
#         return tick.can_settle_skip_size_check(order_index)  # todo
#
#     def _book_get_settle_info(self, id: OrderId, tick_step: int, f_tag: FTag) -> SweptF:
#         side, tick_index, order_index = id.unpack()
#         tick = self._get_book(side).ticks[tick_index]
#         settled_size = 0
#         if f_tag.is_zero():
#             settled_size, f_tag = tick.get_settle_size_and_f_tag(order_index)
#         else:
#             settled_size = tick.get_settle_size(order_index)
#         return SweptF.assign(f_tag, FillLib.from3(side, settled_size, TickMath.getRateAtTick(tick_index, tick_step)))
#
#     def _bookRemove(self, ids: list[OrderId], isStrict: bool, isForced: bool) -> list[int]:
#         len_ = len(ids)
#         if len_ == 0: return []
#         removedCnt = 0
#         removedSizes = []
#         for i in range(0, len_):
#             side, tickIndex, orderIndex = OrderIdLib.unpack(ids[i])
#             order_book = self._get_book(side)
#             tick = order_book.ticks[tickIndex]
#             removedSize, newTickSum = TickLib.tryRemove(tick, orderIndex, isStrict)  # todo
#             if removedSize > 0:
#                 if newTickSum == 0:
#                     TickBitmapLib.reset(order_book.tickBitmap, tickIndex)
#                 ids[removedCnt] = ids[i]
#                 removedSizes[removedCnt] = removedSize
#                 removedCnt += 1
#
#         del ids[-(len_ - removedCnt):]  # 删除removedCnt后面数据
#         len_removedSizes = len(removedSizes)
#         del removedSizes[-(len_removedSizes - removedCnt):]
#
#     def _book_match(self, tick_step: int, latest_ftag: FTag, orders: LongShort) -> (Trade, Fill, MarketAcc, int, int):
#         match_aux = MatchAux(
#             side=orders.side.opposite(),
#             sizes=orders.sizes,
#             limitTicks=orders.limitTicks,
#             tickStep=tick_step,
#             latestFTag=latest_ftag
#         )
#         if TimeInForceLib.shouldSkipMatchableOrders(orders.tif):
#             self._removeMatchableOrders(match_aux)
#             return TradeLib.ZERO, FillLib.ZERO, AccountLib.ZERO_MARKET_ACC, 0, 0
#
#         order_book = self._get_book(match_aux.side)
#         result = TickMatchResult()
#
#
#         pass  # todo
#
#     def _removeMatchableOrders(self, match_aux: MatchAux):
#         order_book = self._get_book(side)
#         bestTick, found = TickIterationLib.begin(order_book.tickBitmap, match_aux.side)  # todo
#         if not found: return
#         for i in range(0, len(match_aux.sizes)):
#             if SideLib.canMatch(match_aux.side, match_aux.limitTicks[i], bestTick):
#                 match_aux.sizes[i] = 0
#         self.__removeZeroSizes(match_aux.sizes, match_aux.limitTicks)
#
#     def __removeZeroSizes(self, sizes: list[int], limitTicks: list[int]):
#         keepCnt = 0
#         lenTicks = len(limitTicks)
#         lenSizes = len(sizes)
#         for i in range(len(sizes)):
#             if sizes[i] == 0: continue
#             sizes[keepCnt], limitTicks[keepCnt] = sizes[i], limitTicks[i]
#             keepCnt += 1
#         del sizes[-(lenSizes - keepCnt):]
#         del limitTicks[-(lenTicks - keepCnt):]
#

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from .TickBitmap import TickBitmap
from .Tick import Tick, TickMatchResult
from .Order import Side, OrderId, OrderStatus
from .MarketTypes import LongShort, SweptF, Trade, Fill, FTag
from .TickMath import TickMath


@dataclass
class OrderBook:
    """Order Book for one side (LONG or SHORT)"""
    tick_bitmap: TickBitmap = field(default_factory=TickBitmap)
    ticks: Dict[int, Tick] = field(default_factory=dict)


class OrderBookUtils:
    def __init__(self):
        """Initialize order book storage"""
        self.book_long: OrderBook = OrderBook()
        self.book_short: OrderBook = OrderBook()
        self.maker_to_nonce: Dict[int, int] = {}
        self.nonce_to_maker: Dict[int, int] = {}
        self.count_maker: int = 0

    def get_book(self, side: Side) -> OrderBook:
        """Get the order book for a given side"""
        return self.book_long if side == Side.LONG else self.book_short

    def get_or_create_maker_nonce(self, maker: int) -> int:
        """Get or create a unique nonce for a maker"""
        maker_nonce = self.maker_to_nonce.get(maker, 0)
        if maker_nonce == 0:
            maker_nonce = self.count_maker + 1
            self.count_maker = maker_nonce
            self.maker_to_nonce[maker] = maker_nonce
            self.nonce_to_maker[maker_nonce] = maker
        return maker_nonce

    def book_add(self, maker: int, orders: LongShort, order_ids: List[OrderId],
                 append_pos: int) -> List[OrderId]:
        """
        Add orders to the order book

        Args:
            maker: Maker address
            orders: Orders to add (sizes and limit ticks)
            order_ids: Order IDs array to populate
            append_pos: Position to start appending

        Returns:
            List of created OrderIds
        """
        book = self.get_book(orders.side)
        maker_nonce = self.get_or_create_maker_nonce(maker)

        for i in range(len(orders.sizes)):
            cur_size = orders.sizes[i]
            tick_index = orders.limit_ticks[i]

            # Get or create tick
            if tick_index not in book.ticks:
                book.ticks[tick_index] = Tick()

            tick = book.ticks[tick_index]

            # Insert order
            order_index, old_tick_sum = Tick.insert_order(tick, cur_size, maker_nonce)

            # Set tick bitmap if this is the first order at this tick
            if old_tick_sum == 0:
                book.tick_bitmap.set(tick_index)

            # Create order ID
            order_ids[append_pos + i] = OrderId.from_(orders.side, tick_index, order_index)

        return order_ids[append_pos:append_pos + len(orders.sizes)]

    def book_remove(self, order_ids: List[OrderId], is_strict: bool,
                    is_forced: bool) -> Tuple[List[OrderId], List[int]]:
        """
        Remove orders from the order book

        Args:
            order_ids: Order IDs to remove
            is_strict: If True, enforce strict checks
            is_forced: If True, orders are being force cancelled

        Returns:
            Tuple of (remaining_order_ids, removed_sizes)
        """
        if len(order_ids) == 0:
            return ([], [])

        removed_sizes = []
        remaining_ids = []

        for order_id in order_ids:
            side, tick_index, order_index = order_id.unpack()

            book = self.get_book(side)
            tick = book.ticks.get(tick_index)

            if tick is None:
                continue

            try:
                removed_size, new_tick_sum = tick.try_remove(order_index, is_strict)

                if removed_size > 0:
                    if new_tick_sum == 0:
                        book.tick_bitmap.reset(tick_index)

                    remaining_ids.append(order_id)
                    removed_sizes.append(removed_size)
            except ValueError:
                # Order not found, cancelled, or filled
                continue

        return remaining_ids, removed_sizes

    def book_can_settle_skip_size_check(self, order_id: OrderId) -> bool:
        """
        Check if an order can settle without size check

        Args:
            order_id: The order to check

        Returns:
            True if order is already settled (can skip size check)
        """
        side, tick_index, order_index = order_id.unpack()
        book = self.get_book(side)
        tick = book.ticks.get(tick_index)

        if tick is None:
            return False

        return tick.can_settle_skip_size_check(order_index)

    def book_get_settle_info(self, order_id: OrderId, tick_step: int, f_tag: int) -> SweptF:
        """
        Get settlement info for an order

        Args:
            order_id: Order to get info for
            tick_step: Tick step for rate calculation
            f_tag: FTag (0 means get from tick)

        Returns:
            SweptF with fill info
        """
        side, tick_index, order_index = order_id.unpack()
        book = self.get_book(side)
        tick = book.ticks.get(tick_index)

        if tick is None:
            return SweptF.zero()

        settled_size = 0
        if f_tag == 0:
            settled_size, f_tag = tick.get_settle_size_and_f_tag(order_index)
        else:
            settled_size = tick.get_settle_size(order_index)

        # Calculate rate at tick
        rate = TickMath.get_rate_at_tick(tick_index, tick_step)

        return SweptF.from3(side, settled_size, rate, f_tag)

    def book_match(self, tick_step: int, latest_f_tag: FTag,
                   orders: LongShort) -> Tuple[Trade, Fill, int, int, int]:
        """
        Match orders in the order book

        This is the main order matching function that matches incoming orders
        against the existing order book.

        Args:
            tick_step: Tick step for rate calculation
            latest_f_tag: Latest funding tag
            orders: Orders to match (sizes and limit ticks)

        Returns:
            Tuple of (total_matched, partial_fill, partial_maker, last_matched_tick, last_matched_rate)
        """
        opposite_side = orders.side.opposite()

        # Check if should skip matchable orders (for SOFT_ALO)
        if orders.tif.should_skip_matchable_orders():
            # Just remove matchable orders without matching
            self._remove_matchable_orders(opposite_side, orders.sizes, orders.limit_ticks)
            return (Trade.zero(), Fill.zero(), 0, 0, 0)

        book = self.get_book(opposite_side)
        result = TickMatchResult()

        total_matched = Trade.zero()
        partial_fill = Fill.zero()
        partial_maker = 0
        last_matched_tick = 0
        last_matched_rate = 0
        cur_order = 0

        while cur_order < len(orders.sizes):
            # Get current best tick
            best_tick, found = book.tick_bitmap.find_highest_tick() if opposite_side.sweep_tick_top_down() else book.tick_bitmap.find_lowest_tick()

            if not found:
                break

            # Find next matchable order
            cur_order = self._next_matchable_order(opposite_side, best_tick,
                                                   orders.limit_ticks, cur_order)
            if cur_order == len(orders.sizes):
                break

            # Process tick matches
            tick = book.ticks.get(best_tick)
            if tick is None:
                break

            tick_sum = tick.get_tick_sum()
            cur_order_size = orders.sizes[cur_order]

            if cur_order_size <= tick_sum:
                # Merge with next order if possible
                next_order = self._next_matchable_order(opposite_side, best_tick,
                                                        orders.limit_ticks, cur_order + 1)
                if next_order < len(orders.sizes):
                    orders.sizes[next_order] += orders.sizes[cur_order]
                    orders.sizes[cur_order] = 0
                    cur_order = next_order
                    continue

            # Process the match
            if tick_sum <= orders.sizes[cur_order]:
                # Full tick match
                matched = tick_sum
                tick.match_all_fill_result(latest_f_tag, result)  # todo
                book.tick_bitmap.reset(best_tick)
            else:
                # Partial tick match
                matched = orders.sizes[cur_order]
                tick.match_partial_fill_result(matched, latest_f_tag, result)

            orders.sizes[cur_order] -= matched
            last_matched_tick = best_tick
            last_matched_rate = TickMath.get_rate_at_tick(best_tick, tick_step)

            total_matched = total_matched + Trade.from3(opposite_side, matched, last_matched_rate)

            # Handle partial fill
            if result.partial_size > 0:
                partial_maker = self.nonce_to_maker.get(result.partial_maker_nonce, 0)
                partial_fill = Fill.from3(opposite_side, result.partial_size, last_matched_rate)
                break

            if orders.sizes[cur_order] == 0:
                break

        # Remove zero sizes
        self._remove_zero_sizes(orders.sizes, orders.limit_ticks)

        return (total_matched.opposite(), partial_fill, partial_maker,
                last_matched_tick, last_matched_rate)

    def _remove_matchable_orders(self, side: Side, sizes: List[int],
                                 limit_ticks: List[int]):
        """Remove matchable orders (for SOFT_ALO)"""
        book = self.get_book(side)
        best_tick, found = book.tick_bitmap.find_highest_tick() if side.sweep_tick_top_down() else book.tick_bitmap.find_lowest_tick()

        if not found:
            return

        for i in range(len(sizes)):
            if side.can_match(limit_ticks[i], best_tick):
                sizes[i] = 0

        self._remove_zero_sizes(sizes, limit_ticks)

    def _next_matchable_order(self, side: Side, cur_tick: int,
                              limit_ticks: List[int], cur_order: int) -> int:
        """Find the next order that can match"""
        n = len(limit_ticks)
        while cur_order < n and not side.can_match(limit_ticks[cur_order], cur_tick):
            cur_order += 1
        return cur_order

    def _remove_zero_sizes(self, sizes: List[int], limit_ticks: List[int]):
        """Remove zero sizes from arrays"""
        keep_cnt = 0
        for i in range(len(sizes)):
            if sizes[i] == 0:
                continue
            sizes[keep_cnt] = sizes[i]
            limit_ticks[keep_cnt] = limit_ticks[i]
            keep_cnt += 1

        del sizes[keep_cnt:]
        del limit_ticks[keep_cnt:]

    def book_purge_oob(self, tick_step: int, bound_rate: int, purge_tag: int,
                       side: Side, max_n_ticks_to_purge: int) -> int:
        """
        Purge out-of-bounds orders

        Args:
            tick_step: Tick step for rate calculation
            bound_rate: Rate boundary
            purge_tag: Tag to mark purged orders
            side: Side to purge
            max_n_ticks_to_purge: Maximum number of ticks to purge

        Returns:
            Number of ticks purged
        """
        book = self.get_book(side)
        result = TickMatchResult()
        n_ticks_purged = 0

        while n_ticks_purged < max_n_ticks_to_purge:
            best_tick, found = book.tick_bitmap.find_highest_tick() if side.sweep_tick_top_down() else book.tick_bitmap.find_lowest_tick()

            if not found:
                break

            tick_rate = TickMath.get_rate_at_tick(best_tick, tick_step)
            if side.check_rate_in_bound(tick_rate, bound_rate):
                break

            tick = book.ticks.get(best_tick)
            if tick is None:
                break

            tick.match_all_fill_result(purge_tag, result)
            book.tick_bitmap.reset(best_tick)

            n_ticks_purged += 1

        return n_ticks_purged

    def get_next_n_ticks(self, side: Side, start_tick: int,
                         n_ticks: int) -> Tuple[List[int], List[int]]:
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

        book = self.get_book(side)

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

        return (ticks, sizes)

    def get_order_status(self, order_id: OrderId) -> OrderStatus:
        """Get the status of an order"""
        side, tick_index, order_index = order_id.unpack()
        book = self.get_book(side)
        tick = book.ticks.get(tick_index)

        if tick is None:
            return OrderStatus.NOT_EXIST

        status, _ = tick.get_order_status_and_size(order_index)
        return status