import pandas as pd
from pandas import Timedelta

from .._typing import DemeterError, TimeUnitEnum


def get_real_n(data: pd.Series, n=5, unit=TimeUnitEnum.hour):
    if data.size < 2:
        raise DemeterError("not enough data for simple_moving_average")
    timespan: Timedelta = data.index[1] - data.index[0]
    if timespan.seconds % 60 != 0:
        return DemeterError("no seconds is allowed")
    span_in_minute = timespan.total_seconds() / 60
    if unit.value % span_in_minute != 0:
        raise DemeterError(f"ma span is {n}{unit.name}, but data span is {span_in_minute}minute, cannot divide exactly")
    real_n = n * int(unit.value / span_in_minute)
    if data.size < real_n:
        raise DemeterError("not enough data for simple_moving_average")
    return real_n
