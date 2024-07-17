import numpy as np
import pandas as pd
from decimal import Decimal

from demeter import DemeterError

DECIMAL_1 = Decimal(1)


def return_value(init_equity: Decimal, final_equity: Decimal) -> Decimal:
    return final_equity - init_equity


def return_rate(init_equity: Decimal, final_equity: Decimal) -> Decimal:
    return final_equity / init_equity if init_equity > 0 else np.inf


def get_return_rate(net_value: pd.Series) -> pd.Series:
    return (net_value / net_value.shift(1)).fillna(DECIMAL_1).replace([np.inf, -np.inf], DECIMAL_1)


def annualized_return(
    timespan_in_day: float = None,
    init_value: Decimal = None,
    final_value: Decimal = None,
    return_rate: pd.Series = None,
    net_value: pd.Series = None,
    type="single",
) -> Decimal:
    """
    calculated for a period of a year's data

    :param init_value:  Net value in the beginning
    :param final_value: Net value in the end
    :param timespan_in_day: time span, unit is day
    """
    if init_value is not None and final_value is not None:
        if type == "single":
            return ((final_value - init_value) / init_value) / Decimal(timespan_in_day / 365)
        elif type == "compound":
            return (final_value / init_value) ** Decimal(365 / timespan_in_day) - 1
    else:
        if return_rate is None:
            if net_value is not None:
                return_rate = get_return_rate(net_value)
            else:
                raise DemeterError("initial and final value is None, or return rate is None")
        if type == "single":
            return (return_rate - 1).sum() / Decimal(timespan_in_day / 365)
        elif type == "compound":
            return return_rate.prod() ** Decimal(365 / timespan_in_day) - 1


def max_draw_down(value: pd.Series):
    """
    Get max draw down

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


def max_draw_down_fast(net_value: pd.Series):
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

    # 传入一个数组，返回最大回撤和对应的最高点索引、最低点索引
    _dp = 0  # 使用 _dp 表示 i 点的最大回撤
    i_high = 0  # 遍历时，0 ~ i - 1 中最高的点的索引，注意是索引

    # 全局最大回撤和对应的最高点和最低点的索引，注意是索引
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
