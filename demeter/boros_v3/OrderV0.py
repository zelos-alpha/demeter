from enum import IntEnum
from typing import Tuple
from dataclasses import dataclass


class TimeInForce(IntEnum):
    GTC = 0
    IOC = 1
    FOK = 2
    ALO = 3
    SOFT_ALO = 4


class TimeInForceLib:
    @staticmethod
    def is_alo(tif: TimeInForce) -> bool:
        return tif == TimeInForce.ALO or tif == TimeInForce.SOFT_ALO

    @staticmethod
    def should_skip_matchable_orders(tif: TimeInForce) -> bool:
        return tif == TimeInForce.SOFT_ALO


class Side(IntEnum):
    LONG = 0
    SHORT = 1


class SideLib:
    @staticmethod
    def opposite(side: Side) -> Side:
        return Side.SHORT if side == Side.LONG else Side.LONG

    @staticmethod
    def sweep_tick_top_down(side: Side) -> bool:
        return side == Side.LONG

    @staticmethod
    def end_tick(side: Side) -> int:
        if side == Side.LONG:
            return -2 ** 15  # int16 min -32768
        else:
            return 2 ** 15 - 1  # int16 max 32767

    @staticmethod
    def possible_to_be_filled(side: Side, order_tick: int, last_tick_filled: int) -> bool:
        if SideLib.sweep_tick_top_down(side):
            return last_tick_filled <= order_tick
        else:
            return last_tick_filled >= order_tick

    @staticmethod
    def tick_to_get_first_avail(side: Side) -> int:
        return SideLib.end_tick(side)

    @staticmethod
    def can_match(side: Side, limit_tick: int, best_tick: int) -> bool:
        if SideLib.sweep_tick_top_down(side):
            return limit_tick <= best_tick
        else:
            return limit_tick >= best_tick

    @staticmethod
    def to_signed_size(size: int, side: Side) -> int:
        if side == Side.LONG:
            return size
        else:
            return -size

    @staticmethod
    def is_of_side(size: int, side: Side) -> bool:
        return (size > 0 and side == Side.LONG) or (size < 0 and side == Side.SHORT)

    @staticmethod
    def check_rate_in_bound(side: Side, rate: int, bound: int) -> bool:
        if side == Side.LONG:
            return rate <= bound
        else:
            return rate >= bound


class OrderStatus(IntEnum):
    NOT_EXIST = 0  # Order does not exist
    OPEN = 1  # Order is open/active
    PENDING_SETTLE = 2  # Order pending settlement
    PURGED = 3  # Order has been purged


@dataclass
class OrderId:
    value: int

    def __int__(self) -> int:
        return self.value

    @classmethod
    def _from(cls, side: Side, tick_index: int, order_index: int) -> 'OrderId':
        return cls(OrderIdLib.from_(side, tick_index, order_index))

    def unpack(self) -> Tuple[Side, int, int]:
        return OrderIdLib.unpack(self.value)

    def is_zero(self) -> bool:
        return OrderIdLib.is_zero(self.value)

    def order_index(self) -> int:
        return OrderIdLib.order_index(self.value)

    def tick_index(self) -> int:
        return OrderIdLib.tick_index(self.value)

    def side(self) -> Side:
        return OrderIdLib.side(self.value)

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other):
        return self.value > other.value

    def __eq__(self, other):
        return self.value == other.value


class OrderIdLib:
    ZERO = 0
    INITIALIZED_MARKER = 1 << 63

    @staticmethod
    def from_(side: Side, tick_index: int, order_index: int) -> int:
        encoded_tick = OrderIdLib._encode_tick_index(tick_index, side)

        packed = 0
        packed |= int(side)
        packed = (packed << 16) | encoded_tick
        packed = (packed << 40) | order_index
        packed |= OrderIdLib.INITIALIZED_MARKER

        return packed

    @staticmethod
    def unpack(order_id: int) -> Tuple[Side, int, int]:
        packed = order_id
        order_index = packed & ((1 << 40) - 1)
        packed >>= 40
        encoded_tick = packed & ((1 << 16) - 1)
        packed >>= 16
        side = Side(packed & 1)
        tick_index = OrderIdLib._decode_tick_index(encoded_tick, side)
        return side, tick_index, order_index

    @staticmethod
    def is_zero(order_id: int) -> bool:
        return order_id == 0

    @staticmethod
    def order_index(order_id: int) -> int:
        return order_id & ((1 << 40) - 1)

    @staticmethod
    def tick_index(order_id: int) -> int:
        encoded_tick = (order_id >> 40) & ((1 << 16) - 1)
        side = OrderIdLib.side(order_id)
        return OrderIdLib._decode_tick_index(encoded_tick, side)

    @staticmethod
    def side(order_id: int) -> Side:
        return Side((order_id >> 56) & 1)

    @staticmethod
    def _encode_tick_index(tick_index: int, side: Side) -> int:
        encoded = tick_index & 0xFFFF
        encoded ^= (1 << 15)
        if SideLib.sweep_tick_top_down(side):
            encoded = ~encoded & 0xFFFF
        return encoded

    @staticmethod
    def _decode_tick_index(encoded: int, side: Side) -> int:
        if SideLib.sweep_tick_top_down(side):
            encoded = ~encoded & 0xFFFF
        return encoded ^ (1 << 15)

    @staticmethod
    def lt_order_id(u: int, v: int) -> bool:
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


if __name__ == '__main__':
    order_id_ = OrderId(9258838983431946245)
    print(order_id_.side())
    print(order_id_.unpack())
    print(OrderId(0).is_zero())
    print(OrderId(0) < OrderId(1))
    print(OrderId(2) < OrderId(1))
