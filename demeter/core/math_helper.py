import warnings
from decimal import Decimal

import pandas as pd


def annualized_returns(init_value, final_value, timespan_in_day):
    """
    calculated for a period of a year's data

    :param init_value:  Net value in the beginning
    :param final_value: Net value in the end
    :param timespan_in_day: time span, unit is day
    """
    return (final_value / init_value) ** Decimal(365 / timespan_in_day) - 1


def get_benchmark_returns(
    init_value: Decimal,
    init_price: pd.Series,
    final_price: pd.Series,
    timespan_in_day: Decimal,
)->Decimal:
    """
    Annualized benchmark return rate

    algorithm: swap token balance to 1:1, and hold those get_position to the end.

    :param init_value: total net value in the beginning
    :type init_value: Decimal
    :param init_price: price in the beginning, price should contain two items, base price and quote price
    :type init_price: Series
    :param final_price: Price in the end, price should contain two items, base price and quote price
    :type final_price: Series
    :param timespan_in_day: time span, unit is day
    :type timespan_in_day: Decimal
    :return: benchmark return
    :rtype: Decimal
    """
    splited_value = init_value / len(init_price)

    amounts = []
    for price in init_price:
        amounts.append(splited_value / price)
    final_value = 0
    i = 0
    for price in final_price:
        final_value += amounts[i] * price
        i += 1
    return (final_value / init_value) ** Decimal(365 / timespan_in_day) - 1


def __devide_value_to_50_50(net_value, price):
    """
    divide base/quote token value to 50:50 by according to price

    :param net_value: Decimal or float
    :param price: quote token price
    """
    base_amount = net_value / 2
    quote_amount = (net_value - base_amount) / price
    return base_amount, quote_amount


def max_draw_down(value: pd.Series):
    """
    Get max draw down

    :param value: value to calculate
    :type value: pd.Series
    """
    warnings.warn("use max_draw_down_fast instead", DeprecationWarning)
    value.index = range(len(value.index))  # restruct index to access faster
    result = 0
    for index, row in value.iteritems():
        current_max = value[index:].apply(lambda nv: 1 - nv / row).max()
        if current_max > result:
            result = current_max
    return result


def max_draw_down_fast(value: pd.Series):
    """
    Get max draw down in a fast algorithm.

    :param value: value to calculate
    :type value:  pd.Series
    """
    max_value, idx_h, idx_l = _withdraw_with_high_low(value.to_list())
    return (value.iloc[idx_h] - value.iloc[idx_l]) / value.iloc[idx_h]


def _withdraw_with_high_low(arr: list):
    """
    from : https://blog.csdn.net/Spade_/article/details/112341428
    """

    # Given an array, return the maximum drawdown and the corresponding indices of the highest and lowest points.
    _dp = 0  # Let _dp[i] represent the maximum drawdown ending at index i.
    i_high = 0  # During iteration, the index of the highest point within the range from 0 to i - 1.

    # Global maximum drawdown and the corresponding highest and lowest point indices, noting that indices are meant.
    g_withdraw, g_high, g_low = float("-inf"), -1, -1

    for i in range(1, len(arr)):
        if arr[i_high] < arr[i - 1]:  # 若 0 ~ i - 1 中最高的点小于当前点
            i_high = i - 1  # 0 ~ i - 1 中最高的点的索引

        _dp = arr[i_high] - arr[i]  # _dp 表示 i 点的最大回撤
        if _dp > g_withdraw:  # 找到新的最大回撤，更新三个值
            g_withdraw = _dp
            g_high = i_high
            g_low = i

    return g_withdraw, g_high, g_low
