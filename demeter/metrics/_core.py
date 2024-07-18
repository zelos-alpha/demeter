import pandas as pd
from typing import List

from demeter import AccountStatus
from demeter.metrics._typing import MetricEnum
from .calculator import *
from decimal import Decimal

DECIMAL_1 = Decimal(1)


def performance_metrics(values: pd.Series, annualized_risk_free_rate=0.03):
    values = values.apply(lambda x: float(x))
    init = values.iloc[0]
    final = values.iloc[-1]

    start = values.index[0]
    start1 = values.index[1]
    interval = start1 - start
    interval_in_day = interval.value / 1e9 / 86400
    end = values.index[len(values) - 1]
    time_range_in_day = (end - start + interval).value / 1e9 / 86400

    metric_map = {
        MetricEnum.return_value: return_value(init, final),
        MetricEnum.return_rate: return_value(init, final),
        MetricEnum.annualized_return: annualized_return(time_range_in_day, init, final),
        MetricEnum.max_draw_down: max_draw_down(values),
        MetricEnum.sharpe_ratio: sharpe_ratio(interval_in_day, values, annualized_risk_free_rate),
        MetricEnum.volatility: volatility(values, time_range_in_day),
    }
    return metric_map
