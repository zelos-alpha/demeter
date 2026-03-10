from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from enum import Enum, IntEnum


class Side(Enum):
    """Trading side: LONG or SHORT"""
    LONG = 1
    SHORT = 2


class TimeInForce(Enum):
    """Order time in force types"""
    GTC = 1  # Good Till Cancelled
    IOC = 2  # Immediate or Cancel
    FOK = 3  # Fill or Kill
    ALO = 4  # Add Liquidity Only


@dataclass
class Trade:
    """Represents a trade with size and cost"""
    signed_size: int
    signed_cost: int


@dataclass
class OrderId:
    """Order identifier"""
    value: int = 0

    def is_zero(self) -> bool:
        return self.value == 0


@dataclass
class AMMId:
    """AMM identifier"""
    value: int = 0

    def is_zero(self) -> bool:
        return self.value == 0


@dataclass
class MarketId:
    """Market identifier"""
    value: int = 0


@dataclass
class OrderReq:
    """Order request structure"""
    cross: bool
    market_id: MarketId
    amm_id: AMMId
    side: Side
    tif: TimeInForce
    size: int
    tick: int


@dataclass
class SingleOrderReq:
    """Single order request with additional parameters"""
    order: OrderReq
    enter_market: bool
    id_to_strict_cancel: OrderId
    exit_market: bool
    isolated_cash_in: int
    isolated_cash_transfer_all: bool
    desired_match_rate: int


@dataclass
class MarketAcc:
    """Represents a market account"""
    root: str
    token_id: int
    market_id: int
    is_cross: bool = False

    def is_zero(self) -> bool:
        return self.root == "0x0"


@dataclass
class SwapMathParams:
    """Parameters for swap math"""
    market: str
    user: MarketAcc
    amm: MarketAcc
    user_side: Side
    taker_fee_rate: int
    amm_otc_fee_rate: int
    amm_all_in_fee_rate: int
    tick_step: int
    n_ticks_to_try_at_once: int
    time_to_mat: int

@dataclass
class MarketId:
    """Market identifier"""
    value: int = 0


@dataclass
class TokenId:
    """Token identifier"""
    value: int = 0


@dataclass
class MarketCache:
    """Cached market data"""
    market: str
    token_id: TokenId
    maturity: int
    tick_step: int


@dataclass
class AMMId:
    """AMM identifier"""
    value: int = 0

    def is_zero(self) -> bool:
        return self.value == 0

@dataclass
class LongShort:
    """Order structure for book matching"""
    tif: TimeInForce
    side: Side
    sizes: List[int]
    ticks: List[int]


@dataclass
class CancelData:
    """Cancellation data"""
    ids: List[OrderId]
    is_all: bool
    is_strict: bool


class Stage(Enum):
    """Stage for tick sweeping"""
    LOOP_BATCH = 1
    LOOP_SINGLE = 2
    BINARY_SEARCH = 3
    FOUND_STOP = 4
    SWEPT_ALL = 5

@dataclass
class TickSweepState:
    """State for sweeping through order book ticks"""
    stage: 'Stage'
    ticks: List[int] = field(default_factory=list)
    tick_sizes: List[int] = field(default_factory=list)
    single_index: int = 0
    bin_min: int = 0
    bin_max: int = 0
    market: str = ""
    side: Side = Side.LONG
    n_ticks_to_try_at_once: int = 5


@dataclass
class OTCTrade:
    """Over-the-counter trade"""
    counter: MarketAcc
    trade: Trade
    cash_to_counter: int


@dataclass
class AMMState:
    """
    AMM State - Core state of the Positive AMM

    This represents the current state of the liquidity pool.

    Abstract World (Invariant calculations):
    - totalFloatAmount: Amount of floating rate liquidity (F)
    - normFixedAmount: Normalized fixed rate liquidity (N)

    Real World:
    - totalLp: Total LP tokens minted

    Market Data:
    - latestFTime: Last funding time
    - maturity: Market maturity timestamp
    - seedTime: AMM initialization time

    Config:
    - minAbsRate: Minimum allowed exchange rate
    - maxAbsRate: Maximum allowed exchange rate
    - cutOffTimestamp: Cutoff time for AMM operations
    """
    total_float_amount: int  # F - Floating rate liquidity
    norm_fixed_amount: int  # N - Normalized fixed rate liquidity
    total_lp: int  # Total LP tokens
    latest_f_time: int  # Last funding time
    maturity: int  # Market maturity timestamp
    seed_time: int  # AMM initialization time
    min_abs_rate: int  # Minimum rate (e.g., 0.01 = 1%)
    max_abs_rate: int  # Maximum rate (e.g., 10.0 = 1000%)
    cut_off_timestamp: int  # Cutoff time for AMM operations


@dataclass
class AMMSeedParams:
    """
    Parameters for seeding/initializing an AMM

    Attributes:
        min_abs_rate: Minimum allowed exchange rate
        max_abs_rate: Maximum allowed exchange rate
        cut_off_timestamp: Cutoff time for AMM operations
        initial_abs_rate: Initial exchange rate
        initial_size: Initial position size
        flip_liquidity: Initial liquidity buffer
        initial_cash: Initial cash deposited
    """
    min_abs_rate: int
    max_abs_rate: int
    cut_off_timestamp: int
    initial_abs_rate: int
    initial_size: int
    flip_liquidity: int
    initial_cash: int


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


class OrderStatus(IntEnum):
    NOT_EXIST = 0
    OPEN = 1
    PENDING_SETTLE = 2
    PURGED = 3


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

    ZERO = None  # Will be set after class definition

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


NodeData.ZERO = NodeData


class TickMatchResult:
    """Result of a match operation."""

    def __init__(self):
        self.partial_size: int = 0
        self.partial_maker_nonce: int = 0
        self.begin_fully_filled_order_index: int = 0
        self.end_fully_filled_order_index: int = 0


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


