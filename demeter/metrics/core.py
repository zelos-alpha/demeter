from typing import Dict

from decimal import Decimal

from ._typing import MetricEnum
from .calculator import *

DECIMAL_1 = Decimal(1)


def performance_metrics(
    values: pd.Series, annualized_risk_free_rate=0.03, benchmark: pd.Series | None = None
) -> Dict[MetricEnum, Decimal]:
    """
    Calculate all performance metrics
    :param values: value's you need to calculate,
    :param annualized_risk_free_rate: annualized risk_free rate
    :param benchmark: benchmark, if set to None, some metrics depends on this will not be calculated
    :return: a dict with metric enum and their value.
    """
    values = values.apply(lambda x: float(x))
    init = values.iloc[0]
    final = values.iloc[-1]

    start = values.index[0]
    start1 = values.index[1]
    interval = start1 - start
    interval_in_day = interval.value / 1e9 / 86400
    end = values.index[len(values) - 1]
    duration_in_day = (end - start + interval).value / 1e9 / 86400

    if benchmark is not None:
        benchmark = benchmark.apply(lambda x: float(x))
        alpha, beta = alpha_beta(values, benchmark)
    else:
        alpha, beta = np.nan, np.nan

    returns = values.pct_change().dropna()
    metric_map = {
        MetricEnum.return_value: return_value(init, final),
        MetricEnum.return_rate: return_rate(init, final),
        MetricEnum.annualized_return: annualized_return(duration_in_day, init, final),
        MetricEnum.max_draw_down: max_draw_down(values),
        MetricEnum.sharpe_ratio: sharpe_ratio(interval_in_day, values, annualized_risk_free_rate),
        MetricEnum.volatility: volatility(returns, duration_in_day),
        MetricEnum.alpha: alpha,
        MetricEnum.beta: beta,
    }
    return {k: Decimal(v) for k, v in metric_map.items()}
