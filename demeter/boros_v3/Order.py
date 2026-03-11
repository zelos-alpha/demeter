from enum import IntEnum
from typing import Tuple, List


class TimeInForce(IntEnum):
    """
    Time in force - determines how long an order remains active

    - GTC (Good Till Cancel): Order remains active until cancelled
    - IOC (Immediate Or Cancel): Must be immediately filled or cancelled
    - FOK (Fill Or Kill): Must be fully filled immediately or cancelled
    - ALO (Aggressive Limit Order): Aggressive execution at limit price
    - SOFT_ALO: Soft ALO - removes matchable orders without filling
    """
    GTC = 0
    IOC = 1
    FOK = 2
    ALO = 3
    SOFT_ALO = 4

    def is_alo(self) -> bool:
        """Check if TimeInForce is ALO or SOFT_ALO"""
        return self == TimeInForce.ALO or self == TimeInForce.SOFT_ALO

    def should_skip_matchable_orders(self) -> bool:
        """Check if should skip matchable orders (for SOFT_ALO)

        SOFT_ALO orders only remove matchable counter orders without actually filling them.
        """
        return self == TimeInForce.SOFT_ALO


class OrderStatus(IntEnum):
    """
    Status of an order in the order book

    - NOT_EXIST: Order never existed or was removed
    - OPEN: Order is active and unfilled
    - PENDING_SETTLE: Order is filled, pending settlement
    - PURGED: Order was purged due to being out of bounds
    """
    NOT_EXIST = 0
    OPEN = 1
    PENDING_SETTLE = 2
    PURGED = 3


class Side(IntEnum):
    """
    Trade side - either LONG or SHORT

    - LONG: Buy/Long position
    - SHORT: Sell/Short position
    """
    LONG = 0
    SHORT = 1

    def opposite(self) -> 'Side':
        """Get the opposite side

        Returns:
            Side.SHORT if LONG, Side.LONG if SHORT
        """
        return Side.SHORT if self == Side.LONG else Side.LONG

    def sweep_tick_top_down(self) -> bool:
        """Check if ticks should be swept top down

        LONG side sweeps from highest tick to lowest.
        SHORT side sweeps from lowest tick to highest.

        Returns:
            True for LONG, False for SHORT
        """
        return self == Side.LONG

    def end_tick(self) -> int:
        """Get the end tick for this side

        Returns:
            -32768 (INT16_MIN) for LONG
            32767 (INT16_MAX) for SHORT
        """
        return -32768 if self == Side.LONG else 32767

    def possible_to_be_filled(self, order_tick: int, last_tick_filled: int) -> bool:
        """Check if an order is possible to be filled

        Args:
            order_tick: The tick of the order
            last_tick_filled: The last tick that was filled

        Returns:
            True if the order can potentially be filled
        """
        if self.sweep_tick_top_down():
            return last_tick_filled <= order_tick
        else:
            return last_tick_filled >= order_tick

    def tick_to_get_first_avail(self) -> int:
        """Special tick value for getting first available tick

        Returns the stop tick, which is the tick before the very first possible tick
        due to wrap-around logic.

        Returns:
            end_tick for this side
        """
        return self.end_tick()

    def can_match(self, limit_tick: int, best_tick: int) -> bool:
        """Check if an order can match with the current best tick

        For LONG orders:
            - limitTick <= bestTick (buy at limit price or better)

        For SHORT orders:
            - limitTick >= bestTick (sell at limit price or better)

        Args:
            limit_tick: The limit price tick of the order
            best_tick: The best available tick on the opposite side

        Returns:
            True if the order can match
        """
        if self.sweep_tick_top_down():
            return limit_tick <= best_tick
        else:
            return limit_tick >= best_tick

    def to_signed_size(self, size: int) -> int:
        """Convert unsigned size to signed based on side

        Args:
            size: The unsigned size

        Returns:
            Positive size for LONG, negative for SHORT
        """
        return size if self == Side.LONG else -size

    def is_of_side(self, size: int) -> bool:
        """Check if size matches the side

        Args:
            size: Signed size value

        Returns:
            True if size is positive and side is LONG, or size is negative and side is SHORT
        """
        return (size > 0 and self == Side.LONG) or (size < 0 and self == Side.SHORT)

    def check_rate_in_bound(self, rate: int, bound: int) -> bool:
        """Check if rate is within the specified bound

        For LONG: rate <= bound
        For SHORT: rate >= bound

        Args:
            rate: The rate to check
            bound: The boundary rate

        Returns:
            True if rate is within bounds
        """
        if self == Side.LONG:
            return rate <= bound
        else:
            return rate >= bound


class OrderId:
    """
    Order Identifier

    Packs side, tick index, and order index into a single 64-bit value.

    Layout (from highest bits):
    - 1 bit: INITIALIZED_MARKER (0x8000000000000000)
    - 7 bits: Unused
    - 1 bit: Side (0=LONG, 1=SHORT)
    - 16 bits: Encoded tick index
    - 40 bits: Order index

    The encoding ensures that for orders of the same side,
    lower unwrapped values have higher priority in the order book.
    """

    INITIALIZED_MARKER = 1 << 63

    def __init__(self, value: int = 0):
        """Initialize OrderId with value"""
        self._value = value

    @classmethod
    def ZERO(cls):
        return cls(0)

    @property
    def value(self) -> int:
        """Get the underlying value"""
        return self._value

    @staticmethod
    def from_(side: Side, tick_index: int, order_index: int) -> 'OrderId':
        """Create OrderId from components

        Args:
            side: The side (LONG or SHORT)
            tick_index: The tick index (-32768 to 32767)
            order_index: The order index (0 to 2^40-1)

        Returns:
            Packed OrderId
        """
        encoded_tick = OrderId._encode_tick_index(tick_index, side)

        packed = int(side)
        packed = (packed << 16) | (encoded_tick & 0xFFFF)
        packed = (packed << 40) | (order_index & 0xFFFFFFFFFF)
        packed |= OrderId.INITIALIZED_MARKER

        return OrderId(packed)

    def unpack(self) -> Tuple[Side, int, int]:
        """Unpack OrderId into components

        Returns:
            Tuple of (side, tick_index, order_index)
        """
        packed = self._value

        order_index = packed & 0xFFFFFFFFFF
        packed >>= 40

        encoded_tick = packed & 0xFFFF
        packed >>= 16

        side_bit = packed & 1

        tick_index = OrderId._decode_tick_index(encoded_tick, Side(side_bit))

        return (Side(side_bit), tick_index, order_index)

    def is_zero(self) -> bool:
        """Check if OrderId is zero

        Returns:
            True if value is 0
        """
        return self._value == 0

    def order_index(self) -> int:
        """Get order index from OrderId

        Returns:
            Order index
        """
        return self._value & 0xFFFFFFFFFF

    def tick_index(self) -> int:
        """Get tick index from OrderId

        Returns:
            Tick index
        """
        encoded_tick = (self._value >> 40) & 0xFFFF
        side = self.side()
        return OrderId._decode_tick_index(encoded_tick, side)

    def side(self) -> Side:
        """Get side from OrderId

        Returns:
            Side (LONG or SHORT)
        """
        side_bit = (self._value >> 56) & 1
        return Side(side_bit)

    def __lt__(self, other: 'OrderId') -> bool:
        """Compare two OrderIds

        Returns:
            True if self.value < other.value
        """
        return self._value < other._value

    def __eq__(self, other: 'OrderId') -> bool:
        """Compare two OrderIds for equality"""
        if not isinstance(other, OrderId):
            return False
        return self._value == other._value

    def __repr__(self) -> str:
        """String representation"""
        return f"OrderId({self._value})"

    @staticmethod
    def _encode_tick_index(tick_index: int, side: Side) -> int:
        """Encode tick index based on side

        Args:
            tick_index: The tick index to encode
            side: The side for encoding

        Returns:
            Encoded tick index
        """
        encoded = (tick_index & 0xFFFF) ^ (1 << 15)
        if side.sweep_tick_top_down():
            encoded = (~encoded) & 0xFFFF
        return encoded

    @staticmethod
    def _decode_tick_index(encoded: int, side: Side) -> int:
        """Decode tick index based on side

        Args:
            encoded: The encoded tick index
            side: The side for decoding

        Returns:
            Decoded tick index
        """
        if side.sweep_tick_top_down():
            encoded = (~encoded) & 0xFFFF
        tick_index = encoded ^ (1 << 15)

        # Handle sign extension
        if tick_index >= 0x8000:
            tick_index -= 0x10000

        return tick_index


class OrderIdArrayLib:
    """Library for OrderId array operations"""

    @staticmethod
    def remove_zeroes_and_update_best_same_side(ids: List[OrderId]) -> None:
        """Remove zero OrderIds and update best same side

        Removes all zero-valued OrderIds from the array and updates
        the best (lowest) order ID to be at the end of the array.

        Args:
            ids: List of OrderIds to process (modified in place)
        """
        length = len(ids)
        if length == 0:
            return

        # Remove zeroes by swapping with elements from the end
        i = 0
        while i < length:
            if ids[i].is_zero():
                # Find next non-zero from end
                while length > i and ids[length - 1].is_zero():
                    length -= 1
                if length > i:
                    ids[i] = ids[length - 1]
                    length -= 1
            else:
                i += 1

        # Truncate array
        del ids[length:]

        # Update best same side
        OrderIdArrayLib.update_best_same_side(ids, 0)

    @staticmethod
    def update_best_same_side(ids: List[OrderId], pre_len: int) -> None:
        """Update best (lowest) order ID to be at the end

        Finds the order with the lowest value and moves it to the end
        of the array (position len - 1).

        Args:
            ids: List of OrderIds to process (modified in place)
            pre_len: Number of elements at the start that should be skipped
        """
        length = len(ids)
        if length == 0:
            return

        # Initialize best with first relevant element
        best_pos = pre_len
        best_id = ids[pre_len] if pre_len < length else OrderId.ZERO

        # Find the lowest order ID
        for i in range(pre_len, length):
            cur_id = ids[i]
            if best_id.is_zero() or cur_id < best_id:
                best_pos = i
                best_id = cur_id

        # Swap best with last element
        if best_pos != length - 1:
            ids[best_pos], ids[length - 1] = ids[length - 1], ids[best_pos]

    @staticmethod
    def extend(arr: List[OrderId], n: int) -> List[OrderId]:
        """Extend array by n elements"""
        for _ in range(n):
            arr.append(OrderId.ZERO)
        return arr

    @staticmethod
    def concat(arr1: List[OrderId], arr2: List[OrderId]) -> List[OrderId]:
        """Concatenate two arrays"""
        return arr1 + arr2

    @staticmethod
    def set_shorter_length(arr: List[OrderId], length: int) -> None:
        """Set array to shorter length"""
        del arr[length:]
