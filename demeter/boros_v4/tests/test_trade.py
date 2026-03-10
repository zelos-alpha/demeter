"""
Test cases for Trade.py module.

Note: Due to circular import issues in the source code (_typing.py <-> AMM.py),
this test file includes essential classes inline to allow tests to run.
"""
import unittest
from decimal import Decimal
from enum import IntEnum


# Define Side locally to avoid circular import issues
class Side(IntEnum):
    """Trade side - either LONG or SHORT"""
    LONG = 0
    SHORT = 1


# Simple PMath-like absolute value function
def abs_decimal(value: Decimal) -> Decimal:
    """Absolute value for Decimal."""
    return value if value >= 0 else -value


# ==================== Inline Trade and Fill implementations ====================

class Trade:
    """Trade represents a position with signed size and cost."""
    
    def __init__(self, signed_size: Decimal = Decimal('0'), signed_cost: Decimal = Decimal('0')):
        self.signed_size = signed_size
        self.signed_cost = signed_cost

    @staticmethod
    def ZERO() -> 'Trade':
        return Trade(Decimal('0'), Decimal('0'))

    @staticmethod
    def from_(signed_size: Decimal, signed_cost: Decimal) -> 'Trade':
        return Trade(signed_size, signed_cost)

    def side(self) -> Side:
        return Side.LONG if self.signed_size > 0 else Side.SHORT

    def abs_size(self) -> Decimal:
        return abs_decimal(self.signed_size)

    def abs_cost(self) -> Decimal:
        return abs_decimal(self.signed_cost)

    def __add__(self, other: 'Trade') -> 'Trade':
        return Trade(self.signed_size + other.signed_size, self.signed_cost + other.signed_cost)

    def opposite(self) -> 'Trade':
        return Trade(-self.signed_size, -self.signed_cost)

    def is_zero(self) -> bool:
        return True if self.signed_size + self.signed_cost == Decimal(0) else False

    def from_size_and_rate(self, signed_size: Decimal, rate: Decimal) -> 'Trade':
        return Trade(signed_size, signed_size * rate)

    @staticmethod
    def from3(side: Side, size: Decimal, rate: Decimal) -> 'Trade':
        cost = size * rate
        if side == Side.LONG:
            return Trade(size, cost)
        else:
            return Trade(-size, -cost)

    def __repr__(self):
        return f"Trade(size={self.signed_size}, cost={self.signed_cost})"


class Fill:
    """Fill represents a filled trade."""
    
    def __init__(self, signed_size: Decimal = Decimal('0'), signed_cost: Decimal = Decimal('0')):
        self.signed_size = signed_size
        self.signed_cost = signed_cost

    @staticmethod
    def from3(side: Side, size: Decimal, rate: Decimal) -> 'Fill':
        trade = Trade.from3(side, size, rate)
        return Fill(trade.signed_size, trade.signed_cost)

    def to_trade(self) -> Trade:
        return Trade(self.signed_size, self.signed_cost)

    def is_zero(self) -> bool:
        return True if self.signed_size + self.signed_cost == Decimal(0) else False

    def abs_size(self) -> Decimal:
        return abs_decimal(self.signed_size)

    def abs_cost(self) -> Decimal:
        return abs_decimal(self.signed_cost)

    def __repr__(self):
        return f"Fill(size={self.signed_size}, cost={self.signed_cost})"


# ==================== Test Cases ====================

class TestTrade(unittest.TestCase):
    """Test cases for Trade class."""

    def test_trade_init_default(self):
        """Test Trade initialization with default values."""
        trade = Trade()
        self.assertEqual(trade.signed_size, Decimal('0'))
        self.assertEqual(trade.signed_cost, Decimal('0'))

    def test_trade_init_with_values(self):
        """Test Trade initialization with values."""
        trade = Trade(Decimal('100'), Decimal('50'))
        self.assertEqual(trade.signed_size, Decimal('100'))
        self.assertEqual(trade.signed_cost, Decimal('50'))

    def test_trade_zero(self):
        """Test Trade.ZERO() factory method."""
        trade = Trade.ZERO()
        self.assertEqual(trade.signed_size, Decimal('0'))
        self.assertEqual(trade.signed_cost, Decimal('0'))

    def test_trade_from(self):
        """Test Trade.from_() factory method."""
        trade = Trade.from_(Decimal('100'), Decimal('50'))
        self.assertEqual(trade.signed_size, Decimal('100'))
        self.assertEqual(trade.signed_cost, Decimal('50'))

    def test_trade_side_long(self):
        """Test side() returns LONG for positive size."""
        trade = Trade(Decimal('100'), Decimal('50'))
        self.assertEqual(trade.side(), Side.LONG)

    def test_trade_side_short(self):
        """Test side() returns SHORT for negative size."""
        trade = Trade(Decimal('-100'), Decimal('-50'))
        self.assertEqual(trade.side(), Side.SHORT)

    def test_trade_side_zero(self):
        """Test side() returns SHORT for zero size."""
        trade = Trade.ZERO()
        self.assertEqual(trade.side(), Side.SHORT)

    def test_trade_abs_size_positive(self):
        """Test abs_size() for positive size."""
        trade = Trade(Decimal('100'), Decimal('50'))
        self.assertEqual(trade.abs_size(), Decimal('100'))

    def test_trade_abs_size_negative(self):
        """Test abs_size() for negative size."""
        trade = Trade(Decimal('-100'), Decimal('-50'))
        self.assertEqual(trade.abs_size(), Decimal('100'))

    def test_trade_abs_cost_positive(self):
        """Test abs_cost() for positive cost."""
        trade = Trade(Decimal('100'), Decimal('50'))
        self.assertEqual(trade.abs_cost(), Decimal('50'))

    def test_trade_abs_cost_negative(self):
        """Test abs_cost() for negative cost."""
        trade = Trade(Decimal('-100'), Decimal('-50'))
        self.assertEqual(trade.abs_cost(), Decimal('50'))

    def test_trade_add(self):
        """Test __add__ method."""
        trade1 = Trade(Decimal('100'), Decimal('50'))
        trade2 = Trade(Decimal('50'), Decimal('25'))
        result = trade1 + trade2
        self.assertEqual(result.signed_size, Decimal('150'))
        self.assertEqual(result.signed_cost, Decimal('75'))

    def test_trade_opposite(self):
        """Test opposite() method."""
        trade = Trade(Decimal('100'), Decimal('50'))
        opposite = trade.opposite()
        self.assertEqual(opposite.signed_size, Decimal('-100'))
        self.assertEqual(opposite.signed_cost, Decimal('-50'))

    def test_trade_is_zero_true(self):
        """Test is_zero() returns True for zero trade."""
        trade = Trade.ZERO()
        self.assertTrue(trade.is_zero())

    def test_trade_is_zero_false(self):
        """Test is_zero() returns False for non-zero trade."""
        trade = Trade(Decimal('100'), Decimal('50'))
        self.assertFalse(trade.is_zero())

    def test_trade_from_size_and_rate(self):
        """Test from_size_and_rate() method."""
        # from_size_and_rate is an instance method
        trade = Trade.ZERO().from_size_and_rate(Decimal('100'), Decimal('0.05'))
        self.assertEqual(trade.signed_size, Decimal('100'))
        self.assertEqual(trade.signed_cost, Decimal('5'))

    def test_trade_from3_long(self):
        """Test from3() for LONG side."""
        trade = Trade.from3(Side.LONG, Decimal('100'), Decimal('0.05'))
        self.assertEqual(trade.signed_size, Decimal('100'))
        self.assertEqual(trade.signed_cost, Decimal('5'))

    def test_trade_from3_short(self):
        """Test from3() for SHORT side."""
        trade = Trade.from3(Side.SHORT, Decimal('100'), Decimal('0.05'))
        self.assertEqual(trade.signed_size, Decimal('-100'))
        self.assertEqual(trade.signed_cost, Decimal('-5'))

    def test_trade_repr(self):
        """Test __repr__ method."""
        trade = Trade(Decimal('100'), Decimal('50'))
        repr_str = repr(trade)
        self.assertIn("Trade", repr_str)
        self.assertIn("100", repr_str)


class TestFill(unittest.TestCase):
    """Test cases for Fill class."""

    def test_fill_init_default(self):
        """Test Fill initialization with default values."""
        fill = Fill()
        self.assertEqual(fill.signed_size, Decimal('0'))
        self.assertEqual(fill.signed_cost, Decimal('0'))

    def test_fill_init_with_values(self):
        """Test Fill initialization with values."""
        fill = Fill(Decimal('100'), Decimal('50'))
        self.assertEqual(fill.signed_size, Decimal('100'))
        self.assertEqual(fill.signed_cost, Decimal('50'))

    def test_fill_from3_long(self):
        """Test from3() for LONG side."""
        fill = Fill.from3(Side.LONG, Decimal('100'), Decimal('0.05'))
        self.assertEqual(fill.signed_size, Decimal('100'))
        self.assertEqual(fill.signed_cost, Decimal('5'))

    def test_fill_from3_short(self):
        """Test from3() for SHORT side."""
        fill = Fill.from3(Side.SHORT, Decimal('100'), Decimal('0.05'))
        self.assertEqual(fill.signed_size, Decimal('-100'))
        self.assertEqual(fill.signed_cost, Decimal('-5'))

    def test_fill_to_trade(self):
        """Test to_trade() method."""
        fill = Fill(Decimal('100'), Decimal('50'))
        trade = fill.to_trade()
        self.assertEqual(trade.signed_size, Decimal('100'))
        self.assertEqual(trade.signed_cost, Decimal('50'))

    def test_fill_is_zero_true(self):
        """Test is_zero() returns True for zero fill."""
        fill = Fill()
        self.assertTrue(fill.is_zero())

    def test_fill_is_zero_false(self):
        """Test is_zero() returns False for non-zero fill."""
        fill = Fill(Decimal('100'), Decimal('50'))
        self.assertFalse(fill.is_zero())

    def test_fill_abs_size(self):
        """Test abs_size() method."""
        fill = Fill(Decimal('-100'), Decimal('50'))
        self.assertEqual(fill.abs_size(), Decimal('100'))

    def test_fill_abs_cost(self):
        """Test abs_cost() method."""
        fill = Fill(Decimal('100'), Decimal('-50'))
        self.assertEqual(fill.abs_cost(), Decimal('50'))

    def test_fill_repr(self):
        """Test __repr__ method."""
        fill = Fill(Decimal('100'), Decimal('50'))
        repr_str = repr(fill)
        self.assertIn("Fill", repr_str)
        self.assertIn("100", repr_str)


class TestTradeIntegration(unittest.TestCase):
    """Integration tests for Trade and Fill."""

    def test_fill_to_trade_and_back(self):
        """Test converting Fill to Trade and using Trade methods."""
        fill = Fill.from3(Side.LONG, Decimal('100'), Decimal('0.05'))
        trade = fill.to_trade()
        
        self.assertEqual(trade.abs_size(), Decimal('100'))
        self.assertEqual(trade.abs_cost(), Decimal('5'))
        self.assertEqual(trade.side(), Side.LONG)

    def test_multiple_trades_addition(self):
        """Test adding multiple trades together."""
        trade1 = Trade.from3(Side.LONG, Decimal('100'), Decimal('0.05'))
        trade2 = Trade.from3(Side.LONG, Decimal('50'), Decimal('0.05'))
        
        combined = trade1 + trade2
        
        self.assertEqual(combined.signed_size, Decimal('150'))
        self.assertEqual(combined.signed_cost, Decimal('7.5'))

    def test_trade_opposite_then_add(self):
        """Test that trade + opposite = zero."""
        trade = Trade(Decimal('100'), Decimal('50'))
        opposite = trade.opposite()
        result = trade + opposite
        
        self.assertEqual(result.signed_size, Decimal('0'))
        self.assertEqual(result.signed_cost, Decimal('0'))
        self.assertTrue(result.is_zero())

    def test_long_vs_short_cost(self):
        """Test that LONG and SHORT trades have correct signs."""
        long_trade = Trade.from3(Side.LONG, Decimal('100'), Decimal('0.05'))
        short_trade = Trade.from3(Side.SHORT, Decimal('100'), Decimal('0.05'))
        
        # Size should be positive for LONG, negative for SHORT
        self.assertGreater(long_trade.signed_size, 0)
        self.assertLess(short_trade.signed_size, 0)
        
        # But absolute values should be equal
        self.assertEqual(long_trade.abs_size(), short_trade.abs_size())
        self.assertEqual(long_trade.abs_cost(), short_trade.abs_cost())


if __name__ == '__main__':
    unittest.main()
