"""
Test cases for Tick.py module.
"""
import unittest
from decimal import Decimal
from demeter.boros_v4.Tick import (
    FenwickNodeMath,
    OrderStatus,
    FTag,
    MatchEvent,
    TickInfo,
    TickNonceData,
    NodeData,
    Tick,
    TickMatchResult,
)


class TestFenwickNodeMath(unittest.TestCase):
    """Test cases for FenwickNodeMath class."""

    def test_cover_length_basic(self):
        """Test basic cover length calculation."""
        # Node 0 should have cover length 1
        self.assertEqual(FenwickNodeMath.cover_length(0), 1)

    def test_cover_length_node_1(self):
        """Test cover length for node 1."""
        # Node 1 has cover length 1 (after raw calculation is halved because not power of 4)
        self.assertEqual(FenwickNodeMath.cover_length(1), 1)

    def test_cover_length_node_3(self):
        """Test cover length for node 3."""
        # Node 3 should have cover length 4
        self.assertEqual(FenwickNodeMath.cover_length(3), 4)

    def test_cover_length_max(self):
        """Test cover length doesn't exceed MAX_COVER_LENGTH."""
        # Test with a large node_id
        result = FenwickNodeMath.cover_length(1000)
        self.assertLessEqual(result, FenwickNodeMath.MAX_COVER_LENGTH)

    def test_raw_cover_length_basic(self):
        """Test raw cover length calculation."""
        self.assertEqual(FenwickNodeMath.raw_cover_length(0), 1)
        # Node 1 is not power of 4, so it gets halved
        self.assertEqual(FenwickNodeMath.raw_cover_length(1), 1)
        self.assertEqual(FenwickNodeMath.raw_cover_length(3), 4)

    def test_is_leaf(self):
        """Test is_leaf method."""
        # Node 0 is a leaf
        self.assertTrue(FenwickNodeMath.is_leaf(0))
        # Node 1 is a leaf
        self.assertTrue(FenwickNodeMath.is_leaf(1))
        # Node 3 is NOT a leaf (internal node)
        self.assertFalse(FenwickNodeMath.is_leaf(3))

    def test_parent(self):
        """Test parent calculation."""
        # Parent of node 0 should be node 3
        result = FenwickNodeMath.parent(0)
        self.assertEqual(result, 3)

    def test_ancestor_covering(self):
        """Test ancestor_covering method."""
        result = FenwickNodeMath.ancestor_covering(5, 4)
        self.assertEqual(result, 5 | (4 - 1))  # 5 | 3 = 7


class TestOrderStatus(unittest.TestCase):
    """Test cases for OrderStatus enum."""

    def test_order_status_values(self):
        """Test OrderStatus enum values."""
        self.assertEqual(OrderStatus.NOT_EXIST, 0)
        self.assertEqual(OrderStatus.OPEN, 1)
        self.assertEqual(OrderStatus.PENDING_SETTLE, 2)
        self.assertEqual(OrderStatus.PURGED, 3)


class TestFTag(unittest.TestCase):
    """Test cases for FTag class."""

    def test_ftag_init_default(self):
        """Test FTag initialization with default value."""
        ftag = FTag()
        self.assertEqual(ftag.value, 0)

    def test_ftag_init_with_value(self):
        """Test FTag initialization with specific value."""
        ftag = FTag(100)
        self.assertEqual(ftag.value, 100)

    def test_ftag_zero(self):
        """Test FTag.ZERO() class method."""
        ftag = FTag.ZERO()
        self.assertEqual(ftag.value, 0)

    def test_ftag_is_purge(self):
        """Test is_purge method."""
        # Normal tag is not purge
        ftag = FTag(100)
        self.assertFalse(ftag.is_purge())

        # Purge tag is 0xFFFFFFFF
        purge_tag = FTag(0xFFFFFFFF)
        self.assertTrue(purge_tag.is_purge())

    def test_ftag_int_conversion(self):
        """Test __int__ method."""
        ftag = FTag(123)
        self.assertEqual(int(ftag), 123)

    def test_ftag_repr(self):
        """Test __repr__ method."""
        ftag = FTag(42)
        self.assertIn("FTag(42)", repr(ftag))


class TestMatchEvent(unittest.TestCase):
    """Test cases for MatchEvent class."""

    def test_match_event_init_default(self):
        """Test MatchEvent initialization with default values."""
        event = MatchEvent()
        self.assertEqual(event.head_index, 0)
        self.assertEqual(event.f_tag.value, 0)

    def test_match_event_init_with_values(self):
        """Test MatchEvent initialization with specific values."""
        ftag = FTag(10)
        event = MatchEvent(head_index=5, f_tag=ftag)
        self.assertEqual(event.head_index, 5)
        self.assertEqual(event.f_tag.value, 10)

    def test_match_event_from_values(self):
        """Test MatchEvent.from_values class method."""
        event = MatchEvent.from_values(15, 20)
        self.assertEqual(event.head_index, 15)
        self.assertEqual(event.f_tag.value, 20)

    def test_match_event_repr(self):
        """Test __repr__ method."""
        event = MatchEvent(5, FTag(10))
        repr_str = repr(event)
        self.assertIn("head=5", repr_str)
        self.assertIn("fTag=", repr_str)


class TestTickInfo(unittest.TestCase):
    """Test cases for TickInfo class."""

    def test_tick_info_init(self):
        """Test TickInfo initialization."""
        info = TickInfo()
        self.assertEqual(info.tick_sum, 0)
        self.assertEqual(info.head_index, 0)
        self.assertEqual(info.tail_index, 0)
        self.assertEqual(info.tick_nonce, 0)
        self.assertEqual(info.active_tick_nonce, 0)

    def test_tick_info_read(self):
        """Test read method."""
        info = TickInfo()
        result = info.read()
        self.assertEqual(len(result), 5)
        self.assertEqual(result, (0, 0, 0, 0, 0))

    def test_tick_info_write(self):
        """Test write method."""
        info = TickInfo()
        info.write(100, 5, 10, 1, 2)
        
        self.assertEqual(info.tick_sum, 100)
        self.assertEqual(info.head_index, 5)
        self.assertEqual(info.tail_index, 10)
        self.assertEqual(info.tick_nonce, 1)
        self.assertEqual(info.active_tick_nonce, 2)


class TestTickNonceData(unittest.TestCase):
    """Test cases for TickNonceData class."""

    def test_tick_nonce_data_init(self):
        """Test TickNonceData initialization."""
        data = TickNonceData()
        self.assertIsNone(data.last_event)
        self.assertEqual(data.first_event_id, 0)
        self.assertEqual(data.last_event_id, 0)
        self.assertEqual(data.next_active_nonce, 0xFFFFFFFFFFFFFFFF)

    def test_tick_nonce_data_from_event(self):
        """Test from_event class method."""
        event = MatchEvent(5, FTag(10))
        data = TickNonceData.from_event(event, 1, 2, 3)
        
        self.assertEqual(data.last_event.head_index, 5)
        self.assertEqual(data.first_event_id, 1)
        self.assertEqual(data.last_event_id, 2)
        self.assertEqual(data.next_active_nonce, 3)

    def test_tick_nonce_data_zero(self):
        """Test ZERO class method."""
        data = TickNonceData.ZERO()
        self.assertIsNone(data.last_event)
        self.assertEqual(data.first_event_id, 0)
        self.assertEqual(data.last_event_id, 0)

    def test_tick_nonce_data_is_zero(self):
        """Test is_zero method."""
        data = TickNonceData.ZERO()
        self.assertTrue(data.is_zero())
        
        # Not zero if has last_event
        event = MatchEvent()
        data.last_event = event
        self.assertFalse(data.is_zero())

    def test_tick_nonce_data_replace_next_active_nonce(self):
        """Test replace_next_active_nonce method."""
        data = TickNonceData()
        result = data.replace_next_active_nonce(100)
        
        self.assertEqual(data.next_active_nonce, 100)
        self.assertIs(result, data)

    def test_tick_nonce_data_repr(self):
        """Test __repr__ method."""
        data = TickNonceData()
        repr_str = repr(data)
        self.assertIn("TickNonceData", repr_str)


class TestNodeData(unittest.TestCase):
    """Test cases for NodeData class."""

    def test_node_data_init(self):
        """Test NodeData initialization."""
        node = NodeData()
        self.assertEqual(node.order_size, 0)
        self.assertEqual(node.maker_nonce, 0)
        self.assertEqual(node.tick_nonce, 0)
        self.assertEqual(node.ref_tick_nonce, 0)

    def test_node_data_from_values(self):
        """Test from_values class method."""
        node = NodeData.from_values(100, 5, 3, 2)
        
        self.assertEqual(node.order_size, 100)
        self.assertEqual(node.maker_nonce, 5)
        self.assertEqual(node.tick_nonce, 3)
        self.assertEqual(node.ref_tick_nonce, 2)

    def test_node_data_value_methods(self):
        """Test value getter methods."""
        node = NodeData.from_values(100, 5, 3, 2)
        
        self.assertEqual(node.order_size_value(), 100)
        self.assertEqual(node.maker_nonce_value(), 5)
        self.assertEqual(node.tick_nonce_value(), 3)
        self.assertEqual(node.ref_tick_nonce_value(), 2)

    def test_node_data_dec_order_size(self):
        """Test dec_order_size method."""
        node = NodeData.from_values(100, 5, 3, 2)
        result = node.dec_order_size(30)
        
        self.assertEqual(node.order_size, 70)
        self.assertIs(result, node)

    def test_node_data_zero(self):
        """Test ZERO class method."""
        node = NodeData.ZERO()
        self.assertEqual(node.order_size, 0)
        self.assertEqual(node.maker_nonce, 0)
        self.assertEqual(node.tick_nonce, 0)
        self.assertEqual(node.ref_tick_nonce, 0)

    def test_node_data_repr(self):
        """Test __repr__ method."""
        node = NodeData.from_values(100, 5, 3, 2)
        repr_str = repr(node)
        self.assertIn("NodeData", repr_str)
        self.assertIn("size=100", repr_str)


class TestTick(unittest.TestCase):
    """Test cases for Tick class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tick = Tick()

    def test_tick_init(self):
        """Test Tick initialization."""
        self.assertEqual(self.tick.info.tick_sum, 0)
        self.assertEqual(self.tick.info.head_index, 0)
        self.assertEqual(self.tick.info.tail_index, 0)
        self.assertEqual(self.tick.info.tick_nonce, 0)
        self.assertEqual(self.tick.info.active_tick_nonce, 0)
        self.assertEqual(len(self.tick.nodes), 0)
        self.assertEqual(len(self.tick.subtree_sum), 0)
        self.assertEqual(len(self.tick.match_events), 0)
        self.assertEqual(len(self.tick.tick_nonce_data), 0)

    def test_insert_order_basic(self):
        """Test basic order insertion."""
        order_index, old_tick_sum = self.tick.insert_order(size=100, maker_nonce=1)
        
        self.assertEqual(order_index, 0)
        self.assertEqual(old_tick_sum, 0)
        self.assertEqual(self.tick.info.tick_sum, 100)
        self.assertEqual(self.tick.info.tail_index, 1)
        self.assertIn(0, self.tick.nodes)

    def test_insert_multiple_orders(self):
        """Test multiple order insertions."""
        self.tick.insert_order(size=100, maker_nonce=1)
        self.tick.insert_order(size=200, maker_nonce=2)
        
        self.assertEqual(self.tick.info.tick_sum, 300)
        self.assertEqual(self.tick.info.tail_index, 2)

    def test_try_remove_basic(self):
        """Test basic order removal."""
        self.tick.insert_order(size=100, maker_nonce=1)
        removed_size, new_tick_sum = self.tick.try_remove(0)
        
        self.assertEqual(removed_size, 100)
        self.assertEqual(new_tick_sum, 0)

    def test_try_remove_invalid_index(self):
        """Test removing with invalid index."""
        with self.assertRaises(ValueError) as context:
            self.tick.try_remove(100)
        
        self.assertEqual(str(context.exception), "MarketOrderNotFound")

    def test_try_remove_non_strict_not_found(self):
        """Test non-strict removal when order index is beyond tail."""
        self.tick.insert_order(size=100, maker_nonce=1)
        # When order_index >= tail_index, it raises ValueError regardless of is_strict
        with self.assertRaises(ValueError) as context:
            self.tick.try_remove(5, is_strict=False)
        
        self.assertEqual(str(context.exception), "MarketOrderNotFound")

    def test_try_remove_strict_not_found(self):
        """Test strict removal when order not found."""
        self.tick.insert_order(size=100, maker_nonce=1)
        
        with self.assertRaises(ValueError) as context:
            self.tick.try_remove(5, is_strict=True)
        
        self.assertEqual(str(context.exception), "MarketOrderNotFound")

    def test_try_remove_already_zero(self):
        """Test removing an order that's already zero."""
        self.tick.insert_order(size=100, maker_nonce=1)
        self.tick.try_remove(0)
        
        # Try to remove again - should return 0 in non-strict mode
        removed_size, new_tick_sum = self.tick.try_remove(0, is_strict=False)
        self.assertEqual(removed_size, 0)

    def test_try_remove_strict_zero_order(self):
        """Test strict removal of zero order."""
        self.tick.insert_order(size=100, maker_nonce=1)
        self.tick.try_remove(0)
        
        with self.assertRaises(ValueError) as context:
            self.tick.try_remove(0, is_strict=True)
        
        self.assertEqual(str(context.exception), "MarketOrderCancelled")

    def test_get_tick_sum(self):
        """Test get_tick_sum method."""
        self.assertEqual(self.tick.get_tick_sum(), 0)
        
        self.tick.insert_order(size=100, maker_nonce=1)
        self.assertEqual(self.tick.get_tick_sum(), 100)

    def test_can_settle_skip_size_check(self):
        """Test can_settle_skip_size_check method."""
        # Initially head_index is 0, so order at index 0 can't be settled
        self.assertFalse(self.tick.can_settle_skip_size_check(0))
        
        self.tick.insert_order(size=100, maker_nonce=1)
        # After insert, head is still 0, order at 0 can't be settled yet
        self.assertFalse(self.tick.can_settle_skip_size_check(0))

    def test_get_order_status_not_exist(self):
        """Test get_order_status_and_size for non-existent order."""
        status, size = self.tick.get_order_status_and_size(0)
        self.assertEqual(status, OrderStatus.NOT_EXIST)
        self.assertEqual(size, 0)

    def test_get_order_status_open(self):
        """Test get_order_status_and_size for open order."""
        self.tick.insert_order(size=100, maker_nonce=1)
        status, size = self.tick.get_order_status_and_size(0)
        
        self.assertEqual(status, OrderStatus.OPEN)
        self.assertEqual(size, 100)

    def test_get_settle_size(self):
        """Test get_settle_size method."""
        self.tick.insert_order(size=100, maker_nonce=1)
        size = self.tick.get_settle_size(0)
        
        self.assertEqual(size, 100)

    def test_get_settle_size_not_found(self):
        """Test get_settle_size for non-existent order."""
        # get_settle_size raises KeyError for non-existent order
        with self.assertRaises(KeyError):
            self.tick.get_settle_size(0)

    def test_get_settle_size_and_f_tag(self):
        """Test get_settle_size_and_f_tag method."""
        self.tick.insert_order(size=100, maker_nonce=1)
        size, ftag = self.tick.get_settle_size_and_f_tag(0)
        
        self.assertEqual(size, 100)
        self.assertIsInstance(ftag, FTag)

    def test_get_settle_size_and_f_tag_not_found(self):
        """Test get_settle_size_and_f_tag for non-existent order."""
        size, ftag = self.tick.get_settle_size_and_f_tag(0)
        
        self.assertEqual(size, 0)
        self.assertEqual(ftag.value, 0)

    def test_match_all_fill_result(self):
        """Test match_all_fill_result method."""
        self.tick.insert_order(size=100, maker_nonce=1)
        
        result = TickMatchResult(0, 0, 0)
        self.tick.match_all_fill_result(FTag(10), result)
        
        self.assertEqual(result.partial_size, 0)
        self.assertEqual(result.begin_fully_filled_order_index, 0)
        self.assertEqual(result.end_fully_filled_order_index, 1)
        self.assertEqual(self.tick.info.tick_sum, 0)
        self.assertEqual(self.tick.info.head_index, 1)
        self.assertEqual(self.tick.info.tail_index, 1)

    def test_match_partial_fill_result(self):
        """Test match_partial_fill_result method."""
        self.tick.insert_order(size=100, maker_nonce=1)
        self.tick.insert_order(size=100, maker_nonce=2)
        
        result = TickMatchResult(0, 0, 0)
        self.tick.match_partial_fill_result(50, FTag(10), result)
        
        # Should have partial fill in first order
        self.assertGreater(result.partial_size, 0)
        self.assertEqual(result.begin_fully_filled_order_index, 0)

    def test_push_new_match_event(self):
        """Test _push_new_match_event method."""
        self.tick.insert_order(size=100, maker_nonce=1)
        
        result = self.tick._push_new_match_event(
            cur_tick_nonce=0,
            active_tick_nonce=0,
            head_index=0,
            f_tag=FTag(10)
        )
        
        self.assertEqual(result, 0)
        self.assertEqual(len(self.tick.match_events), 1)

    def test_tick_repr(self):
        """Test __repr__ method."""
        self.tick.insert_order(size=100, maker_nonce=1)
        repr_str = repr(self.tick)
        
        self.assertIn("Tick", repr_str)
        self.assertIn("tickSum=100", repr_str)


class TestTickIntegration(unittest.TestCase):
    """Integration tests for Tick class with multiple operations."""

    def test_multiple_insert_and_remove(self):
        """Test multiple insert and remove operations."""
        tick = Tick()
        
        # Insert multiple orders
        idx1, _ = tick.insert_order(size=100, maker_nonce=1)
        idx2, _ = tick.insert_order(size=200, maker_nonce=2)
        idx3, _ = tick.insert_order(size=300, maker_nonce=3)
        
        self.assertEqual(tick.get_tick_sum(), 600)
        
        # Remove middle order
        removed, _ = tick.try_remove(idx2)
        self.assertEqual(removed, 200)
        
        # Remaining sum should be 400
        self.assertEqual(tick.get_tick_sum(), 400)

    def test_order_lifecycle(self):
        """Test complete order lifecycle."""
        tick = Tick()
        
        # Insert order
        idx, _ = tick.insert_order(size=100, maker_nonce=1)
        
        # Check order status
        status, size = tick.get_order_status_and_size(idx)
        self.assertEqual(status, OrderStatus.OPEN)
        self.assertEqual(size, 100)
        
        # Get settle info
        settle_size, ftag = tick.get_settle_size_and_f_tag(idx)
        self.assertEqual(settle_size, 100)

    def test_match_events_tracking(self):
        """Test match events are tracked correctly."""
        tick = Tick()
        
        # Insert orders
        tick.insert_order(size=100, maker_nonce=1)
        tick.insert_order(size=100, maker_nonce=2)
        
        # Fill entire tick
        result = TickMatchResult(0, 0, 0)
        tick.match_all_fill_result(FTag(1), result)
        
        # Should have one match event
        self.assertEqual(len(tick.match_events), 1)
        
        # Fill partial
        result2 = TickMatchResult(0, 0, 0)
        tick.match_partial_fill_result(50, FTag(2), result2)
        
        # Should have two match events
        self.assertEqual(len(tick.match_events), 2)


if __name__ == '__main__':
    unittest.main()
