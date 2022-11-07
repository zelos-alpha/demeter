import numpy as np
import pandas as pd
from pandas import Timedelta
from pandas._typing import TimedeltaConvertibleTypes, Axis

from .._typing import ZelosError, TimeUnitEnum


def get_real_n(data: pd.Series, n=5, unit=TimeUnitEnum.hour):
    if data.size < 2:
        raise ZelosError("not enough data for simple_moving_average")
    timespan: Timedelta = data.index[1] - data.index[0]
    if timespan.seconds % 60 != 0:
        return ZelosError("no seconds is allowed")
    span_in_minute = timespan.total_seconds() / 60
    if unit.value % span_in_minute != 0:
        raise ZelosError(f"ma span is {n}{unit.name}, but data span is {span_in_minute}minute, cannot divide exactly")
    real_n = n * int(unit.value / span_in_minute)
    if data.size < real_n:
        raise ZelosError("not enough data for simple_moving_average")
    return real_n


def simple_moving_average(data: pd.Series | pd.DataFrame,
                          n=5,
                          unit=TimeUnitEnum.hour,
                          min_periods: int | None = None,
                          center: bool = False,
                          win_type: str | None = None,
                          on: str | None = None,
                          axis: Axis = 0,
                          closed: str | None = None,
                          method: str = "single",
                          ) -> pd.Series:
    """
    calculate simple moving average, this function will help you get window size from time and unit

    docs for other params, see https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.rolling.html

    :param data: data
    :type data: Series
    :param n: window width, should set along with unit, eg: 5 hour, 2 minute
    :type n: int
    :param unit: unit of n, can be minute,hour,day
    :type unit: TimeUnitEnum
    :return: simple moving average data
    :rtype: Series

    """

    return data.rolling(window=get_real_n(data, n, unit),
                        min_periods=min_periods,
                        center=center,
                        win_type=win_type,
                        on=on,
                        axis=axis,
                        closed=closed,
                        method=method,
                        ).mean()


def exponential_moving_average(data: pd.Series | pd.DataFrame,
                               com: float | None = None,
                               span: float | None = None,
                               halflife: float | TimedeltaConvertibleTypes | None = None,
                               alpha: float | None = None,
                               min_periods: int | None = 0,
                               adjust: bool = True,
                               ignore_na: bool = False,
                               axis: Axis = 0,
                               times: str | np.ndarray | pd.DataFrame | pd.Series | None = None,
                               method: str = "single",
                               ):
    """
    calculate exponential moving average, just a shortcut for pandas.evm().mean()

     docs for params, see: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.ewm.html

    """
    return data.ewm(com=com,
                    span=span,
                    halflife=halflife,
                    alpha=alpha,
                    min_periods=min_periods,
                    adjust=adjust,
                    ignore_na=ignore_na,
                    axis=axis,
                    times=times,
                    method=method,
                    ).mean()
