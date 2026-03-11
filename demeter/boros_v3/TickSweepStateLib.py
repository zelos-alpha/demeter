from ._typing import Side, List, Tuple, TickSweepState, Stage


class TickSweepStateLib:
    @staticmethod
    def create(market: str, tick_side: Side, n_ticks_to_try_at_once: int,
               mock_ticks: List[int] = None, mock_sizes: List[int] = None) -> 'TickSweepState':
        """Create a new TickSweepState"""
        if mock_ticks is None:
            mock_ticks = []
        if mock_sizes is None:
            mock_sizes = []

        if len(mock_ticks) == 0:
            return TickSweepState(stage=Stage.SWEPT_ALL)

        return TickSweepState(
            stage=Stage.LOOP_BATCH,
            ticks=mock_ticks,
            tick_sizes=mock_sizes,
            single_index=0,
            bin_min=0,
            bin_max=0,
            market=market,
            side=tick_side,
            n_ticks_to_try_at_once=n_ticks_to_try_at_once
        )

    @staticmethod
    def has_more(state: TickSweepState) -> bool:
        """Check if there are more ticks to process"""
        return state.stage != Stage.FOUND_STOP and state.stage != Stage.SWEPT_ALL

    @staticmethod
    def get_last_tick(state: TickSweepState) -> int:
        """Get the last tick being processed"""
        if state.stage == Stage.LOOP_BATCH:
            return state.ticks[-1] if state.ticks else 0
        if state.stage in (Stage.LOOP_SINGLE, Stage.BINARY_SEARCH, Stage.FOUND_STOP):
            return state.ticks[state.single_index]
        return 0

    @staticmethod
    def get_last_tick_and_sum_size(state: TickSweepState) -> Tuple[int, int]:
        """Get the last tick and sum of sizes up to that tick"""
        if state.stage == Stage.LOOP_BATCH:
            return (state.ticks[-1] if state.ticks else 0, sum(state.tick_sizes))
        if state.stage in (Stage.LOOP_SINGLE, Stage.FOUND_STOP):
            return (state.ticks[state.single_index], state.tick_sizes[state.single_index])
        if state.stage == Stage.BINARY_SEARCH:
            return (state.ticks[state.single_index],
                    sum(state.tick_sizes[state.bin_min:state.single_index + 1]))
        return (0, 0)

    @staticmethod
    def transition_up(state: TickSweepState) -> None:
        """Move to next batch/tick"""
        if state.stage == Stage.LOOP_BATCH:
            state.stage = Stage.SWEPT_ALL
        elif state.stage == Stage.LOOP_SINGLE:
            state.single_index += 1
            if state.single_index >= len(state.ticks):
                raise AssertionError("Single index out of bounds")
        elif state.stage == Stage.BINARY_SEARCH:
            state.bin_min = state.single_index + 1
            if state.bin_min == state.bin_max:
                if state.bin_min >= len(state.ticks):
                    raise AssertionError("Binary search out of bounds")
                state.single_index = state.bin_min
                state.stage = Stage.FOUND_STOP
            else:
                state.single_index = (state.bin_min + state.bin_max) // 2

    @staticmethod
    def transition_down(state: TickSweepState) -> None:
        """Narrow down search or stop"""
        if state.stage == Stage.LOOP_BATCH:
            if len(state.ticks) > 4:
                state.stage = Stage.BINARY_SEARCH
                state.bin_min = 0
                state.bin_max = len(state.ticks)
                state.single_index = (state.bin_min + state.bin_max) // 2
            else:
                state.stage = Stage.LOOP_SINGLE
                state.single_index = 0
        elif state.stage == Stage.LOOP_SINGLE:
            state.stage = Stage.FOUND_STOP
        elif state.stage == Stage.BINARY_SEARCH:
            state.bin_max = state.single_index
            if state.bin_min == state.bin_max:
                state.stage = Stage.FOUND_STOP
            else:
                state.single_index = (state.bin_min + state.bin_max) // 2
