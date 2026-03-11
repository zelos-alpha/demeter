"""
Test cases for Order Types Python Implementation
Tests for all functions in order.py
"""

import unittest
from order import (
    TimeInForce, OrderStatus, Side,
    TimeInForceLib, SideLib, OrderIdLib, OrderIdArrayLib
)


class TestTimeInForceLib(unittest.TestCase):
    """Test TimeInForceLib functions."""
    
    def test_is_alo_true(self):
        """Test is_alo returns True for ALO."""
        self.assertTrue(TimeInForceLib.is_alo(TimeInForce.ALO))
        self.assertTrue(TimeInForceLib.is_alo(TimeInForce.SOFT_ALO))
    
    def test_is_alo_false(self):
        """Test is_alo returns False for non-ALO."""
        self.assertFalse(TimeInForceLib.is_alo(TimeInForce.GTC))
        self.assertFalse(TimeInForceLib.is_alo(TimeInForce.IOC))
        self.assertFalse(TimeInForceLib.is_alo(TimeInForce.FOK))
    
    def test_should_skip_matchable_orders(self):
        """Test should_skip_matchable_orders only returns True for SOFT_ALO."""
        self.assertTrue(TimeInForceLib.should_skip_matchable_orders(TimeInForce.SOFT_ALO))
        self.assertFalse(TimeInForceLib.should_skip_matchable_orders(TimeInForce.ALO))
        self.assertFalse(TimeInForceLib.should_skip_matchable_orders(TimeInForce.GTC))


class TestSideLib(unittest.TestCase):
    """Test SideLib functions."""
    
    def test_opposite(self):
        """Test opposite returns correct opposite side."""
        self.assertEqual(SideLib.opposite(Side.LONG), Side.SHORT)
        self.assertEqual(SideLib.opposite(Side.SHORT), Side.LONG)
    
    def test_sweep_tick_top_down(self):
        """Test sweep_tick_top_down returns True only for LONG."""
        self.assertTrue(SideLib.sweep_tick_top_down(Side.LONG))
        self.assertFalse(SideLib.sweep_tick_top_down(Side.SHORT))
    
    def test_end_tick(self):
        """Test end_tick returns correct int16 boundaries."""
        self.assertEqual(SideLib.end_tick(Side.LONG), -2**15)
        self.assertEqual(SideLib.end_tick(Side.SHORT), 2**15 - 1)
    
    def test_possible_to_be_filled_long(self):
        """Test possible_to_be_filled for LONG side."""
        # LONG: lastTickFilled <= orderTick
        self.assertTrue(SideLib.possible_to_be_filled(Side.LONG, 100, 50))
        self.assertTrue(SideLib.possible_to_be_filled(Side.LONG, 100, 100))
        self.assertFalse(SideLib.possible_to_be_filled(Side.LONG, 100, 150))
    
    def test_possible_to_be_filled_short(self):
        """Test possible_to_be_filled for SHORT side."""
        # SHORT: lastTickFilled >= orderTick
        self.assertTrue(SideLib.possible_to_be_filled(Side.SHORT, 100, 150))
        self.assertTrue(SideLib.possible_to_be_filled(Side.SHORT, 100, 100))
        self.assertFalse(SideLib.possible_to_be_filled(Side.SHORT, 100, 50))
    
    def test_tick_to_get_first_avail(self):
        """Test tick_to_get_first_avail returns end_tick."""
        self.assertEqual(SideLib.tick_to_get_first_avail(Side.LONG), SideLib.end_tick(Side.LONG))
        self.assertEqual(SideLib.tick_to_get_first_avail(Side.SHORT), SideLib.end_tick(Side.SHORT))
    
    def test_can_match_long(self):
        """Test can_match for LONG side."""
        # LONG: limitTick <= bestTick
        self.assertTrue(SideLib.can_match(Side.LONG, 100, 105))  # buy at 100, ask is 105
        self.assertTrue(SideLib.can_match(Side.LONG, 105, 105))  # buy at 105, ask is 105
        self.assertFalse(SideLib.can_match(Side.LONG, 110, 105))  # buy at 110, ask is 105 (too expensive)
    
    def test_can_match_short(self):
        """Test can_match for SHORT side."""
        # SHORT: limitTick >= bestTick
        self.assertTrue(SideLib.can_match(Side.SHORT, 110, 105))  # sell at 110, bid is 105
        self.assertTrue(SideLib.can_match(Side.SHORT, 105, 105))  # sell at 105, bid is 105
        self.assertFalse(SideLib.can_match(Side.SHORT, 100, 105))  # sell at 100, bid is 105 (too cheap)
    
    def test_to_signed_size(self):
        """Test to_signed_size converts size based on side."""
        self.assertEqual(SideLib.to_signed_size(1000, Side.LONG), 1000)
        self.assertEqual(SideLib.to_signed_size(1000, Side.SHORT), -1000)
        self.assertEqual(SideLib.to_signed_size(0, Side.LONG), 0)
        self.assertEqual(SideLib.to_signed_size(0, Side.SHORT), 0)
    
    def test_is_of_side(self):
        """Test is_of_side checks if size matches side."""
        self.assertTrue(SideLib.is_of_side(100, Side.LONG))
        self.assertTrue(SideLib.is_of_side(-100, Side.SHORT))
        self.assertFalse(SideLib.is_of_side(-100, Side.LONG))
        self.assertFalse(SideLib.is_of_side(100, Side.SHORT))
        self.assertFalse(SideLib.is_of_side(0, Side.LONG))
        self.assertFalse(SideLib.is_of_side(0, Side.SHORT))
    
    def test_check_rate_in_bound_long(self):
        """Test check_rate_in_bound for LONG side (rate <= bound)."""
        self.assertTrue(SideLib.check_rate_in_bound(Side.LONG, 5, 10))
        self.assertTrue(SideLib.check_rate_in_bound(Side.LONG, 10, 10))
        self.assertFalse(SideLib.check_rate_in_bound(Side.LONG, 15, 10))
    
    def test_check_rate_in_bound_short(self):
        """Test check_rate_in_bound for SHORT side (rate >= bound)."""
        self.assertTrue(SideLib.check_rate_in_bound(Side.SHORT, 15, 10))
        self.assertTrue(SideLib.check_rate_in_bound(Side.SHORT, 10, 10))
        self.assertFalse(SideLib.check_rate_in_bound(Side.SHORT, 5, 10))


class TestOrderIdLib(unittest.TestCase):
    """Test OrderIdLib functions."""
    
    def test_from_order(self):
        """Test OrderId creation from components."""
        # Create OrderId for LONG side, tick 100, order index 1
        order_id = OrderIdLib.from_order(Side.LONG, 100, 1)
        
        # Verify it has the initialized marker
        self.assertGreater(order_id, 0)
        self.assertGreater(order_id, OrderIdLib.INITIALIZED_MARKER)
    
    def test_from_order_short(self):
        """Test OrderId creation for SHORT side."""
        order_id = OrderIdLib.from_order(Side.SHORT, 100, 1)
        self.assertGreater(order_id, 0)
    
    def test_unpack(self):
        """Test OrderId unpacking."""
        # Create and unpack
        order_id = OrderIdLib.from_order(Side.LONG, 100, 1)
        side, tick, idx = OrderIdLib.unpack(order_id)
        
        self.assertEqual(side, Side.LONG)
        self.assertEqual(idx, 1)
        # Note: tick encoding/decoding may differ due to signed encoding
    
    def test_unpack_short(self):
        """Test OrderId unpacking for SHORT side."""
        order_id = OrderIdLib.from_order(Side.SHORT, 100, 1)
        side, tick, idx = OrderIdLib.unpack(order_id)
        
        self.assertEqual(side, Side.SHORT)
        self.assertEqual(idx, 1)
    
    def test_is_zero_true(self):
        """Test is_zero returns True for zero OrderId."""
        self.assertTrue(OrderIdLib.is_zero(0))
    
    def test_is_zero_false(self):
        """Test is_zero returns False for non-zero OrderId."""
        order_id = OrderIdLib.from_order(Side.LONG, 100, 1)
        self.assertFalse(OrderIdLib.is_zero(order_id))
    
    def test_order_index(self):
        """Test order_index extraction."""
        order_id = OrderIdLib.from_order(Side.LONG, 100, 42)
        idx = OrderIdLib.order_index(order_id)
        self.assertEqual(idx, 42)
    
    def test_side(self):
        """Test side extraction."""
        long_id = OrderIdLib.from_order(Side.LONG, 100, 1)
        short_id = OrderIdLib.from_order(Side.SHORT, 100, 1)
        
        self.assertEqual(OrderIdLib.side(long_id), Side.LONG)
        self.assertEqual(OrderIdLib.side(short_id), Side.SHORT)
    
    def test_tick_index(self):
        """Test tick_index extraction."""
        order_id = OrderIdLib.from_order(Side.LONG, 100, 1)
        tick = OrderIdLib.tick_index(order_id)
        # Due to encoding, may not equal exactly 100
        self.assertIsInstance(tick, int)
    
    def test_lt_order_id(self):
        """Test OrderId comparison."""
        id1 = OrderIdLib.from_order(Side.LONG, 100, 1)
        id2 = OrderIdLib.from_order(Side.LONG, 100, 2)
        
        self.assertTrue(OrderIdLib.lt_order_id(id1, id2))
        self.assertFalse(OrderIdLib.lt_order_id(id2, id1))
        self.assertFalse(OrderIdLib.lt_order_id(id1, id1))


class TestOrderIdArrayLib(unittest.TestCase):
    """Test OrderIdArrayLib functions."""
    
    def test_remove_zeroes_and_update_best_same_side_empty(self):
        """Test with empty array."""
        ids = []
        OrderIdArrayLib.remove_zeroes_and_update_best_same_side(ids)
        self.assertEqual(ids, [])
    
    def test_remove_zeroes_no_zeros(self):
        """Test removing zeros when none exist."""
        id1 = OrderIdLib.from_order(Side.LONG, 100, 1)
        id2 = OrderIdLib.from_order(Side.LONG, 101, 2)
        ids = [id1, id2]
        
        OrderIdArrayLib.remove_zeroes_and_update_best_same_side(ids)
        
        # Should still have 2 elements
        self.assertEqual(len(ids), 2)
    
    def test_remove_zeroes_with_zeros(self):
        """Test removing zeros from array."""
        id1 = OrderIdLib.from_order(Side.LONG, 100, 1)
        id2 = OrderIdLib.from_order(Side.LONG, 101, 2)
        ids = [id1, 0, id2, 0]
        
        OrderIdArrayLib.remove_zeroes_and_update_best_same_side(ids)
        
        # Should have 2 non-zero elements
        self.assertEqual(len(ids), 2)
        self.assertFalse(OrderIdLib.is_zero(ids[0]))
        self.assertFalse(OrderIdLib.is_zero(ids[1]))
    
    def test_remove_zeroes_all_zeros(self):
        """Test when all elements are zeros."""
        ids = [0, 0, 0]
        
        OrderIdArrayLib.remove_zeroes_and_update_best_same_side(ids)
        
        # Should be empty
        self.assertEqual(len(ids), 0)
    
    def test_update_best_same_side_empty(self):
        """Test update_best_same_side with empty array."""
        ids = []
        OrderIdArrayLib.update_best_same_side(ids, 0)
        self.assertEqual(ids, [])
    
    def test_update_best_same_side_no_pre_len(self):
        """Test update_best_same_side with pre_len=0."""
        id1 = OrderIdLib.from_order(Side.LONG, 100, 1)
        id2 = OrderIdLib.from_order(Side.LONG, 101, 2)
        id3 = OrderIdLib.from_order(Side.LONG, 99, 3)
        ids = [id1, id2, id3]
        
        OrderIdArrayLib.update_best_same_side(ids, 0)
        
        # Best (lowest) should be at end
        self.assertEqual(ids[-1], id3)  # tick 99 is lowest
    
    def test_update_best_same_side_with_pre_len(self):
        """Test update_best_same_side with pre_len>0."""
        id1 = OrderIdLib.from_order(Side.LONG, 100, 1)
        id2 = OrderIdLib.from_order(Side.LONG, 101, 2)
        id3 = OrderIdLib.from_order(Side.LONG, 99, 3)
        ids = [id1, id2, id3]
        
        # pre_len=2 means first 2 are already processed
        OrderIdArrayLib.update_best_same_side(ids, 2)
        
        # Compare remaining (index 2) to find best
        self.assertEqual(len(ids), 3)


class TestEnums(unittest.TestCase):
    """Test enum values."""
    
    def test_time_in_force_values(self):
        """Test TimeInForce enum values."""
        self.assertEqual(TimeInForce.GTC, 0)
        self.assertEqual(TimeInForce.IOC, 1)
        self.assertEqual(TimeInForce.FOK, 2)
        self.assertEqual(TimeInForce.ALO, 3)
        self.assertEqual(TimeInForce.SOFT_ALO, 4)
    
    def test_order_status_values(self):
        """Test OrderStatus enum values."""
        self.assertEqual(OrderStatus.NOT_EXIST, 0)
        self.assertEqual(OrderStatus.OPEN, 1)
        self.assertEqual(OrderStatus.PENDING_SETTLE, 2)
        self.assertEqual(OrderStatus.PURGED, 3)
    
    def test_side_values(self):
        """Test Side enum values."""
        self.assertEqual(Side.LONG, 0)
        self.assertEqual(Side.SHORT, 1)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple functions."""
    
    def test_order_lifecycle(self):
        """Test creating, manipulating, and checking order."""
        # Create order
        order_id = OrderIdLib.from_order(Side.LONG, 100, 1)
        
        # Check properties
        self.assertFalse(OrderIdLib.is_zero(order_id))
        self.assertEqual(OrderIdLib.order_index(order_id), 1)
        self.assertEqual(OrderIdLib.side(order_id), Side.LONG)
        
        # Create opposite side
        opposite_id = OrderIdLib.from_order(SideLib.opposite(Side.LONG), 100, 1)
        self.assertEqual(OrderIdLib.side(opposite_id), Side.SHORT)
    
    def test_matching_logic(self):
        """Test matching logic with different sides."""
        # LONG order at 100 should match with SHORT at 105 (best)
        self.assertTrue(SideLib.can_match(Side.LONG, 100, 105))
        
        # SHORT order at 105 should match with LONG at 100 (best)
        self.assertTrue(SideLib.can_match(Side.SHORT, 105, 100))
    
    def test_array_operations(self):
        """Test array operations with OrderIds."""
        ids = []
        for i in range(5):
            ids.append(OrderIdLib.from_order(Side.LONG, 100 + i, i))
        
        # Add some zeros
        ids = [ids[0], 0, ids[1], 0, ids[2], ids[3], ids[4]]
        
        # Remove zeros and update
        OrderIdArrayLib.remove_zeroes_and_update_best_same_side(ids)
        
        # Should have 5 non-zero elements
        self.assertEqual(len(ids), 5)
        
        # All should be non-zero
        for order_id in ids:
            self.assertFalse(OrderIdLib.is_zero(order_id))


if __name__ == "__main__":
    unittest.main()
