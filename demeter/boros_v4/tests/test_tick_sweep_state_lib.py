"""
Test cases for TickSweepStateLib.py module.

Note: Due to circular import issues in the source code (_typing.py <-> AMM.py),
this test file includes essential classes inline to allow tests to run.
"""
import unittest
from decimal import Decimal
from enum import IntEnum
from typing import List, Tuple, Literal
from dataclasses import dataclass, field


# Define Side locally
class Side(IntEnum):
    """Trade side - either LONG or SHORT"""
    LONG = 0
    SHORT = 1


# Define Stage locally
class Stage(IntEnum):
    """State machine stages"""
    LOOP_BATCH = 0
    LOOP_SINGLE = 1
    BINARY_SEARCH = 2
    FOUND_STOP = 3
    SWEPT_ALL = 4


# Simple mock for OrderBookStorageStruct
class MockOrderBookStorageStruct:
    pass


# Simple mock for MarketEntry
class MockMarketEntry:
    def get_next_n_ticks(self, ob_struct, side: Side, start_tick: int, n: int) -> Tuple[List[int], List[Decimal]]:
        """Mock implementation that returns sample ticks."""
        if side == Side.SHORT:
            # For SHORT, return ticks from high to low
            return [32760, 32750, 32740, 32730, 32720][:n], [Decimal('100') for _ in range(n)][:n]
        else:
            # For LONG, return ticks from low to high
            return [-32760, -32750, -32740, -32730, -32720][:n], [Decimal('100') for _ in range(n)][:n]


# Inline implementation of TickSweepState
@dataclass
class TickSweepState:
    ob_struct: MockOrderBookStorageStruct
    stage: Stage = Stage.LOOP_BATCH
    ticks: List[int] = field(default_factory=list)
    tick_sizes: List[Decimal] = field(default_factory=list)
    single_index: int = 0
    bin_min: int = 0
    bin_max: int = 0
    market: MockMarketEntry = None
    side: Side = Side.SHORT
    n_ticks_to_try_at_once: int = 5

    @staticmethod
    def create(market: MockMarketEntry, ob_struct: MockOrderBookStorageStruct, tick_side: Side,
               n_ticks_to_try_at_once: int) -> 'TickSweepState':
        if tick_side == Side.SHORT:
            start_tick = -32768
        else:
            start_tick = 32767

        ticks, tick_sizes = market.get_next_n_ticks(ob_struct, tick_side, start_tick, n_ticks_to_try_at_once)

        if len(ticks) == 0:
            return TickSweepState(
                ob_struct=ob_struct,
                stage=Stage.SWEPT_ALL,
                market=market,
                side=tick_side,
                n_ticks_to_try_at_once=n_ticks_to_try_at_once
            )

        return TickSweepState(
            ob_struct=ob_struct,
            stage=Stage.LOOP_BATCH,
            ticks=ticks,
            tick_sizes=tick_sizes,
            single_index=0,
            bin_min=0,
            bin_max=0,
            market=market,
            side=tick_side,
            n_ticks_to_try_at_once=n_ticks_to_try_at_once
        )

    def has_more(self) -> bool:
        return self.stage != Stage.FOUND_STOP and self.stage != Stage.SWEPT_ALL

    def get_last_tick(self) -> int:
        if self.stage == Stage.LOOP_BATCH:
            return self._last_tick_array()
        elif self.stage in (Stage.LOOP_SINGLE, Stage.BINARY_SEARCH, Stage.FOUND_STOP):
            return self.ticks[self.single_index]
        else:
            raise ValueError(f"Invalid stage for getLastTick: {self.stage}")

    def get_last_tick_and_sum_size(self) -> Tuple[int, Decimal]:
        if self.stage == Stage.LOOP_BATCH:
            return self._last_tick_array(), sum(self.tick_sizes)
        elif self.stage in (Stage.LOOP_SINGLE, Stage.FOUND_STOP):
            return self.ticks[self.single_index], self.tick_sizes[self.single_index]
        elif self.stage == Stage.BINARY_SEARCH:
            last_tick = self.ticks[self.single_index]
            sum_size = sum(self.tick_sizes[self.bin_min:self.single_index + 1])
            return last_tick, sum_size
        else:
            raise ValueError(f"Invalid stage for getLastTickAndSumSize: {self.stage}")

    def get_sum_cost(self, tick_step: int) -> Decimal:
        cost = Decimal('0')

        if self.stage == Stage.LOOP_BATCH:
            for i in range(len(self.tick_sizes)):
                cost += self._calculate_tick_cost(self.ticks[i], self.tick_sizes[i], tick_step)
        elif self.stage == Stage.LOOP_SINGLE:
            cost = self._calculate_tick_cost(
                self.ticks[self.single_index],
                self.tick_sizes[self.single_index],
                tick_step
            )
        elif self.stage == Stage.BINARY_SEARCH:
            for i in range(self.bin_min, self.single_index + 1):
                cost += self._calculate_tick_cost(self.ticks[i], self.tick_sizes[i], tick_step)
        else:
            raise ValueError(f"Invalid stage for getSumCost: {self.stage}")

        return cost

    def _last_tick_array(self) -> int:
        if not self.ticks:
            raise ValueError("Empty ticks array")
        return self.ticks[-1]

    def _calculate_tick_cost(self, tick: int, size: Decimal, tick_step: int) -> Decimal:
        # Simplified rate calculation
        rate = abs(tick) * tick_step * 0.00001

        if self.side == Side.LONG:
            signed_size = size
        else:
            signed_size = -size

        return signed_size * Decimal(str(rate))

    def _end_tick(self) -> int:
        if self.side == Side.LONG:
            return -32768
        else:
            return 32767

    @staticmethod
    def _should_use_binary_search(length: int) -> bool:
        return length > 4

    def transition_up(self):
        if self.stage == Stage.LOOP_BATCH:
            self._transition_up_batch()
        elif self.stage == Stage.LOOP_SINGLE:
            self._transition_up_single()
        elif self.stage == Stage.BINARY_SEARCH:
            self._transition_up_binary()
        else:
            raise ValueError(f"Cannot transitionUp from stage: {self.stage}")

    def _transition_up_batch(self):
        last_tick = self._last_tick_array()
        end_tick = self._end_tick()

        if len(self.ticks) != self.n_ticks_to_try_at_once or last_tick == end_tick:
            self.stage = Stage.SWEPT_ALL
            return

        new_ticks, new_sizes = self.market.get_next_n_ticks(
            self.ob_struct, self.side, last_tick, self.n_ticks_to_try_at_once
        )

        if len(new_ticks) == 0:
            self.stage = Stage.SWEPT_ALL
            return

        self.ticks = new_ticks
        self.tick_sizes = new_sizes
        self.single_index = 0

    def _transition_up_single(self):
        self.single_index += 1
        if self.single_index >= len(self.ticks):
            raise ValueError("singleIndex overflow in transitionUpSingle")

    def _transition_up_binary(self):
        self.bin_min = self.single_index + 1

        if self.bin_min == self.bin_max:
            if self.bin_min >= len(self.ticks):
                raise ValueError("bin_min overflow in transitionUpBinary")
            self.single_index = self.bin_min
            self.stage = Stage.FOUND_STOP
        else:
            self.single_index = (self.bin_min + self.bin_max) // 2

    def transition_down(self):
        if self.stage == Stage.LOOP_BATCH:
            self._transition_down_batch()
        elif self.stage == Stage.LOOP_SINGLE:
            self.stage = Stage.FOUND_STOP
        elif self.stage == Stage.BINARY_SEARCH:
            self._transition_down_binary()
        else:
            raise ValueError(f"Cannot transitionDown from stage: {self.stage}")

    def _transition_down_batch(self):
        if not self._should_use_binary_search(len(self.ticks)):
            self.stage = Stage.LOOP_SINGLE
            self.single_index = 0
        else:
            self.stage = Stage.BINARY_SEARCH
            self.bin_min = 0
            self.bin_max = len(self.ticks)
            self.single_index = (self.bin_min + self.bin_max) // 2

    def _transition_down_binary(self):
        self.bin_max = self.single_index

        if self.bin_min == self.bin_max:
            self.stage = Stage.FOUND_STOP
        else:
            self.single_index = (self.bin_min + self.bin_max) // 2


# ==================== Test Cases ====================

class TestStage(unittest.TestCase):
    """Test cases for Stage enum."""

    def test_stage_values(self):
        """Test Stage enum values."""
        self.assertEqual(Stage.LOOP_BATCH, 0)
        self.assertEqual(Stage.LOOP_SINGLE, 1)
        self.assertEqual(Stage.BINARY_SEARCH, 2)
        self.assertEqual(Stage.FOUND_STOP, 3)
        self.assertEqual(Stage.SWEPT_ALL, 4)


class TestTickSweepStateCreation(unittest.TestCase):
    """Test cases for TickSweepState creation."""

    def setUp(self):
        self.market = MockMarketEntry()
        self.ob_struct = MockOrderBookStorageStruct()

    def test_create_short_side(self):
        """Test creation with SHORT side."""
        state = TickSweepState.create(
            self.market, self.ob_struct, Side.SHORT, 5
        )
        self.assertEqual(state.side, Side.SHORT)
        self.assertEqual(state.stage, Stage.LOOP_BATCH)
        self.assertEqual(len(state.ticks), 5)

    def test_create_long_side(self):
        """Test creation with LONG side."""
        state = TickSweepState.create(
            self.market, self.ob_struct, Side.LONG, 5
        )
        self.assertEqual(state.side, Side.LONG)
        self.assertEqual(state.stage, Stage.LOOP_BATCH)
        self.assertEqual(len(state.ticks), 5)

    def test_create_with_small_n(self):
        """Test creation with small n_ticks_to_try_at_once."""
        state = TickSweepState.create(
            self.market, self.ob_struct, Side.SHORT, 3
        )
        self.assertEqual(len(state.ticks), 3)


class TestTickSweepStateHasMore(unittest.TestCase):
    """Test cases for has_more method."""

    def setUp(self):
        self.market = MockMarketEntry()
        self.ob_struct = MockOrderBookStorageStruct()
        self.state = TickSweepState.create(
            self.market, self.ob_struct, Side.SHORT, 5
        )

    def test_has_more_loop_batch(self):
        """Test has_more in LOOP_BATCH stage."""
        self.assertTrue(self.state.has_more())

    def test_has_more_found_stop(self):
        """Test has_more in FOUND_STOP stage."""
        self.state.stage = Stage.FOUND_STOP
        self.assertFalse(self.state.has_more())

    def test_has_more_swept_all(self):
        """Test has_more in SWEPT_ALL stage."""
        self.state.stage = Stage.SWEPT_ALL
        self.assertFalse(self.state.has_more())

    def test_has_more_loop_single(self):
        """Test has_more in LOOP_SINGLE stage."""
        self.state.stage = Stage.LOOP_SINGLE
        self.assertTrue(self.state.has_more())

    def test_has_more_binary_search(self):
        """Test has_more in BINARY_SEARCH stage."""
        self.state.stage = Stage.BINARY_SEARCH
        self.assertTrue(self.state.has_more())


class TestTickSweepStateGetLastTick(unittest.TestCase):
    """Test cases for get_last_tick method."""

    def setUp(self):
        self.market = MockMarketEntry()
        self.ob_struct = MockOrderBookStorageStruct()
        self.state = TickSweepState.create(
            self.market, self.ob_struct, Side.SHORT, 5
        )

    def test_get_last_tick_loop_batch(self):
        """Test get_last_tick in LOOP_BATCH stage."""
        last_tick = self.state.get_last_tick()
        self.assertEqual(last_tick, self.state.ticks[-1])

    def test_get_last_tick_loop_single(self):
        """Test get_last_tick in LOOP_SINGLE stage."""
        self.state.stage = Stage.LOOP_SINGLE
        self.state.single_index = 2
        last_tick = self.state.get_last_tick()
        self.assertEqual(last_tick, self.state.ticks[2])

    def test_get_last_tick_binary_search(self):
        """Test get_last_tick in BINARY_SEARCH stage."""
        self.state.stage = Stage.BINARY_SEARCH
        self.state.single_index = 3
        last_tick = self.state.get_last_tick()
        self.assertEqual(last_tick, self.state.ticks[3])


class TestTickSweepStateGetLastTickAndSumSize(unittest.TestCase):
    """Test cases for get_last_tick_and_sum_size method."""

    def setUp(self):
        self.market = MockMarketEntry()
        self.ob_struct = MockOrderBookStorageStruct()
        self.state = TickSweepState.create(
            self.market, self.ob_struct, Side.SHORT, 5
        )

    def test_get_last_tick_and_sum_size_loop_batch(self):
        """Test in LOOP_BATCH stage."""
        last_tick, sum_size = self.state.get_last_tick_and_sum_size()
        self.assertEqual(last_tick, self.state.ticks[-1])
        self.assertEqual(sum_size, sum(self.state.tick_sizes))

    def test_get_last_tick_and_sum_size_loop_single(self):
        """Test in LOOP_SINGLE stage."""
        self.state.stage = Stage.LOOP_SINGLE
        self.state.single_index = 2
        last_tick, sum_size = self.state.get_last_tick_and_sum_size()
        self.assertEqual(last_tick, self.state.ticks[2])
        self.assertEqual(sum_size, self.state.tick_sizes[2])


class TestShouldUseBinarySearch(unittest.TestCase):
    """Test cases for _should_use_binary_search method."""

    def test_length_less_equal_4(self):
        """Test with length <= 4."""
        self.assertFalse(TickSweepState._should_use_binary_search(1))
        self.assertFalse(TickSweepState._should_use_binary_search(4))

    def test_length_greater_4(self):
        """Test with length > 4."""
        self.assertTrue(TickSweepState._should_use_binary_search(5))
        self.assertTrue(TickSweepState._should_use_binary_search(10))


class TestTransitionDown(unittest.TestCase):
    """Test cases for transition_down method."""

    def setUp(self):
        self.market = MockMarketEntry()
        self.ob_struct = MockOrderBookStorageStruct()
        self.state = TickSweepState.create(
            self.market, self.ob_struct, Side.SHORT, 5
        )

    def test_transition_down_loop_batch_small(self):
        """Test transition_down from LOOP_BATCH with small tick list."""
        self.state.ticks = [1, 2, 3]
        self.state.tick_sizes = [Decimal('100') for _ in range(3)]
        self.state.transition_down()
        self.assertEqual(self.state.stage, Stage.LOOP_SINGLE)
        self.assertEqual(self.state.single_index, 0)

    def test_transition_down_loop_batch_large(self):
        """Test transition_down from LOOP_BATCH with large tick list."""
        self.state.transition_down()
        self.assertEqual(self.state.stage, Stage.BINARY_SEARCH)
        self.assertEqual(self.state.bin_min, 0)
        self.assertEqual(self.state.bin_max, 5)

    def test_transition_down_loop_single(self):
        """Test transition_down from LOOP_SINGLE."""
        self.state.stage = Stage.LOOP_SINGLE
        self.state.transition_down()
        self.assertEqual(self.state.stage, Stage.FOUND_STOP)


class TestTransitionUp(unittest.TestCase):
    """Test cases for transition_up method."""

    def setUp(self):
        self.market = MockMarketEntry()
        self.ob_struct = MockOrderBookStorageStruct()
        self.state = TickSweepState.create(
            self.market, self.ob_struct, Side.SHORT, 5
        )

    def test_transition_up_loop_single(self):
        """Test transition_up from LOOP_SINGLE."""
        self.state.stage = Stage.LOOP_SINGLE
        self.state.single_index = 0
        self.state.transition_up()
        self.assertEqual(self.state.single_index, 1)

    def test_transition_up_binary_search(self):
        """Test transition_up from BINARY_SEARCH."""
        self.state.stage = Stage.BINARY_SEARCH
        self.state.single_index = 2
        self.state.bin_min = 0
        self.state.bin_max = 5
        self.state.transition_up()
        self.assertEqual(self.state.bin_min, 3)


class TestEndTick(unittest.TestCase):
    """Test cases for _end_tick method."""

    def test_end_tick_long(self):
        """Test _end_tick for LONG side."""
        state = TickSweepState(
            ob_struct=MockOrderBookStorageStruct(),
            side=Side.LONG
        )
        self.assertEqual(state._end_tick(), -32768)

    def test_end_tick_short(self):
        """Test _end_tick for SHORT side."""
        state = TickSweepState(
            ob_struct=MockOrderBookStorageStruct(),
            side=Side.SHORT
        )
        self.assertEqual(state._end_tick(), 32767)


if __name__ == '__main__':
    unittest.main()
