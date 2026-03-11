from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from .MarketTypes import LongShort, Trade, MarketCtx, MarketMem, UserMem, CancelData
from .Order import TimeInForce, Side, OrderId, OrderIdArrayLib
from .OrderBookUtils import OrderBookUtils

class CoreOrderUtils(OrderBookUtils):
    """
        Core Order Utilities

        Core functions for adding and removing orders from the order book.
        """

    def __init__(self):
        """Initialize"""
        self._is_order_remove: Dict[int, bool] = {}  # Transient mapping
        self._book = {}  # Mock order book storage
        self._ctx = MarketCtx()
        super().__init__()

    def _should_place_on_book(self, orders: LongShort, prev_matched: Trade) -> bool:
        """
        Determine if orders should be placed on the book based on TimeInForce

        Args:
            orders: The orders to check
            prev_matched: Previous matched trade

        Returns:
            True if orders should be placed on book
        """
        tif = orders.tif
        has_matched_all = orders.is_empty()

        if tif == TimeInForce.GTC:
            # Good Till Cancel - place if not fully matched
            return not has_matched_all

        elif tif == TimeInForce.IOC:
            # Immediate Or Cancel - never place on book
            return False

        elif tif == TimeInForce.FOK:
            # Fill Or Kill - must be fully matched, never place on book
            if has_matched_all:
                return False
            else:
                raise ValueError("MarketOrderFOKNotFilled: Order not fully filled")

        elif tif == TimeInForce.ALO:
            # Aggressive Limit Order - place if not fully matched and prev not filled
            if not prev_matched.is_zero():
                raise ValueError("MarketOrderALOFilled: ALO order already filled")
            return not has_matched_all

        elif tif == TimeInForce.SOFT_ALO:
            # Soft ALO - place if not fully matched
            return not has_matched_all

        else:
            raise ValueError("Unknown TimeInForce")

    def _core_add(
            self,
            market: MarketMem,
            user: UserMem,
            orders: LongShort,
            prev_matched: Trade
    ) -> List[OrderId]:
        """
        Add orders to the order book

        Args:
            market: Market state
            user: User state
            orders: Orders to add
            prev_matched: Previous matched trade

        Returns:
            List of added order IDs
        """
        # Check if should place on book
        if not self._should_place_on_book(orders, prev_matched):
            return []

        # Check max orders limit
        total_orders = len(user.long_ids) + len(user.short_ids) + len(orders.sizes)
        if total_orders > self._ctx.max_open_orders:
            raise ValueError("MarketMaxOrdersExceeded: Too many open orders")

        # Extend appropriate array and add orders
        if orders.side == Side.LONG:
            user.long_ids = OrderIdArrayLib.extend(user.long_ids, len(orders.sizes))
            ids = user.long_ids
        else:
            user.short_ids = OrderIdArrayLib.extend(user.short_ids, len(orders.sizes))
            ids = user.short_ids

        # Get pre-length before adding
        pre_len = len(ids) - len(orders.sizes)

        # Add orders to book (mock implementation)
        for i in range(len(orders.sizes)):
            order_id = OrderId.from_(orders.side, orders.limit_ticks[i], pre_len + i)
            ids[pre_len + i] = order_id

        # Update PM data on add
        self._update_pm_on_add(user, market, orders)

        # Update best same side
        OrderIdArrayLib.update_best_same_side(ids, pre_len)

        return ids[pre_len:]

    def _update_pm_on_add(self, user: UserMem, market: MarketMem, orders: LongShort):
        """Update PM data when adding orders"""
        size_added = 0
        pm_added = 0

        for i in range(len(orders.sizes)):
            size_added += orders.sizes[i]
            # Mock PM calculation - in real implementation would use _calcPMFromTick
            pm_added += orders.sizes[i] * 1000  # Simplified

        user.pm_data.add(orders.side, size_added, pm_added)

    def _core_remove_aft(
            self,
            market: MarketMem,
            user: UserMem,
            cancel: CancelData,
            is_forced: bool
    ) -> List[OrderId]:
        """
        Remove orders after trading

        Args:
            market: Market state
            user: User state
            cancel: Cancel data
            is_forced: Whether this is a forced removal

        Returns:
            List of removed order IDs
        """
        if cancel.is_all:
            return self._core_remove_all_aft(market, user, is_forced)

        # Remove from book
        removed_ids, removed_sizes = self._book_remove(cancel.ids, cancel.is_strict, is_forced)

        remove_cnt = len(removed_ids)
        if remove_cnt == 0:
            return removed_ids

        # Mark removed orders in transient mapping
        for order_id in removed_ids:
            self._is_order_remove[order_id.value] = True

        # Process long IDs
        remove_cnt = self._process_order_removal(user.long_ids, remove_cnt)

        # Process short IDs
        remove_cnt = self._process_order_removal(user.short_ids, remove_cnt)

        if remove_cnt != 0:
            raise ValueError("MarketOrderNotFound: Order not found")

        # Update PM data on remove
        self._update_pm_on_remove(user, market, removed_ids, removed_sizes)

        return removed_ids

    def _process_order_removal(self, ids: List[OrderId], remove_cnt: int) -> int:
        """Process order removal from an ID array"""
        length = len(ids)
        i = 0

        while i < length and remove_cnt > 0:
            cur_id = ids[i]

            if not self._is_order_remove.get(cur_id.value, False):
                i += 1
                continue

            # Remove this order
            remove_cnt -= 1
            self._is_order_remove[cur_id.value] = False

            # Swap with last element
            ids[i] = ids[length - 1]
            length -= 1

        # Truncate array
        OrderIdArrayLib.set_shorter_length(ids, length)

        # Update best same side
        OrderIdArrayLib.update_best_same_side(ids, 0)

        return remove_cnt

    def _core_remove_all_aft(
            self,
            market: MarketMem,
            user: UserMem,
            is_forced: bool
    ) -> List[OrderId]:
        """
        Remove all orders

        Args:
            market: Market state
            user: User state
            is_forced: Whether this is a forced removal

        Returns:
            List of all removed order IDs
        """
        removed_ids = []

        # Remove LONG orders
        if len(user.long_ids) > 0:
            removed_sizes = self._book_remove(user.long_ids, False, is_forced)
            self._update_pm_on_remove(user, market, user.long_ids, removed_sizes)
            removed_ids.extend(user.long_ids)

        # Remove SHORT orders
        if len(user.short_ids) > 0:
            removed_sizes = self._book_remove(user.short_ids, False, is_forced)
            self._update_pm_on_remove(user, market, user.short_ids, removed_sizes)
            removed_ids.extend(user.short_ids)

        # Clear arrays
        user.long_ids = []
        user.short_ids = []

        return removed_ids

    def _book_remove(
            self,
            ids: List[OrderId],
            is_strict: bool,
            is_forced: bool
    ) -> Tuple[List[OrderId], List[int]]:
        """
        Remove orders from the book

        Args:
            ids: Order IDs to remove
            is_strict: Whether to use strict mode
            is_forced: Whether this is forced

        Returns:
            Tuple of (removed_ids, removed_sizes)
        """
        # Mock implementation - in real code would interact with OrderBookUtils
        removed_ids = []
        removed_sizes = []

        for order_id in ids:
            if order_id.is_zero():
                continue
            # Mock: assume all orders exist and have size 100
            removed_ids.append(order_id)
            removed_sizes.append(100)

        return removed_ids, removed_sizes

    def _update_pm_on_remove(
            self,
            user: UserMem,
            market: MarketMem,
            ids: List[OrderId],
            sizes: List[int]
    ):
        """Update PM data when removing orders"""
        for i in range(len(ids)):
            side, tick_index, _ = ids[i].unpack()
            # Mock PM calculation
            pm = sizes[i] * 1000
            user.pm_data.sub(side, sizes[i], pm)