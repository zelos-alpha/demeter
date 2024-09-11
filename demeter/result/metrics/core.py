from typing import Dict, Any

from decimal import Decimal

from ._typing import MetricEnum
from .calculator import *

DECIMAL_1 = Decimal(1)


def performance_metrics(
    values: pd.Series, annualized_risk_free_rate=0.03, benchmark: pd.Series | None = None
) -> Dict[MetricEnum, Any]:
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
        alpha, beta = alpha_beta(values, benchmark, duration_in_day)
        benchmark_init = benchmark.iloc[0]
        benchmark_final = benchmark.iloc[-1]
        benchmark_return = return_rate(benchmark_init, benchmark_final)
        benchmark_apr = annualized_return(duration_in_day, benchmark_init, benchmark_final)
    else:
        alpha, beta, benchmark_return, benchmark_apr = np.nan, np.nan, np.nan, np.nan

    returns = values.pct_change().dropna()
    metric_map = {
        MetricEnum.start_period: values.index[0],
        MetricEnum.end_period: values.index[-1],
        MetricEnum.duration: (values.index[-1] - values.index[0]) + interval,
        MetricEnum.return_value: return_value(init, final),
        MetricEnum.return_rate: return_rate(init, final),
        MetricEnum.annualized_return: annualized_return(duration_in_day, init, final),
        MetricEnum.max_draw_down: max_draw_down(values),
        MetricEnum.sharpe_ratio: sharpe_ratio(interval_in_day, duration_in_day, values, annualized_risk_free_rate),
        MetricEnum.volatility: volatility(returns, interval_in_day),
        MetricEnum.alpha: alpha,
        MetricEnum.beta: beta,
        MetricEnum.benchmark_rate: benchmark_return,
        MetricEnum.annualized_benchmark_rate: benchmark_apr,
    }
    return {k: v for k, v in metric_map.items()}


def round_results(val_dict: Dict[MetricEnum, Any], decimal: int = 3):
    return {k: round(v, decimal) if isinstance(v, (int, float, complex, Decimal)) else v for k, v in val_dict.items()}
