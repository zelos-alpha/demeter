from datetime import timedelta

import pandas as pd
from pandas import Timedelta

from .._typing import DemeterError


def get_real_n(data: pd.Series, window: timedelta):
    if data.size < 2:
        raise DemeterError("not enough data for simple_moving_average")
    timespan: Timedelta = data.index[1] - data.index[0]
    if timespan.seconds % 60 != 0:
        return DemeterError("no seconds is allowed")
    data_span_in_minute = timespan.total_seconds() / 60
    window_minutes = int(window.total_seconds()) // 60
    if window_minutes % data_span_in_minute != 0:
        raise DemeterError(f"window span is {window_minutes}minutes, "
                           f"but data span is {data_span_in_minute}minute, cannot divide exactly")
    real_n = window_minutes // int(data_span_in_minute)
    if data.size < real_n:
        raise DemeterError("not enough data for simple_moving_average")
    return real_n
