"""
Trade Types Python Implementation
Based on contracts/types/Trade.sol
"""

from typing import Tuple
from order import Side
from pmath import PMath


class TradeUndesiredSideError(Exception):
    """Raised when trade side doesn't match expected side."""
    pass


class TradeUndesiredRateError(Exception):
    """Raised when trade rate doesn't match expected rate."""
    pass


class TradeLib:
    """Library for Trade operations.
    
    Trade packs: size(128) | cost(128) into 256 bits.
    Signed values: positive for LONG, negative for SHORT.
    """
    
    ZERO = 0
    
    @staticmethod
    def from_signed_values(signed_size: int, signed_cost: int) -> int:
        """
        Create Trade from signed size and signed cost.
        """
        return TradeLib.from_128(signed_size, signed_cost)
    
    @staticmethod
    def from_128(signed_size: int, signed_cost: int) -> int:
        """
        Create Trade from int128 signed size and cost.
        """
        # Convert to uint128 representation
        raw_signed_size = signed_size & ((1 << 128) - 1)
        raw_signed_cost = signed_cost & ((1 << 128) - 1)
        
        # Pack: size << 128 | cost
        return (raw_signed_size << 128) | raw_signed_cost
    
    @staticmethod
    def unpack(trade: int) -> Tuple[int, int]:
        """
        Unpack Trade into (signedSize, signedCost).
        Returns int128 values.
        """
        raw = trade
        
        # Extract high 128 bits (size) and low 128 bits (cost)
        signed_size = raw >> 128
        signed_cost = raw & ((1 << 128) - 1)
        
        # Convert to int128
        if signed_size & (1 << 127):
            signed_size = signed_size - (1 << 128)
        
        if signed_cost & (1 << 127):
            signed_cost = signed_cost - (1 << 128)
        
        return (signed_size, signed_cost)
    
    @staticmethod
    def side(trade: int) -> Side:
        """
        Get side from trade based on signed size.
        Positive = LONG, Negative = SHORT.
        """
        signed_size = TradeLib.signed_size(trade)
        return Side.LONG if signed_size > 0 else Side.SHORT
    
    @staticmethod
    def signed_size(trade: int) -> int:
        """
        Get signed size (int128) from trade.
        """
        raw = trade >> 128
        # Convert to int128
        if raw & (1 << 127):
            raw = raw - (1 << 128)
        return raw
    
    @staticmethod
    def abs_size(trade: int) -> int:
        """
        Get absolute size (uint128) from trade.
        """
        return abs(TradeLib.signed_size(trade))
    
    @staticmethod
    def signed_cost(trade: int) -> int:
        """
        Get signed cost (int128) from trade.
        """
        raw = trade & ((1 << 128) - 1)
        # Convert to int128
        if raw & (1 << 127):
            raw = raw - (1 << 128)
        return raw
    
    @staticmethod
    def abs_cost(trade: int) -> int:
        """
        Get absolute cost (uint128) from trade.
        """
        return abs(TradeLib.signed_cost(trade))
    
    @staticmethod
    def add(trade_a: int, trade_b: int) -> int:
        """
        Add two trades together.
        """
        size_a, cost_a = TradeLib.unpack(trade_a)
        size_b, cost_b = TradeLib.unpack(trade_b)
        
        new_size = size_a + size_b
        new_cost = cost_a + cost_b
        
        return TradeLib.from_128(new_size, new_cost)
    
    @staticmethod
    def opposite(trade: int) -> int:
        """
        Get opposite trade (negate both size and cost).
        """
        size, cost = TradeLib.unpack(trade)
        return TradeLib.from_128(-size, -cost)
    
    @staticmethod
    def is_zero(trade: int) -> bool:
        """Check if trade is zero."""
        return trade == 0
    
    @staticmethod
    def from_size_and_rate(signed_size: int, rate: int) -> int:
        """
        Create Trade from signed size and rate.
        cost = size * rate (mulDown)
        """
        cost = PMath.mul_down(signed_size, rate)
        return TradeLib.from_signed_values(signed_size, cost)
    
    @staticmethod
    def from_three(side: Side, size: int, rate: int) -> int:
        """
        Create Trade from side, size, and rate.
        For LONG: size and cost are positive.
        For SHORT: size and cost are negative.
        """
        signed_size = size & ((1 << 128) - 1)
        signed_cost = PMath.mul_down(signed_size, rate)
        
        if side == Side.LONG:
            return TradeLib.from_128(signed_size, signed_cost)
        else:
            return TradeLib.from_128(-signed_size, -signed_cost)
    
    @staticmethod
    def require_desired_side_and_rate(trade: int, expected_side: Side, desired_rate: int) -> None:
        """
        Verify trade has expected side and rate.
        Raises TradeUndesiredSideError or TradeUndesiredRateError if not.
        """
        signed_size = TradeLib.signed_size(trade)
        
        if signed_size != 0:
            actual_side = TradeLib.side(trade)
            if actual_side != expected_side:
                raise TradeUndesiredSideError(f"Trade side {actual_side} != expected {expected_side}")
        
        TradeLib.require_desired_rate(trade, desired_rate)
    
    @staticmethod
    def require_desired_rate(trade: int, desired_rate: int) -> None:
        """
        Verify trade cost is within expected rate.
        Raises TradeUndesiredRateError if cost exceeds max allowed.
        """
        signed_size = TradeLib.signed_size(trade)
        signed_cost = TradeLib.signed_cost(trade)
        
        # maxCost = size * rate (mulDown)
        max_cost = PMath.mul_down(signed_size, desired_rate)
        
        if signed_cost > max_cost:
            raise TradeUndesiredRateError(f"Trade cost {signed_cost} > max allowed {max_cost}")


class FillLib:
    """Library for Fill operations.
    
    Fill is similar to Trade but represents a fill in a single tick.
    Can be fully cast to Trade.
    """
    
    ZERO = 0
    
    @staticmethod
    def to_trade(fill: int) -> int:
        """
        Convert Fill to Trade.
        Fill is directly castable to Trade (same format).
        """
        return fill
    
    @staticmethod
    def from_three(side: Side, size: int, rate: int) -> int:
        """
        Create Fill from side, size, and rate.
        """
        return FillLib.to_trade(TradeLib.from_three(side, size, rate))
    
    @staticmethod
    def is_zero(fill: int) -> bool:
        """Check if fill is zero."""
        return fill == 0
    
    @staticmethod
    def side(fill: int) -> Side:
        """Get side from fill."""
        return FillLib.to_trade(fill).side()
    
    @staticmethod
    def abs_size(fill: int) -> int:
        """Get absolute size from fill."""
        return FillLib.to_trade(fill).abs_size()
    
    @staticmethod
    def abs_cost(fill: int) -> int:
        """Get absolute cost from fill."""
        return FillLib.to_trade(fill).abs_cost()
