from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Any, List

import pandas as pd

from .. import RowData
from .._typing import DemeterError


def to_minute(time: datetime) -> datetime:
    """
    Convert a datetime instance to minute(Just set its second to 0)

    :param time: time instance to convert
    :type time: datetime
    :return: time whose second is zero
    :rtype: datetime
    """
    return datetime(time.year, time.month, time.day, time.hour, time.minute)


class Trigger:
    """
    Abstract trigger.

    Trigger will do something(decide by do function) when condition is met(decide by when function)

    Extra args can be passed through kwargs. e.g. tg = Trigger(lambda r:r, extra_arg1=0, extra_arg2="1")

    :param do: which action to take.
    :type do: Callable[[RowData], Any]
    """

    def __init__(self, do: Callable[[RowData], Any], **kwargs):
        self._do = do if do is not None else lambda x: x
        self.kwargs = kwargs

    def when(self, row_data: RowData) -> bool:
        """
        If the condition is met or not.

        :param row_data: data of this iteration. used to decide to if the condition is meet.
        :type row_data: RowData
        :return: if condition is met, return true
        :rtype: bool
        """
        return False

    def do(self, row_data: RowData):
        """
        when condition is met, what actions will be taken

        :param row_data: data of this iteration
        :type row_data: condition
        :return: Anything do function returns
        :rtype: Any
        """
        return self._do(row_data, **self.kwargs)

    def is_out_date(self, t) -> bool:
        return False


class AtTimeTrigger(Trigger):
    """
    Trigger action at a specific time

    Extra args can be passed through kwargs.

    :param time: time to trigger action
    :type time: datetime
    :param do: which action to take.
    :type do: Callable[[RowData], Any]
    """

    def __init__(self, time: datetime, do, **kwargs):
        self._time = to_minute(time)
        super().__init__(do, **kwargs)

    def when(self, row_data: RowData) -> bool:
        return row_data.timestamp == self._time

    def is_out_date(self, t) -> bool:
        return t >= self._time


class AtTimesTrigger(Trigger):
    """
    trigger action at some specific times

    Extra args can be passed through kwargs.

    :param time: when current timestamp is in List[datetime], will trigger action
    :type time: List[datetime]
    :param do: which action to take.
    :type do: Callable[[RowData], Any]

    """

    def __init__(self, time: List[datetime], do, **kwargs):
        self._time = [to_minute(t) for t in time]
        super().__init__(do, **kwargs)

    def when(self, row_data: RowData) -> bool:
        return self._time in row_data.timestamp

    def is_out_date(self, t) -> bool:
        return t >= max(self._time)


@dataclass
class TimeRange:
    """
    Time range
    """

    start: datetime
    end: datetime


class TimeRangeTrigger(Trigger):
    """
    trigger action at a time range

    Extra args can be passed through kwargs. e.g. tg = Trigger(lambda r:r, extra_arg1=0, extra_arg2="1")

    :param time_range: when current timestamp is between time range, will trigger action, end time will not be included
    :type time_range: TimeRange
    :param do: which action to take.
    :type do: Callable[[RowData], Any]
    """

    def __init__(self, time_range: TimeRange, do, **kwargs):
        self._time_range = TimeRange(to_minute(time_range.start), to_minute(time_range.end))
        super().__init__(do, **kwargs)

    def when(self, row_data: RowData) -> bool:
        return self._time_range.start <= row_data.timestamp < self._time_range.end

    def is_out_date(self, t) -> bool:
        return t >= self._time_range.end


class TimeRangesTrigger(Trigger):
    """
    trigger action at some time range

    Extra args can be passed through kwargs. e.g. tg = Trigger(lambda r:r, extra_arg1=0, extra_arg2="1")

    :param time_range: when current timestamp is between any time range, will trigger action, end time will not be included
    :type time_range: List[TimeRange]
    :param do: which action to take.
    :type do: Callable[[RowData], Any]
    """

    def __init__(self, time_range: List[TimeRange], do, **kwargs):
        self._time_range: [TimeRange] = [TimeRange(to_minute(t.start), to_minute(t.end)) for t in time_range]
        super().__init__(do, **kwargs)

    def when(self, row_data: RowData) -> bool:
        for r in self._time_range:
            if r.start <= row_data.timestamp < r.end:
                return True
        return False

    def is_out_date(self, t) -> bool:
        return t >= max([x.end for x in self._time_range])


def _check_time_delta(delta: timedelta):
    if delta.total_seconds() % 60 != 0:
        raise DemeterError("min time span is 1 minute")


class PeriodTrigger(Trigger):
    """
    Trigger action periodically

    Extra args can be passed through kwargs. e.g. tg = Trigger(lambda r:r, extra_arg1=0, extra_arg2="1")

    :param time_delta: Period
    :type time_delta: timedelta
    :param do: which action to take.
    :type do: Callable[[RowData], Any]
    :param trigger_immediately: whither to trigger action when back test just started
    :type trigger_immediately: bool
    :param pending: pending time to start the trigger, can be used to trigger at specific time of a day.
    :type pending: timedelta
    """

    def __init__(self, time_delta: timedelta, do, trigger_immediately=False, pending=timedelta(minutes=0), **kwargs):
        self._next_match = None
        self._delta = time_delta
        self._trigger_immediately = trigger_immediately
        self._pending = pending
        _check_time_delta(time_delta)
        super().__init__(do, **kwargs)

    def reset(self):
        self._next_match = None

    def when(self, row_data: RowData) -> bool:
        if self._next_match is None:
            self._next_match = row_data.timestamp + self._delta + self._pending
            return self._trigger_immediately

        if self._next_match == row_data.timestamp:
            self._next_match = self._next_match + self._delta
            return True

        return False


class PeriodsTrigger(Trigger):
    """
    trigger action periodically, but you can set multiple period.

    Extra args can be passed through kwargs. e.g. tg = Trigger(lambda r:r, extra_arg1=0, extra_arg2="1")

    :param time_delta: Periods,
    :type time_delta: List[timedelta]
    :param do: which action to take.
    :type do: Callable[[RowData], Any]
    :param trigger_immediately: whither to trigger action when back test just started
    :type trigger_immediately: bool
    :param pending: pending time to start the trigger, can be used to trigger at specific time of a day.
    :type pending: timedelta
    """

    def __init__(
        self, time_delta: List[timedelta], do, trigger_immediately=False, pending=timedelta(minutes=0), **kwargs
    ):
        self._next_matches = [None for _ in time_delta]
        self._deltas = time_delta
        self._trigger_immediately = trigger_immediately
        self._pending = pending

        for td in time_delta:
            _check_time_delta(td)
        super().__init__(do, **kwargs)

    def reset(self):
        self._next_matches = [None for _ in self._deltas]

    def when(self, row_data: RowData) -> bool:
        if self._next_matches[0] is None:
            self._next_matches = [row_data.timestamp + d + self._pending for d in self._deltas]
            return self._trigger_immediately

        for i in range(len(self._deltas)):
            if self._next_matches[i] == row_data.timestamp:
                self._next_matches[i] = self._next_matches[i] + self._deltas[i]
                return True

        return False


class PriceTrigger(Trigger):
    """
    Trigger when price meet a customized condition

    Extra args can be passed through kwargs. e.g. tg = Trigger(lambda r:r, extra_arg1=0, extra_arg2="1")

    :param condition: customized condition, arg is price of tokens
    :type condition: Callable[[pd.Series], bool]
    :param do: which action to take.
    :type do: Callable[[RowData], Any]
    """

    def __init__(self, condition: Callable[[pd.Series], bool], do, **kwargs):
        self._condition = condition
        super().__init__(do, **kwargs)

    def when(self, row_data: RowData) -> bool:
        return self._condition(row_data.prices)


class CustomizedTrigger(Trigger):
    """
    Trigger on customized condition

    Extra args can be passed through kwargs. e.g. tg = Trigger(lambda r:r, extra_arg1=0, extra_arg2="1")

    :param condition: customized condition
    :type condition: Callable[[RowData], bool]
    :param do: which action to take.
    :type do: Callable[[RowData], Any]
    """

    def __init__(self, condition: Callable[[RowData], bool], do, **kwargs):
        self._condition = condition
        super().__init__(do, **kwargs)

    def when(self, row_data: RowData) -> bool:
        return self._condition(row_data)
