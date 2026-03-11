"""
Test cases for Trade Types Python Implementation
Tests for all functions in trade.py
"""

import unittest
from trade import (
    TradeLib, FillLib,
    TradeUndesiredSideError, TradeUndesiredRateError
)
from order import Side


class TestTradeLibFrom(unittest.TestCase):
    """Test TradeLib creation functions."""
    
    def test_from_signed_values(self):
        """Test from_signed_values creates correct trade."""
        trade = TradeLib.from_signed_values(1000, 500)
        
        # Unpack and verify
        size, cost = TradeLib.unpack(trade)
        self.assertEqual(size, 1000)
        self.assertEqual(cost, 500)
    
    def test_from_128_positive(self):
        """Test from_128 with positive values."""
        trade = TradeLib.from_128(2**127 - 1, 2**127 - 1)
        
        size, cost = TradeLib.unpack(trade)
        self.assertEqual(size, 2**127 - 1)
        self.assertEqual(cost, 2**127 - 1)
    
    def test_from_128_negative(self):
        """Test from_128 with negative values."""
        trade = TradeLib.from_128(-1000, -500)
        
        size, cost = TradeLib.unpack(trade)
        self.assertEqual(size, -1000)
        self.assertEqual(cost, -500)
    
    def test_zero_trade(self):
        """Test zero trade creation."""
        trade = TradeLib.ZERO
        self.assertEqual(trade, 0)


class TestTradeLibUnpack(unittest.TestCase):
    """Test TradeLib unpack function."""
    
    def test_unpack_positive_trade(self):
        """Test unpacking a positive trade."""
        trade = TradeLib.from_signed_values(1000, 500)
        size, cost = TradeLib.unpack(trade)
        
        self.assertEqual(size, 1000)
        self.assertEqual(cost, 500)
    
    def test_unpack_negative_trade(self):
        """Test unpacking a negative trade."""
        trade = TradeLib.from_signed_values(-1000, -500)
        size, cost = TradeLib.unpack(trade)
        
        self.assertEqual(size, -1000)
        self.assertEqual(cost, -500)
    
    def test_unpack_zero_trade(self):
        """Test unpacking a zero trade."""
        size, cost = TradeLib.unpack(TradeLib.ZERO)
        
        self.assertEqual(size, 0)
        self.assertEqual(cost, 0)


class TestTradeLibSide(unittest.TestCase):
    """Test TradeLib side function."""
    
    def test_side_long_positive(self):
        """Test side returns LONG for positive trade."""
        trade = TradeLib.from_signed_values(1000, 500)
        self.assertEqual(TradeLib.side(trade), Side.LONG)
    
    def test_side_short_negative(self):
        """Test side returns SHORT for negative trade."""
        trade = TradeLib.from_signed_values(-1000, -500)
        self.assertEqual(TradeLib.side(trade), Side.SHORT)
    
    def test_side_zero(self):
        """Test side returns SHORT for zero trade (size = 0)."""
        self.assertEqual(TradeLib.side(TradeLib.ZERO), Side.SHORT)


class TestTradeLibSize(unittest.TestCase):
    """Test TradeLib size functions."""
    
    def test_signed_size_positive(self):
        """Test signed_size for positive trade."""
        trade = TradeLib.from_signed_values(1000, 500)
        self.assertEqual(TradeLib.signed_size(trade), 1000)
    
    def test_signed_size_negative(self):
        """Test signed_size for negative trade."""
        trade = TradeLib.from_signed_values(-1000, -500)
        self.assertEqual(TradeLib.signed_size(trade), -1000)
    
    def test_signed_size_zero(self):
        """Test signed_size for zero trade."""
        self.assertEqual(TradeLib.signed_size(TradeLib.ZERO), 0)
    
    def test_abs_size_positive(self):
        """Test abs_size for positive trade."""
        trade = TradeLib.from_signed_values(1000, 500)
        self.assertEqual(TradeLib.abs_size(trade), 1000)
    
    def test_abs_size_negative(self):
        """Test abs_size for negative trade."""
        trade = TradeLib.from_signed_values(-1000, -500)
        self.assertEqual(TradeLib.abs_size(trade), 1000)


class TestTradeLibCost(unittest.TestCase):
    """Test TradeLib cost functions."""
    
    def test_signed_cost_positive(self):
        """Test signed_cost for positive trade."""
        trade = TradeLib.from_signed_values(1000, 500)
        self.assertEqual(TradeLib.signed_cost(trade), 500)
    
    def test_signed_cost_negative(self):
        """Test signed_cost for negative trade."""
        trade = TradeLib.from_signed_values(-1000, -500)
        self.assertEqual(TradeLib.signed_cost(trade), -500)
    
    def test_abs_cost(self):
        """Test abs_cost returns absolute value."""
        trade = TradeLib.from_signed_values(-1000, -500)
        self.assertEqual(TradeLib.abs_cost(trade), 500)


class TestTradeLibAdd(unittest.TestCase):
    """Test TradeLib add function."""
    
    def test_add_positive_trades(self):
        """Test adding two positive trades."""
        trade1 = TradeLib.from_signed_values(1000, 500)
        trade2 = TradeLib.from_signed_values(500, 250)
        
        result = TradeLib.add(trade1, trade2)
        
        size, cost = TradeLib.unpack(result)
        self.assertEqual(size, 1500)
        self.assertEqual(cost, 750)
    
    def test_add_negative_trades(self):
        """Test adding two negative trades."""
        trade1 = TradeLib.from_signed_values(-1000, -500)
        trade2 = TradeLib.from_signed_values(-500, -250)
        
        result = TradeLib.add(trade1, trade2)
        
        size, cost = TradeLib.unpack(result)
        self.assertEqual(size, -1500)
        self.assertEqual(cost, -750)
    
    def test_add_opposite_trades(self):
        """Test adding opposite trades (should cancel)."""
        trade1 = TradeLib.from_signed_values(1000, 500)
        trade2 = TradeLib.from_signed_values(-1000, -500)
        
        result = TradeLib.add(trade1, trade2)
        
        self.assertTrue(TradeLib.is_zero(result))
    
    def test_add_with_zero(self):
        """Test adding trade with zero."""
        trade1 = TradeLib.from_signed_values(1000, 500)
        
        result = TradeLib.add(trade1, TradeLib.ZERO)
        
        size, cost = TradeLib.unpack(result)
        self.assertEqual(size, 1000)
        self.assertEqual(cost, 500)


class TestTradeLibOpposite(unittest.TestCase):
    """Test TradeLib opposite function."""
    
    def test_opposite_positive(self):
        """Test opposite of positive trade."""
        trade = TradeLib.from_signed_values(1000, 500)
        opposite = TradeLib.opposite(trade)
        
        size, cost = TradeLib.unpack(opposite)
        self.assertEqual(size, -1000)
        self.assertEqual(cost, -500)
    
    def test_opposite_negative(self):
        """Test opposite of negative trade."""
        trade = TradeLib.from_signed_values(-1000, -500)
        opposite = TradeLib.opposite(trade)
        
        size, cost = TradeLib.unpack(opposite)
        self.assertEqual(size, 1000)
        self.assertEqual(cost, 500)
    
    def test_opposite_zero(self):
        """Test opposite of zero trade."""
        self.assertTrue(TradeLib.opposite(TradeLib.ZERO))


class TestTradeLibIsZero(unittest.TestCase):
    """Test TradeLib is_zero function."""
    
    def test_is_zero_true(self):
        """Test is_zero returns True for zero trade."""
        self.assertTrue(TradeLib.is_zero(TradeLib.ZERO))
    
    def test_is_zero_false(self):
        """Test is_zero returns False for non-zero trade."""
        trade = TradeLib.from_signed_values(1000, 500)
        self.assertFalse(TradeLib.is_zero(trade))


class TestTradeLibFromThree(unittest.TestCase):
    """Test TradeLib from_three function."""
    
    def test_from_three_long(self):
        """Test from_three creates correct LONG trade."""
        trade = TradeLib.from_three(Side.LONG, 1000, 500)
        
        size, cost = TradeLib.unpack(trade)
        self.assertEqual(size, 1000)
        self.assertEqual(cost, 500)
    
    def test_from_three_short(self):
        """Test from_three creates correct SHORT trade."""
        trade = TradeLib.from_three(Side.SHORT, 1000, 500)
        
        size, cost = TradeLib.unpack(trade)
        self.assertEqual(size, -1000)
        self.assertEqual(cost, -500)


class TestTradeLibRequireDesiredSideAndRate(unittest.TestCase):
    """Test TradeLib require_desired_side_and_rate function."""
    
    def test_require_matching_side_and_rate(self):
        """Test passes when side and rate match."""
        trade = TradeLib.from_three(Side.LONG, 1000, 500)
        # Should not raise
        TradeLib.require_desired_side_and_rate(trade, Side.LONG, 500)
    
    def test_require_wrong_side_raises(self):
        """Test raises when side doesn't match."""
        trade = TradeLib.from_three(Side.LONG, 1000, 500)
        
        with self.assertRaises(TradeUndesiredSideError):
            TradeLib.require_desired_side_and_rate(trade, Side.SHORT, 500)
    
    def test_require_zero_trade_no_side_check(self):
        """Test zero trade skips side check."""
        # Zero trade should pass side check
        TradeLib.require_desired_side_and_rate(TradeLib.ZERO, Side.LONG, 500)


class TestTradeLibRequireDesiredRate(unittest.TestCase):
    """Test TradeLib require_desired_rate function."""
    
    def test_require_matching_rate(self):
        """Test passes when rate matches."""
        trade = TradeLib.from_three(Side.LONG, 1000, 500)
        # Should not raise
        TradeLib.require_desired_rate(trade, 500)
    
    def test_require_higher_rate_raises(self):
        """Test raises when actual cost exceeds max allowed."""
        trade = TradeLib.from_three(Side.LONG, 1000, 500)
        
        # Rate of 400 would mean max cost = 400, but actual is 500
        with self.assertRaises(TradeUndesiredRateError):
            TradeLib.require_desired_rate(trade, 400)


class TestFillLib(unittest.TestCase):
    """Test FillLib functions."""
    
    def test_to_trade(self):
        """Test to_trade conversion."""
        fill = 12345
        trade = FillLib.to_trade(fill)
        self.assertEqual(trade, fill)
    
    def test_from_three_long(self):
        """Test from_three creates correct LONG fill."""
        fill = FillLib.from_three(Side.LONG, 1000, 500)
        
        self.assertEqual(TradeLib.signed_size(fill), 1000)
        self.assertEqual(TradeLib.signed_cost(fill), 500)
    
    def test_from_three_short(self):
        """Test from_three creates correct SHORT fill."""
        fill = FillLib.from_three(Side.SHORT, 1000, 500)
        
        self.assertEqual(TradeLib.signed_size(fill), -1000)
        self.assertEqual(TradeLib.signed_cost(fill), -500)
    
    def test_is_zero(self):
        """Test is_zero function."""
        self.assertTrue(FillLib.is_zero(FillLib.ZERO))
        self.assertFalse(FillLib.is_zero(12345))
    
    def test_side(self):
        """Test side function."""
        fill_long = FillLib.from_three(Side.LONG, 1000, 500)
        fill_short = FillLib.from_three(Side.SHORT, 1000, 500)
        
        self.assertEqual(FillLib.side(fill_long), Side.LONG)
        self.assertEqual(FillLib.side(fill_short), Side.SHORT)
    
    def test_abs_size(self):
        """Test abs_size function."""
        fill = FillLib.from_three(Side.SHORT, 1000, 500)
        self.assertEqual(FillLib.abs_size(fill), 1000)
    
    def test_abs_cost(self):
        """Test abs_cost function."""
        fill = FillLib.from_three(Side.SHORT, 1000, 500)
        self.assertEqual(FillLib.abs_cost(fill), 500)


class TestTradeLibIntegration(unittest.TestCase):
    """Integration tests for TradeLib."""
    
    def test_trade_lifecycle(self):
        """Test complete trade lifecycle."""
        # Create trade
        trade = TradeLib.from_three(Side.LONG, 1000, 500)
        
        # Check properties
        self.assertEqual(TradeLib.side(trade), Side.LONG)
        self.assertEqual(TradeLib.abs_size(trade), 1000)
        self.assertEqual(TradeLib.abs_cost(trade), 500)
        
        # Add another trade
        trade2 = TradeLib.from_three(Side.LONG, 500, 600)
        combined = TradeLib.add(trade, trade2)
        
        self.assertEqual(TradeLib.abs_size(combined), 1500)
        
        # Get opposite
        opposite = TradeLib.opposite(trade)
        self.assertEqual(TradeLib.side(opposite), Side.SHORT)
        
        # Verify opposite cancels
        result = TradeLib.add(trade, opposite)
        self.assertTrue(TradeLib.is_zero(result))
    
    def test_fill_to_trade_conversion(self):
        """Test Fill to Trade conversion."""
        fill = FillLib.from_three(Side.SHORT, 2000, 300)
        trade = FillLib.to_trade(fill)
        
        self.assertEqual(TradeLib.side(trade), Side.SHORT)
        self.assertEqual(TradeLib.abs_size(trade), 2000)
        self.assertEqual(TradeLib.abs_cost(trade), 300)


if __name__ == "__main__":
    unittest.main()
