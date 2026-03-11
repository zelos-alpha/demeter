import numpy as np
import pandas as pd
from demeter import DemeterError


def return_value(init_equity: float, final_equity: float) -> float:
    """
    Get return rate

    :param init_equity: init equity
    :param final_equity: final equity
    :return: return value
    """
    return final_equity - init_equity


def return_rate(init_equity: float, final_equity: float) -> float:
    """
    rate of return, if init_equity is 0, will return np.inf

    :param init_equity: init equity
    :param final_equity: final equity
    :return: return rate
    """
    return final_equity / init_equity - 1 if init_equity > 0 else np.inf


def return_multiple(net_value: pd.Series) -> pd.Series:
    """
    get return multiple, value(t) / value(t-1), if there are nan/inf values, it will be set to 1

    :param net_value: list of values
    :return: return multiple
    """
    return (net_value / net_value.shift(1)).fillna(1).replace([np.inf, -np.inf], 1)


def return_rate_series(net_value: pd.Series) -> pd.Series:
    """
    calculate return rate of a net value series, (value(t) - value(t-1)) / value(t-1),
    if there are nan/inf values, it will be set to 0.

    :param net_value: list of values
    :return: return rate list
    """
    return net_value.pct_change().fillna(0).replace([np.inf, -np.inf], 0)


def annualized_return(
    duration_in_day: float,
    init_value: float = None,
    final_value: float = None,
    return_rates: pd.Series = None,
    net_values: pd.Series = None,
    interest_type="compound",
) -> float:
    """
    | Annualizing an asset's return rate. you can choose one way to calculate
    | * initial value and final value
    | * return rate list
    | * net value list

    :param duration_in_day: days between initial time and final time
    :param init_value: initial value
    :param final_value: final value
    :param return_rates: a list of return rate
    :param net_values: a list of net value
    :param interest_type: interest type, can be "single" or "compound", default is compound
    :return: annualized return value:
    """

    if interest_type == "single":
        if init_value is not None and final_value is not None:
            return ((final_value - init_value) / init_value) / (duration_in_day / 365)
        elif net_values is not None:
            return (net_values.iloc[-1] - net_values.iloc[0]) / net_values.iloc[0] / (duration_in_day / 365)
        elif return_rates is not None:
            raise DemeterError("single interest series should not exist, it should be compound")
        else:
            raise DemeterError("Choose one to calculate: initial and final value/return rate/net value")
    elif interest_type == "compound":
        if init_value is not None and final_value is not None:
            return (final_value / init_value) ** (365 / duration_in_day) - 1
        elif net_values is not None:
            return_rates = return_multiple(net_values)
            return return_rates.prod() ** (365 / duration_in_day) - 1
        elif return_rates is not None:
            return (return_rates + 1).prod() ** (365 / duration_in_day) - 1
        else:
            raise DemeterError("Choose one to calculate: initial and final value/return rate/net value")


def max_draw_down_benchmark(value: pd.Series):
    """
    Calculate the maximum drawdown based on its definition.
    This method is computationally intensive and is used for comparing results with max_draw_down.

    :param value: value to calculate
    :type value: pd.Series
    """
    value.index = range(len(value.index))  # restruct index to access faster
    result = 0
    for index, row in value.iteritems():
        current_max = value[index:].apply(lambda nv: 1 - nv / row).max()
        if current_max > result:
            result = current_max
    return result


def max_draw_down(net_value: pd.Series):
    """
    Get max draw down in a fast algorithm.

    :param net_value: value to calculate
    :type net_value:  pd.Series
    """
    max_value, idx_h, idx_l = _withdraw_with_high_low(net_value.to_list())
    return (net_value.iloc[idx_h] - net_value.iloc[idx_l]) / net_value.iloc[idx_h]


def _withdraw_with_high_low(arr: list):
    """
    from : https://blog.csdn.net/Spade_/article/details/112341428
    """

    # Given an array, return the maximum drawdown and the corresponding indices of the highest and lowest points.
    _dp = 0  # Let _dp[i] represent the maximum drawdown ending at index i.
    i_high = 0  # During iteration, the index of the highest point within the range from 0 to i - 1.

    # Global maximum drawdown and the corresponding highest and lowest point indices, noting that indices are meant.
    g_withdraw, g_high, g_low = -np.inf, -1, -1

    for i in range(1, len(arr)):
        # If the highest point within the range from 0 to i - 1 is less than the current point...
        if arr[i_high] < arr[i - 1]:
            i_high = i - 1  # ...the index of the highest point within the range from 0 to i - 1
        _dp = arr[i_high] - arr[i]  # ...then _dp[i] is updated to represent the maximum drawdown ending at index i.
        if _dp > g_withdraw:  # Find the new maximum drawdown and update the three values:
            g_withdraw = _dp
            g_high = i_high
            g_low = i

    return g_withdraw, g_high, g_low


def volatility(returns: pd.Series, interval_in_day):
    """
    Calculate volatility, The number of trading days is 365 instead of 252.

    :param interval_in_day: Daily data interval.
    :param returns: list of values
    :return: volatility value
    """
    return returns.std() * np.sqrt(365 / interval_in_day)


def sharpe_ratio(interval_in_day: float, duration_in_day: int, values: pd.Series, annualized_risk_free_rate: float):
    """
    Calculate sharpe ratio. The number of trading days is 365 instead of 252.

    :param interval_in_day: Daily data interval.
    :param duration_in_day: days between initial time and final time
    :param values: list of values
    :param annualized_risk_free_rate: annualized risk free rate
    :return: sharpe ratio
    """

    returns = (values / values.shift(1)).dropna()

    mean_yearly_return = annualized_return(duration_in_day, return_rates=returns - 1)
    std_yearly_return = volatility(returns, interval_in_day)

    result = (mean_yearly_return - annualized_risk_free_rate) / std_yearly_return

    return result


def alpha_beta(values: pd.Series, benchmark: pd.Series, duration_in_day: int):
    """
    Calculate alpha and beta

    :param values: list of values
    :param benchmark: benchmark
    :param duration_in_day: days between initial time and final time

    :return: alpha and beta
    """
    portfolio_returns = (values / values.shift(1)).dropna()
    benchmark_returns = (benchmark / benchmark.shift(1)).dropna()

    cov = np.cov(portfolio_returns, benchmark_returns)
    beta = cov[0, 1] / cov[1, 1]

    portfolio_apy = annualized_return(duration_in_day, return_rates=portfolio_returns - 1)
    benchmark_apy = annualized_return(duration_in_day, return_rates=benchmark_returns - 1)

    alpha = portfolio_apy - beta * benchmark_apy

    return alpha, beta
