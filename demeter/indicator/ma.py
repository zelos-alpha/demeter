from datetime import timedelta

import numpy as np
import pandas as pd
from pandas._typing import TimedeltaConvertibleTypes, Axis

from .common import get_real_n


def simple_moving_average(data: pd.Series | pd.DataFrame,
                          window: timedelta = timedelta(hours=5),
                          min_periods: int | None = None,
                          center: bool = False,
                          win_type: str | None = None,
                          on: str | None = None,
                          axis: Axis = 0,
                          closed: str | None = None,
                          method: str = "single",
                          ) -> pd.Series:
    """
    calculate simple moving average, Note: window is based on time span

    docs for other params, see https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.rolling.html

    :param data: data
    :type data: Series
    :param window: window width
    :type window: timedelta
    :return: simple moving average data
    :rtype: Series

    """

    return data.rolling(window=get_real_n(data, window),
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
