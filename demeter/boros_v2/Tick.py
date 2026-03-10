from typing import Dict, List, Optional, Tuple
from ._typing import TickInfo, NodeData, MatchEvent, TickNonceData, FenwickNodeMath, TickMatchResult, FTag, OrderStatus


class Tick:
    """
    Main Tick class managing orders in a price tick.
    Uses a Fenwick tree-like structure for efficient order management.
    """

    def __init__(self):
        self.info = TickInfo()
        self.nodes: Dict[int, NodeData] = {}  # nodeId -> NodeData
        self.subtree_sum: Dict[int, int] = {}  # nodeId -> subtree sum
        self.match_events: List[MatchEvent] = []
        self.tick_nonce_data: Dict[int, TickNonceData] = {}

    # ==================== insertOrder ====================
    def insert_order(self, size: int, maker_nonce: int) -> Tuple[int, int]:
        """
        Insert a new order into the tick.
        Returns: (orderIndex, oldTickSum)
        """
        (tick_sum, head_index, tail_index, tick_nonce, active_tick_nonce) = self.info.read()

        # orderIndex = tailIndex (insert at the end)
        order_index = tail_index
        old_tick_sum = tick_sum

        # Calculate subtree sum for the new node
        # This walks up the tree to accumulate subtree sums
        node_id = order_index
        subtree_sum = 0

        while node_id >= 1 and node_id - 1 >= head_index:
            cover_len = FenwickNodeMath.cover_length(node_id)
            if node_id - cover_len < head_index:
                break
            parent_id = node_id - cover_len
            if parent_id in self.subtree_sum:
                subtree_sum += self.subtree_sum[parent_id]
            node_id = parent_id

        # Update tick sum and tail index
        tick_sum += size
        tail_index += 1

        # Create node data
        self.nodes[order_index] = NodeData.from_values(
            size, maker_nonce, tick_nonce, active_tick_nonce
        )

        # Store subtree sum if non-zero
        if subtree_sum > 0:
            self.subtree_sum[order_index] = subtree_sum

        # Update tick info
        self.info.write(tick_sum, head_index, tail_index, tick_nonce, active_tick_nonce)

        return (order_index, old_tick_sum)

    # ==================== tryRemove ====================
    def try_remove(self, order_index: int, is_strict: bool = False) -> Tuple[int, int]:
        """
        Try to remove an order from the tick.
        Returns: (removedSize, newTickSum)
        """
        (tick_sum, head_index, tail_index, tick_nonce, active_tick_nonce) = self.info.read()

        if order_index >= tail_index:
            raise ValueError("MarketOrderNotFound")

        if order_index not in self.nodes:
            removed_size = 0
            if is_strict:
                raise ValueError("MarketOrderNotFound")
            return (0, tick_sum)

        node = self.nodes[order_index]
        removed_size = node.order_size_value()

        if is_strict:
            if removed_size == 0:
                raise ValueError("MarketOrderCancelled")
            if order_index < head_index:
                raise ValueError("MarketOrderFilled")
        elif removed_size == 0 or order_index < head_index:
            return (0, tick_sum)

        # Update subtree sums up the tree
        child = order_index
        parent = FenwickNodeMath.parent(child)

        while parent < tail_index and parent != child:
            if parent in self.subtree_sum:
                self.subtree_sum[parent] -= removed_size
            child = parent
            parent = FenwickNodeMath.parent(child)

        # Update tick sum
        tick_sum -= removed_size

        # Remove node
        self.nodes[order_index] = NodeData.ZERO()

        # Update tick info
        self.info.write(tick_sum, head_index, tail_index, tick_nonce, active_tick_nonce)

        return (removed_size, tick_sum)

    # ==================== _pushNewMatchEvent ====================
    def _push_new_match_event(self, cur_tick_nonce: int, active_tick_nonce: int,
                              head_index: int, f_tag: FTag) -> int:
        """
        Push a new match event to record a fill.
        Returns: new activeTickNonce
        """
        # Get reference data from activeTickNonce
        ref_data = self.tick_nonce_data.get(active_tick_nonce, TickNonceData.ZERO())
        ref_event = ref_data.last_event if ref_data.last_event else None

        # Check if same fTag - if so, don't record new event
        if ref_event and int(ref_event.f_tag) == int(f_tag):
            return active_tick_nonce

        # Create new event
        new_event_id = len(self.match_events)
        new_event = MatchEvent(head_index, f_tag)
        self.match_events.append(new_event)

        # Get current data for curTickNonce
        cur_data = self.tick_nonce_data.get(cur_tick_nonce, TickNonceData.ZERO())

        if cur_data.is_zero():
            first_event_id = ref_data.last_event_id if ref_event else 0
        else:
            first_event_id = cur_data.first_event_id

        last_event_id = new_event_id

        # Store/update tick nonce data
        self.tick_nonce_data[cur_tick_nonce] = TickNonceData.from_event(
            new_event, first_event_id, last_event_id, 0xFFFFFFFFFFFFFFFF
        )

        # Update nextActiveNonce if nonces differ
        if cur_tick_nonce != active_tick_nonce:
            # Update old active tick nonce to point to new one
            if active_tick_nonce in self.tick_nonce_data:
                self.tick_nonce_data[active_tick_nonce] = \
                    self.tick_nonce_data[active_tick_nonce].replace_next_active_nonce(cur_tick_nonce)

        return cur_tick_nonce

    # ==================== matchAllFillResult ====================
    def match_all_fill_result(self, f_tag: FTag) -> TickMatchResult:
        """
        Called when the entire tick is filled.
        """
        (tick_sum, head_index, tail_index, tick_nonce, active_tick_nonce) = self.info.read()

        # Push new match event
        active_tick_nonce = self._push_new_match_event(
            tick_nonce, active_tick_nonce, head_index, f_tag
        )

        result = TickMatchResult()
        result.partial_size = 0
        result.partial_maker_nonce = 0
        result.begin_fully_filled_order_index = head_index
        result.end_fully_filled_order_index = tail_index

        # Increment tick nonce and reset tick
        tick_nonce += 1
        self.info.write(0, tail_index, tail_index, tick_nonce, active_tick_nonce)

        return result

    # ==================== matchPartialFillResult ====================
    def match_partial_fill_result(self, to_match_size: int, f_tag: FTag) -> TickMatchResult:
        """
        Called when only part of the tick is filled.
        """
        (tick_sum, head_index, tail_index, tick_nonce, active_tick_nonce) = self.info.read()

        # Push new match event
        active_tick_nonce = self._push_new_match_event(
            tick_nonce, active_tick_nonce, head_index, f_tag
        )

        # Find new head index and handle partial fill
        new_head_index, partial_size, partial_maker_nonce = self._match_partial_inner(
            head_index, tail_index, to_match_size
        )

        result = TickMatchResult()
        result.partial_size = partial_size
        result.partial_maker_nonce = partial_maker_nonce
        result.begin_fully_filled_order_index = head_index
        result.end_fully_filled_order_index = new_head_index

        # Update tick
        new_tick_sum = tick_sum - to_match_size
        self.info.write(new_tick_sum, new_head_index, tail_index, tick_nonce, active_tick_nonce)

        return result

    # ==================== _matchPartialInner ====================
    def _match_partial_inner(self, head_index: int, tail_index: int,
                             remaining: int) -> Tuple[int, int, int]:
        """
        Internal function to handle partial fill logic.
        Returns: (newHeadIndex, partialSize, partialMakerNonce)
        """
        cover_lengths = []
        cl = FenwickNodeMath.MAX_COVER_LENGTH
        while cl > 0:
            cover_lengths.append(cl)
            cl //= FenwickNodeMath.SIZE_LEVEL

        for cover_len in cover_lengths:
            # Find first node at this cover length
            start_node = head_index | (cover_len - 1)

            for node_id in range(start_node, tail_index):
                node_cl = FenwickNodeMath.cover_length(node_id)
                if node_cl != cover_len:
                    continue

                # Calculate sum for this node
                node_sum = 0
                subtree_sum = 0
                if node_id in self.nodes:
                    node_sum = self.nodes[node_id].order_size_value()
                if node_id in self.subtree_sum and not FenwickNodeMath.is_leaf(node_id):
                    subtree_sum = self.subtree_sum[node_id]
                    node_sum += subtree_sum

                if node_sum <= remaining:
                    remaining -= node_sum
                    head_index = node_id + 1
                    continue

                # This node has the partial fill
                if remaining < subtree_sum:
                    # Partial fill within subtree
                    if node_id in self.subtree_sum:
                        self.subtree_sum[node_id] = subtree_sum - remaining
                    return (head_index, 0, 0)

                # Partial fill at this node
                partial_size = remaining - subtree_sum
                if node_id in self.nodes:
                    old_node = self.nodes[node_id]
                    partial_maker_nonce = old_node.maker_nonce_value()

                    # Update node with reduced size
                    if subtree_sum > 0 and node_id in self.subtree_sum:
                        self.subtree_sum[node_id] = 0
                    self.nodes[node_id] = old_node.dec_order_size(partial_size)

                    return (node_id, partial_size, partial_maker_nonce)

        return (head_index, 0, 0)

    # ==================== getSettleSizeAndFTag ====================
    def get_settle_size_and_f_tag(self, order_index: int) -> Tuple[int, FTag]:
        """
        Get the settlement size and fTag for an order.
        Returns: (settledSize, fTag)
        """
        if order_index not in self.nodes:
            return (0, FTag.ZERO())

        node = self.nodes[order_index]
        size = node.order_size_value()

        if size == 0:
            return (0, FTag.ZERO())

        f_tag = self._get_f_tag(order_index, node.tick_nonce_value(),
                                node.ref_tick_nonce_value())
        return (size, f_tag)

    # ==================== _getFTag ====================
    def _get_f_tag(self, order_id: int, tick_nonce: int,
                   ref_tick_nonce: int) -> FTag:
        """
        Get the fTag for an order based on its nonce and refNonce.
        """
        # Case 1: refTickNonce != tickNonce
        if ref_tick_nonce != tick_nonce:
            ref_data = self.tick_nonce_data.get(ref_tick_nonce)
            if ref_data and ref_data.last_event:
                # Check if current tickNonce is before nextActiveNonce
                if ref_data.next_active_nonce > tick_nonce:
                    return ref_data.last_event.f_tag

        # Case 2: Within current nonce range
        data = self.tick_nonce_data.get(tick_nonce)
        if data and data.last_event:
            if data.last_event.head_index <= order_id:
                return data.last_event.f_tag

        # Case 3: Binary search through historical events
        if data and data.first_event_id < len(self.match_events):
            start_idx = data.first_event_id
            end_idx = data.last_event_id - 1

            result_f_tag = FTag.ZERO()
            while start_idx <= end_idx:
                mid = (start_idx + end_idx) // 2
                if mid >= len(self.match_events):
                    break

                event = self.match_events[mid]
                if order_id < event.head_index:
                    end_idx = mid - 1
                else:
                    result_f_tag = event.f_tag
                    start_idx = mid + 1

            return result_f_tag

        return FTag.ZERO()

    # ==================== Utility Methods ====================
    def get_tick_sum(self) -> int:
        return self.info.tick_sum

    def can_settle_skip_size_check(self, order_index: int) -> bool:
        """Check if order can be settled (orderIndex < headIndex)."""
        return order_index < self.info.head_index

    def get_order_status_and_size(self, order_index: int) -> Tuple[OrderStatus, int]:
        """Get the status and size of an order."""
        if order_index not in self.nodes:
            return (OrderStatus.NOT_EXIST, 0)

        node = self.nodes[order_index]
        size = node.order_size_value()

        if size == 0:
            return (OrderStatus.NOT_EXIST, 0)

        if order_index >= self.info.head_index:
            return (OrderStatus.OPEN, size)

        # Order is settled
        f_tag = self._get_f_tag(order_index, node.tick_nonce_value(),
                                node.ref_tick_nonce_value())
        if f_tag.is_purge():
            return (OrderStatus.PURGED, size)
        else:
            return (OrderStatus.PENDING_SETTLE, size)

    def __repr__(self):
        return (f"Tick(tickSum={self.info.tick_sum}, "
                f"head={self.info.head_index}, tail={self.info.tail_index}, "
                f"nonce={self.info.tick_nonce}, activeNonce={self.info.active_tick_nonce}, "
                f"nodes={len(self.nodes)})")