"""
Order Types Python Implementation
Based on contracts/types/Order.sol
"""

from enum import IntEnum
from typing import Tuple


class TimeInForce(IntEnum):
    """Time in force options for orders."""
    GTC = 0  # Good Till Cancelled
    IOC = 1  # Immediate or Cancel
    FOK = 2  # Fill or Kill
    ALO = 3  # Aggressive Limit Order
    SOFT_ALO = 4  # Soft Aggressive Limit Order


class OrderStatus(IntEnum):
    """Order status enumeration."""
    NOT_EXIST = 0  # Order does not exist
    OPEN = 1  # Order is open/active
    PENDING_SETTLE = 2  # Order pending settlement
    PURGED = 3  # Order has been purged


class Side(IntEnum):
    """Order side enumeration."""
    LONG = 0  # Buy order
    SHORT = 1  # Sell order


class TimeInForceLib:
    """Library for TimeInForce operations."""
    
    @staticmethod
    def is_alo(tif: TimeInForce) -> bool:
        """Check if order is ALO (Aggressive Limit Order) or SOFT_ALO."""
        return tif == TimeInForce.ALO or tif == TimeInForce.SOFT_ALO
    
    @staticmethod
    def should_skip_matchable_orders(tif: TimeInForce) -> bool:
        """Check if should skip matchable orders (only for SOFT_ALO)."""
        return tif == TimeInForce.SOFT_ALO


class SideLib:
    """Library for Side operations."""
    
    @staticmethod
    def opposite(side: Side) -> Side:
        """Get the opposite side."""
        return Side.SHORT if side == Side.LONG else Side.LONG
    
    @staticmethod
    def sweep_tick_top_down(side: Side) -> bool:
        """Check if side sweeps tick top-down (LONG)."""
        return side == Side.LONG
    
    @staticmethod
    def end_tick(side: Side) -> int:
        """Get the end tick for a side."""
        import sys
        if side == Side.LONG:
            return -2**15  # int16 min
        else:
            return 2**15 - 1  # int16 max
    
    @staticmethod
    def possible_to_be_filled(side: Side, order_tick: int, last_tick_filled: int) -> bool:
        """Check if order can be filled based on tick comparison."""
        if SideLib.sweep_tick_top_down(side):
            return last_tick_filled <= order_tick
        else:
            return last_tick_filled >= order_tick
    
    @staticmethod
    def tick_to_get_first_avail(side: Side) -> int:
        """Get the stop tick (tick before the first possible tick)."""
        return SideLib.end_tick(side)
    
    @staticmethod
    def can_match(side: Side, limit_tick: int, best_tick: int) -> bool:
        """
        Check if order can match with best tick.
        LONG: limitTick <= bestTick (buy price <= ask)
        SHORT: limitTick >= bestTick (sell price >= bid)
        """
        if SideLib.sweep_tick_top_down(side):
            return limit_tick <= best_tick
        else:
            return limit_tick >= best_tick
    
    @staticmethod
    def to_signed_size(size: int, side: Side) -> int:
        """Convert size to signed value based on side."""
        if side == Side.LONG:
            return size
        else:
            return -size
    
    @staticmethod
    def is_of_side(size: int, side: Side) -> bool:
        """Check if size matches side (positive for LONG, negative for SHORT)."""
        return (size > 0 and side == Side.LONG) or (size < 0 and side == Side.SHORT)
    
    @staticmethod
    def check_rate_in_bound(side: Side, rate: int, bound: int) -> bool:
        """Check if rate is within bound for side."""
        if side == Side.LONG:
            return rate <= bound
        else:
            return rate >= bound


class OrderIdLib:
    """Library for OrderId operations."""
    
    ZERO = 0
    INITIALIZED_MARKER = 1 << 63
    
    @staticmethod
    def from_order(side: Side, tick_index: int, order_index: int) -> int:
        """
        Create OrderId from side, tick index, and order index.
        Encodes the order ID with special bit manipulation.
        """
        encoded_tick = OrderIdLib._encode_tick_index(tick_index, side)
        
        packed = 0
        packed |= int(side)
        packed = (packed << 16) | encoded_tick
        packed = (packed << 40) | order_index
        packed |= OrderIdLib.INITIALIZED_MARKER
        
        return packed
    
    @staticmethod
    def unpack(order_id: int) -> Tuple[Side, int, int]:
        """
        Unpack OrderId into (side, tickIndex, orderIndex).
        """
        packed = order_id
        
        order_index = packed & ((1 << 40) - 1)
        packed >>= 40
        
        encoded_tick = packed & ((1 << 16) - 1)
        packed >>= 16
        
        side = Side(packed & 1)
        
        tick_index = OrderIdLib._decode_tick_index(encoded_tick, side)
        
        return (side, tick_index, order_index)
    
    @staticmethod
    def is_zero(order_id: int) -> bool:
        """Check if OrderId is zero."""
        return order_id == 0
    
    @staticmethod
    def order_index(order_id: int) -> int:
        """Get order index from OrderId."""
        return order_id & ((1 << 40) - 1)
    
    @staticmethod
    def tick_index(order_id: int) -> int:
        """Get tick index from OrderId."""
        encoded_tick = (order_id >> 40) & ((1 << 16) - 1)
        side = OrderIdLib.side(order_id)
        return OrderIdLib._decode_tick_index(encoded_tick, side)
    
    @staticmethod
    def side(order_id: int) -> Side:
        """Get side from OrderId."""
        return Side((order_id >> 56) & 1)
    
    @staticmethod
    def _encode_tick_index(tick_index: int, side: Side) -> int:
        """Encode tick index for OrderId."""
        encoded = tick_index & 0xFFFF
        encoded ^= (1 << 15)
        if SideLib.sweep_tick_top_down(side):
            encoded = ~encoded & 0xFFFF
        return encoded
    
    @staticmethod
    def _decode_tick_index(encoded: int, side: Side) -> int:
        """Decode tick index from OrderId."""
        if SideLib.sweep_tick_top_down(side):
            encoded = ~encoded & 0xFFFF
        return encoded ^ (1 << 15)
    
    @staticmethod
    def lt_order_id(u: int, v: int) -> bool:
        """Check if OrderId u < OrderId v (by unwrapped value)."""
        return u < v


class OrderIdArrayLib:
    """Library for OrderId array operations."""
    
    @staticmethod
    def remove_zeroes_and_update_best_same_side(ids: list) -> None:
        """
        Remove zero OrderIds from array and update best same side.
        Modifies the array in place.
        """
        length = len(ids)
        if length == 0:
            return
        
        i = 0
        while i < length:
            while i < length and OrderIdLib.is_zero(ids[i]):
                ids[i] = ids[length - 1]
                length -= 1
            i += 1
        
        # Truncate array to new length
        del ids[length:]
        
        # Update best same side
        OrderIdArrayLib.update_best_same_side(ids, 0)
    
    @staticmethod
    def update_best_same_side(ids: list, pre_len: int) -> None:
        """
        Update best OrderId in the array (after preLen).
        The best OrderId (lowest) is moved to the end of the processed portion.
        """
        length = len(ids)
        if length == 0:
            return
        
        best_pos = 0
        best_id = 0
        
        if pre_len > 0:
            best_id = ids[pre_len - 1]
            best_pos = pre_len - 1
        
        for i in range(pre_len, length):
            cur_id = ids[i]
            # Find the minimum order id
            if OrderIdLib.is_zero(best_id) or OrderIdLib.lt_order_id(cur_id, best_id):
                best_pos = i
                best_id = cur_id
        
        # Swap best with last element (to keep minimum at end)
        ids[best_pos], ids[length - 1] = ids[length - 1], ids[best_pos]
