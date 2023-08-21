from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from .. import MarketDict
from .._typing import DemeterError
from ..broker import RowData


def to_minute(time: datetime) -> datetime:
    """
    second with 0 datetime
    :param time:
    :return:
    """
    return datetime(time.year, time.month, time.day, time.hour, time.minute)


"""
Note: in current version, all the market data should have the same index, which means the same timestamp range and
 interval, so we choose timestamp in default market to trigger actions. 
"""


class Trigger:
    def __init__(self, do, *args, **kwargs):
        self._do = do if do is not None else self.do_nothing
        self.kwargs = kwargs
        self.args = args

    def when(self, row_data: MarketDict[RowData]) -> bool:
        """
        when to handler data
        :param row_data: data in row
        :return:
        """
        return False

    def do_nothing(self, row_data: MarketDict[RowData], *args, **kwargs):
        pass

    def do(self, row_data: MarketDict[RowData]):
        """
        operation to handler with row data
        :param row_data:
        :return:
        """
        return self._do(row_data, *self.args, **self.kwargs)


class AtTimeTrigger(Trigger):
    """
    trigger action at a specific time
    """

    def __init__(self, time: datetime, do, *args, **kwargs):
        self._time = to_minute(time)
        super().__init__(do, *args, **kwargs)

    def when(self, row_data: MarketDict[RowData]) -> bool:
        return row_data.default.timestamp == self._time


class AtTimesTrigger(Trigger):
    """
    trigger action at some specific time
    """

    def __init__(self, time: [datetime], do, *args, **kwargs):
        self._time = [to_minute(t) for t in time]
        super().__init__(do, *args, **kwargs)

    def when(self, row_data: MarketDict[RowData]) -> bool:
        return self._time in row_data.default.timestamp


@dataclass
class TimeRange:
    start: datetime
    end: datetime


class TimeRangeTrigger(Trigger):
    """
    trigger action at a time range
    """

    def __init__(self, time_range: TimeRange, do, *args, **kwargs):
        self._time_range = TimeRange(
            to_minute(time_range.start), to_minute(time_range.end)
        )
        super().__init__(do, *args, **kwargs)

    def when(self, row_data: MarketDict[RowData]) -> bool:
        return (
            self._time_range.start <= row_data.default.timestamp < self._time_range.end
        )


class TimeRangesTrigger(Trigger):
    """
    trigger action at some time range
    """

    def __init__(self, time_range: [TimeRange], do, *args, **kwargs):
        self._time_range: [TimeRange] = [
            TimeRange(to_minute(t.start), to_minute(t.end)) for t in time_range
        ]
        super().__init__(do, *args, **kwargs)

    def when(self, row_data: MarketDict[RowData]) -> bool:
        for r in self._time_range:
            if r.start <= row_data.default.timestamp < r.end:
                return True
        return False


def check_time_delta(delta: timedelta):
    if delta.total_seconds() % 60 != 0:
        raise DemeterError("min time span is 1 minute")


class PeriodTrigger(Trigger):
    """
    trigger period action
    """

    def __init__(
        self, time_delta: timedelta, do, trigger_immediately=False, *args, **kwargs
    ):
        self._next_match = None
        self._delta = time_delta
        self._trigger_immediately = trigger_immediately
        check_time_delta(time_delta)
        super().__init__(do, *args, **kwargs)

    def reset(self):
        self._next_match = None

    def when(self, row_data: MarketDict[RowData]) -> bool:
        if self._next_match is None:
            self._next_match = row_data.default.timestamp + self._delta
            return self._trigger_immediately

        if self._next_match == row_data.default.timestamp:
            self._next_match = self._next_match + self._delta
            return True

        return False


class PeriodsTrigger(Trigger):
    """
    trigger some period actions
    """

    def __init__(
        self, time_delta: [timedelta], do, trigger_immediately=False, *args, **kwargs
    ):
        self._next_matches = [None for _ in time_delta]
        self._deltas = time_delta
        self._trigger_immediately = trigger_immediately

        for td in time_delta:
            check_time_delta(td)
        super().__init__(do, *args, **kwargs)

    def reset(self):
        self._next_matches = [None for _ in self._deltas]

    def when(self, row_data: MarketDict[RowData]) -> bool:
        if self._next_matches[0] is None:
            self._next_matches = [row_data.default.timestamp + d for d in self._deltas]
            return self._trigger_immediately

        for i in range(len(self._deltas)):
            if self._next_matches[i] == row_data.default.timestamp:
                self._next_matches[i] = self._next_matches[i] + self._deltas[i]
                return True

        return False
