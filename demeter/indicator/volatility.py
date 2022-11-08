from datetime import timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import math

from demeter import DemeterError
from .common import get_real_n


def actual_volatility(data: pd.Series,
                      window: timedelta = timedelta(minutes=5),
                      timeunit: timedelta = timedelta(days=1)) -> "Series(float64)":
    """
    get actual volatility. step:

    1. get window size according to n and unit
    2. get return rate according to window size
    3. calculate standard deviation for each data point, form current point p[n] to previous point p[n - window_size].

    note:
    1. the first window_size * 2 - 1 data will be NAN

    :param data: data to process
    :type data: Series
    :param window: window width
    :type window: timedelta
    :param timeunit: time unit for volatility, default is one day
    :type timeunit: timedelta
    """
    real_n = get_real_n(data, window)

    if real_n * 2 - 1 >= len(data.index):
        raise DemeterError(f"data length is {len(data.index)}, but window size is {real_n}, "
                           f"data length should be greater than {real_n * 2 - 1} to avoid all NAN")

    if data.dtypes == "object":
        shifted = data.shift(periods=real_n, fill_value=Decimal(float("nan")))
        return_rate = data.div(shifted).apply(Decimal.ln)
    else:
        shifted = data.shift(periods=real_n)
        return_rate = data.div(shifted).apply(np.log)

    volatility_column: pd.Series = return_rate.rolling(window=real_n).std()
    amp = math.sqrt(timeunit.total_seconds() / window.total_seconds())
    return volatility_column * amp
