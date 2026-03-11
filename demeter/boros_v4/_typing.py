from dataclasses import dataclass, field
from decimal import Decimal
from enum import IntEnum
from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from .AMM import AMM
    from .Trade import Trade


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

    def to_signed_size(self, size: Decimal) -> Decimal:
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


@dataclass
class OrderId:
    pass  # todo


@dataclass
class OrderReq:
    amm: "AMM"
    side: Side
    tif: TimeInForce
    size: Decimal
    tick: int


@dataclass
class SingleOrderReq:
    order: OrderReq
    id_to_strict_cancel: OrderId  # todo

@dataclass
class SwapMathParams:
    user_side: Side
    taker_fee_rate: Decimal
    amm_otc_fee_rate: Decimal
    amm_all_in_fee_rate: Decimal
    tick_step: int
    n_ticks_to_try_at_once: int
    time_to_mat: int

@dataclass
class LongShort:
    tif: TimeInForce = TimeInForce.GTC
    side: Side = Side.LONG
    sizes: List[Decimal] = field(default_factory=list)
    limit_ticks: List[int] = field(default_factory=list)

    def is_empty(self) -> bool:
        """检查订单是否为空"""
        return len(self.sizes) == 0


@dataclass
class CancelData:
    ids: List[OrderId] = field(default_factory=list)
    is_all: bool = False
    is_strict: bool = False


class OrdersLib:
    @staticmethod
    def create_orders(
            side: Side,
            tif: TimeInForce,
            size: Decimal,
            limit_tick: int
    ) -> LongShort:
        if size == 0:
            return LongShort()

        return LongShort(
            tif=tif,
            side=side,
            sizes=[size],
            limit_ticks=[limit_tick]
        )

    @staticmethod
    def create_orders_from_size(
            tif: TimeInForce,
            size: Decimal,
            limit_tick: int
    ) -> LongShort:
        if size == 0:
            return LongShort()

            # 根据size正负判断方向
        side = Side.LONG if size > 0 else Side.SHORT

        # 取绝对值作为数量
        abs_size = abs(size)

        return LongShort(
            tif=tif,
            side=side,
            sizes=[abs_size],
            limit_ticks=[limit_tick]
        )

    @staticmethod
    def create_cancel(
            id_to_cancel: OrderId,
            is_strict: bool
    ) -> CancelData:
        if id_to_cancel.is_zero():
            return CancelData.empty()

        return CancelData(
            ids=[id_to_cancel],
            is_all=False,
            is_strict=is_strict
        )

    @staticmethod
    def is_empty(orders: LongShort) -> bool:
        return orders.is_empty()


class Stage(IntEnum):
    """
    状态机阶段

    LOOP_BATCH    - 批量扫描多个tick (初始阶段)
    LOOP_SINGLE   - 逐个tick扫描 (数据量小时使用)
    BINARY_SEARCH - 二分查找 (数据量大时使用)
    FOUND_STOP    - 找到最优停止点
    SWEPT_ALL     - 扫描完所有可交易tick
    """
    LOOP_BATCH = 0
    LOOP_SINGLE = 1
    BINARY_SEARCH = 2
    FOUND_STOP = 3
    SWEPT_ALL = 4



@dataclass
class OTCTrade:
    trade: "Trade"
    cash_to_counter: Decimal


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
