from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, List, Tuple
from enum import IntEnum


@dataclass
class TickMatchResult:
    partial_size: Decimal
    begin_fully_filled_order_index: int
    end_fully_filled_order_index: int


class FenwickNodeMath:
    """Fenwick tree utilities for order management."""
    SIZE_LEVEL = 4
    HIGHEST_LEVEL = 9
    MAX_COVER_LENGTH = (1 << HIGHEST_LEVEL) << HIGHEST_LEVEL  # 2^18

    @staticmethod
    def cover_length(node_id: int) -> int:
        """Calculate cover length for a node ID."""
        res = FenwickNodeMath.raw_cover_length(node_id)
        if res > FenwickNodeMath.MAX_COVER_LENGTH:
            res = FenwickNodeMath.MAX_COVER_LENGTH
        return res

    @staticmethod
    def raw_cover_length(node_id: int) -> int:
        """Raw cover length calculation."""
        res = (node_id + 1) & ~node_id

        # Check if power of 4 (even bits set)
        even_bit_mask = 0x55555555555555555555555555555555
        is_power_of_4 = (res & even_bit_mask) > 0
        if not is_power_of_4:
            res >>= 1
        return res

    @staticmethod
    def is_leaf(node_id: int) -> bool:
        """Check if node is a leaf (not an internal node)."""
        return (node_id & 3) != 3

    @staticmethod
    def parent(node_id: int) -> int:
        """Get parent node ID."""
        cover_length = FenwickNodeMath.raw_cover_length(node_id)
        if cover_length < FenwickNodeMath.MAX_COVER_LENGTH:
            node_id = node_id | (cover_length * 3)
        return node_id

    @staticmethod
    def ancestor_covering(node_id: int, cover_length: int) -> int:
        """Get ancestor node covering the given length."""
        return node_id | (cover_length - 1)


class OrderStatus(IntEnum):
    NOT_EXIST = 0
    OPEN = 1
    PENDING_SETTLE = 2
    PURGED = 3


class FTag:
    """FTag represents a funding tag for settlements."""

    def __init__(self, value: int = 0):
        self.value = value & 0xFFFFFFFF  # uint32

    @classmethod
    def ZERO(cls):
        return cls(0)

    def is_purge(self) -> bool:
        return self.value == 0xFFFFFFFF

    def __int__(self):
        return self.value

    def __repr__(self):
        return f"FTag({self.value})"


class MatchEvent:
    """Records a fill event at a specific headIndex with a specific fTag."""

    def __init__(self, head_index: int = 0, f_tag: FTag = FTag.ZERO()):
        self.head_index = head_index  # uint40
        self.f_tag = f_tag  # FTag (uint32)

    @classmethod
    def from_values(cls, head_index: int, f_tag_val: int):
        return cls(head_index, FTag(f_tag_val))

    def __repr__(self):
        return f"MatchEvent(head={self.head_index}, fTag={self.f_tag})"


class TickInfo:
    """Stores tick metadata: tickSum, headIndex, tailIndex, tickNonce, activeTickNonce."""

    def __init__(self):
        self.tick_sum: int = 0  # Total size of all orders in tick
        self.head_index: int = 0  # Index of oldest active order
        self.tail_index: int = 0  # Index after newest order
        self.tick_nonce: int = 0  # Incremented on each fill
        self.active_tick_nonce: int = 0  # Current active nonce for new orders

    def read(self) -> Tuple[int, int, int, int, int]:
        return (self.tick_sum, self.head_index, self.tail_index,
                self.tick_nonce, self.active_tick_nonce)

    def write(self, tick_sum: int, head_index: int, tail_index: int,
              tick_nonce: int, active_tick_nonce: int):
        self.tick_sum = tick_sum
        self.head_index = head_index
        self.tail_index = tail_index
        self.tick_nonce = tick_nonce
        self.active_tick_nonce = active_tick_nonce


class TickNonceData:
    """Stores data for each tickNonce: lastEvent, firstEventId, lastEventId, nextActiveNonce."""

    def __init__(self):
        self.last_event: Optional[MatchEvent] = None
        self.first_event_id: int = 0
        self.last_event_id: int = 0
        self.next_active_nonce: int = 0xFFFFFFFFFFFFFFFF  # uint40 max

    @classmethod
    def from_event(cls, last_event: MatchEvent, first_event_id: int,
                   last_event_id: int, next_active_nonce: int):
        data = cls()
        data.last_event = last_event
        data.first_event_id = first_event_id
        data.last_event_id = last_event_id
        data.next_active_nonce = next_active_nonce
        return data

    @classmethod
    def ZERO(cls):
        return cls()

    def is_zero(self) -> bool:
        return (self.last_event is None and
                self.first_event_id == 0 and
                self.last_event_id == 0)

    def replace_next_active_nonce(self, new_nonce: int) -> 'TickNonceData':
        self.next_active_nonce = new_nonce
        return self

    def __repr__(self):
        return (f"TickNonceData(lastEvent={self.last_event}, "
                f"firstEventId={self.first_event_id}, "
                f"lastEventId={self.last_event_id}, "
                f"nextActiveNonce={self.next_active_nonce})")


class NodeData:
    """Stores order data: orderSize, makerNonce, tickNonce, refTickNonce."""

    def __init__(self):
        self.order_size: int = 0  # uint128
        self.maker_nonce: int = 0  # uint40
        self.tick_nonce: int = 0  # uint40
        self.ref_tick_nonce: int = 0  # uint40

    @classmethod
    def from_values(cls, order_size: int, maker_nonce: int,
                    tick_nonce: int, ref_tick_nonce: int):
        data = cls()
        data.order_size = order_size
        data.maker_nonce = maker_nonce
        data.tick_nonce = tick_nonce
        data.ref_tick_nonce = ref_tick_nonce
        return data

    def order_size_value(self) -> int:
        return self.order_size

    def maker_nonce_value(self) -> int:
        return self.maker_nonce

    def tick_nonce_value(self) -> int:
        return self.tick_nonce

    def ref_tick_nonce_value(self) -> int:
        return self.ref_tick_nonce

    def dec_order_size(self, amount: int) -> 'NodeData':
        self.order_size -= amount
        return self

    @classmethod
    def ZERO(cls):
        return cls()

    def __repr__(self):
        return (f"NodeData(size={self.order_size}, makerNonce={self.maker_nonce}, "
                f"tickNonce={self.tick_nonce}, refTickNonce={self.ref_tick_nonce})")


class Tick:
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
    def match_all_fill_result(self, f_tag: FTag, result: TickMatchResult):
        """
        Called when the entire tick is filled.
        """
        (tick_sum, head_index, tail_index, tick_nonce, active_tick_nonce) = self.info.read()

        # Push new match event
        active_tick_nonce = self._push_new_match_event(
            tick_nonce, active_tick_nonce, head_index, f_tag
        )

        result.partial_size = 0
        result.partial_maker_nonce = 0
        result.begin_fully_filled_order_index = head_index
        result.end_fully_filled_order_index = tail_index

        # Increment tick nonce and reset tick
        tick_nonce += 1
        self.info.write(0, tail_index, tail_index, tick_nonce, active_tick_nonce)

    # ==================== matchPartialFillResult ====================
    def match_partial_fill_result(self, to_match_size: int, f_tag: FTag, result: TickMatchResult):
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

        result.partial_size = partial_size
        result.partial_maker_nonce = partial_maker_nonce
        result.begin_fully_filled_order_index = head_index
        result.end_fully_filled_order_index = new_head_index

        # Update tick
        new_tick_sum = tick_sum - to_match_size
        self.info.write(new_tick_sum, new_head_index, tail_index, tick_nonce, active_tick_nonce)

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

    def get_settle_size(self, order_index: int) -> int:
        return self.nodes[order_index].order_size

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
