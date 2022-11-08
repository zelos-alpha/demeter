from decimal import Decimal

import pandas as pd

from demeter import TimeUnitEnum, DemeterError
from .common import get_real_n


def actual_volatility(data: pd.Series,
                      n: int = 5,
                      unit: TimeUnitEnum = TimeUnitEnum.hour) -> "Series(float64)":
    """
    get actual volatility. step:

    1. get window size according to n and unit
    2. get return rate according to window size
    3. calculate standard deviation for each data point, form current point p[n] to previous point p[n - window_size].

    note:
    1. the first window_size * 2 - 1 data will be NAN
    2. volatility is based on time window. not monthly or annually

    :param data: data to process
    :type data: Series
    :param n: time length
    :type n: int
    :param unit: time unit
    :type unit: TimeUnitEnum
    """
    real_n = get_real_n(data, n, unit)

    if real_n * 2 - 1 >= len(data.index):
        raise DemeterError(f"data length is {len(data.index)}, but window size is {real_n}, "
                           f"data length should be greater than {real_n * 2 - 1} to avoid all NAN")

    shifted = data.shift(periods=real_n, fill_value=Decimal(float("nan")))
    return_rate = data.div(shifted).apply(Decimal.ln)
    column = return_rate.rolling(window=real_n).std()

    return column
