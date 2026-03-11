from enum import IntEnum
from typing import Tuple, Optional, List
from dataclasses import dataclass, field
from Order import TimeInForce, Side, OrderId


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

@dataclass
class LongShort:
    """Order input structure"""
    tif: TimeInForce = TimeInForce.GTC
    side: Side = Side.LONG
    sizes: List[int] = field(default_factory=list)
    limit_ticks: List[int] = field(default_factory=list)



@dataclass
class Trade:
    """Trade - Sum of fills across multiple ticks"""
    signed_size: int = 0
    signed_cost: int = 0

    @staticmethod
    def from3(side: Side, size: int, rate: int) -> 'Trade':
        """Create Trade from side, size and rate"""
        signed_size = size if side == Side.LONG else -size
        signed_cost = (signed_size * rate) // (10 ** 18)
        return Trade(signed_size=signed_size, signed_cost=signed_cost)

    @staticmethod
    def zero() -> 'Trade':
        """Create zero trade"""
        return Trade()

    def opposite(self) -> 'Trade':
        """Get opposite trade"""
        return Trade(signed_size=-self.signed_size, signed_cost=-self.signed_cost)

    def is_zero(self) -> bool:
        """Check if trade is zero"""
        return self.signed_size == 0 and self.signed_cost == 0

    def __add__(self, other: 'Trade') -> 'Trade':
        """Add two trades"""
        return Trade(
            signed_size=self.signed_size + other.signed_size,
            signed_cost=self.signed_cost + other.signed_cost
        )


@dataclass
class Fill:
    """Fill - Single tick fill"""
    side: Side = Side.LONG
    size: int = 0
    rate: int = 0

    @staticmethod
    def from3(side: Side, size: int, rate: int) -> 'Fill':
        """Create Fill from side, size and rate"""
        return Fill(side=side, size=size, rate=rate)

    @staticmethod
    def zero() -> 'Fill':
        """Create zero fill"""
        return Fill()

    def to_trade(self) -> Trade:
        """Convert to Trade"""
        return Trade.from3(self.side, self.size, self.rate)


@dataclass
class SweptF:
    """Swept F with FTag"""
    f_tag: int = 0
    fill: Fill = field(default_factory=Fill)

    @staticmethod
    def from3(side: Side, size: int, rate: int, f_tag: int) -> 'SweptF':
        """Create SweptF from components"""
        return SweptF(f_tag=f_tag, fill=Fill.from3(side, size, rate))


@dataclass
class CancelData:
    """Cancel data structure"""
    ids: List[OrderId] = field(default_factory=list)
    is_all: bool = False
    is_strict: bool = False


@dataclass
class MarketMem:
    """Market memory state"""
    OI: int = 0  # Open Interest
    latest_f_time: int = 0
    k_maturity: int = 0
    k_tick_step: int = 1
    taker_fee: int = 0


@dataclass
class PMData:
    """Portfolio Manager Data"""
    sum_long_size: int = 0
    sum_long_pm: int = 0
    sum_short_size: int = 0
    sum_short_pm: int = 0

    def add(self, side: Side, size: int, pm: int):
        """Add to PM data"""
        if side == Side.LONG:
            self.sum_long_size += size
            self.sum_long_pm += pm
        else:
            self.sum_short_size += size
            self.sum_short_pm += pm

    def sub(self, side: Side, size: int, pm: int):
        """Subtract from PM data"""
        if side == Side.LONG:
            self.sum_long_size -= size
            self.sum_long_pm -= pm
        else:
            self.sum_short_size -= size
            self.sum_short_pm -= pm


@dataclass
class UserMem:
    """User memory state"""
    addr: int = 0
    long_ids: List[OrderId] = field(default_factory=list)
    short_ids: List[OrderId] = field(default_factory=list)
    signed_size: int = 0
    pre_settle_size: int = 0
    pm_data: PMData = field(default_factory=PMData)


@dataclass
class MarketCtx:
    """Market context"""
    max_open_orders: int = 100
    implied_rate: int = 0
    k_tick_step: int = 1
    use_implied_as_mark_rate: bool = False
    mark_rate_oracle: int = 0
    taker_fee: int = 0


@dataclass
class MarketAcc:
    """Market account identifier - packed 26 bytes."""
    _value: int  # uint208 packed value

    def __init__(self, root: int, account_id: int, token_id: int, market_id: int):
        packed = root
        packed = (packed << 8) | account_id
        packed = (packed << 16) | token_id
        packed = (packed << 24) | market_id
        self._value = packed

    @staticmethod
    def zero() -> 'MarketAcc':
        return MarketAcc(0, 0, 0, 0)

    @staticmethod
    def from_value(value: int) -> 'MarketAcc':
        acc = MarketAcc.__new__(MarketAcc)
        acc._value = value
        return acc

    def root(self) -> int:
        return self._value >> 48

    def account_id(self) -> int:
        return (self._value >> 40) & 0xFF

    def token_id(self) -> int:
        return (self._value >> 24) & 0xFFFF

    def market_id(self) -> int:
        return self._value & 0xFFFFFF

    def is_zero(self) -> bool:
        return self._value == 0

    def is_cross(self) -> bool:
        return self.market_id() == 0xFFFFFF  # MarketIdLib.CROSS

    def value(self) -> int:
        return self._value

    def account(self) -> 'Account':  # todo update
        """Get the Account part (address + accountId)."""
        # Shift right 40 bits to get the Account (168 bits = 21 bytes)
        raw = self._value >> 40
        # Create Account from raw value
        acc = Account.__new__(Account)  # todo update
        acc._value = raw & ((1 << 168) - 1)
        return acc

    def to_cross(self) -> 'MarketAcc':
        """Convert to cross market account."""
        # Keep the upper bits and set marketId to CROSS (0xFFFFFF)
        packed = ((self._value >> 24) << 24) | 0xFFFFFF
        return MarketAcc.from_value(packed)

@dataclass
class OTCTrade:
    counter: 'MarketAcc'
    trade: 'Trade'
    cash_to_counter: int  # int256


class PayFee:
    def __init__(self, value: int = 0):
        self._value = value

    @classmethod
    def ZERO(cls):
        return cls(0)

    # @staticmethod
    # def zero() -> 'PayFee':
    #     """Create zero PayFee."""
    #     return PayFee(0)

    @staticmethod
    def from_(payment: int, fees: int) -> 'PayFee':
        return PayFee.from_int128(payment, fees)

    @staticmethod
    def from_int128(payment: int, fees: int) -> 'PayFee':
        raw_payment = payment & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        raw_fees = fees & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        return PayFee((raw_payment << 128) | raw_fees)

    def unpack(self) -> Tuple[int, int]:
        payment = int(self._value >> 128)
        fees = int(self._value & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
        # Convert to signed for payment
        if payment >= 2 ** 127:
            payment -= 2 ** 128
        return payment, fees

    def fee(self) -> int:
        """Get fees from PayFee."""
        return int(self._value & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)

    def __add__(self, other: 'PayFee') -> 'PayFee':
        payment1, fees1 = self.unpack()
        payment2, fees2 = other.unpack()
        return PayFee.from_int128(payment1 + payment2, fees1 + fees2)

    def add_fee(self, fee: int) -> 'PayFee':
        payment, fees = self.unpack()
        return PayFee.from_int128(payment, fees + fee)

    def add_payment(self, payment: int) -> 'PayFee':
        old_payment, fees = self.unpack()
        return PayFee.from_int128(old_payment + payment, fees)

    def sub_payment(self, payment: int) -> 'PayFee':
        old_payment, fees = self.unpack()
        return PayFee.from_int128(old_payment - payment, fees)

    def total(self) -> int:
        payment, fees = self.unpack()
        return payment - fees

    def __repr__(self):
        payment, fees = self.unpack()
        return f"PayFee({payment}, {fees})"


class VMResult:
    def __init__(self, value: int = 0):
        self._value = value

    @classmethod
    def ZERO(cls):
        return cls(0)

    @staticmethod
    def from_(value: int, margin: int) -> 'VMResult':
        return VMResult.from_int128(value, margin)

    @staticmethod
    def from_int128(value: int, margin: int) -> 'VMResult':
        raw_value = value & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        raw_margin = margin & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        return VMResult((raw_value << 128) | raw_margin)

    def unpack(self) -> Tuple[int, int]:
        value = int(self._value >> 128)
        margin = int(self._value & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
        # Convert to signed for value
        if value >= 2 ** 127:
            value -= 2 ** 128
        return value, margin

    def __add__(self, other: 'VMResult') -> 'VMResult':
        value1, margin1 = self.unpack()
        value2, margin2 = other.unpack()
        return VMResult.from_int128(value1 + value2, margin1 + margin2)


@dataclass
class UserResult:
    settle: PayFee
    payment: PayFee
    removed_ids: List[OrderId]
    book_matched: 'Trade'
    partial_maker: 'MarketAcc'
    partial_pay_fee: PayFee
    is_strict_im: bool
    final_vm: VMResult


@dataclass
class OTCResult:
    settle: PayFee
    payment: PayFee
    is_strict_im: bool
    final_vm: VMResult