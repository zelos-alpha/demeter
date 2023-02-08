from decimal import Decimal
from typing import Union

import pandas as pd

from .._typing import UnitDecimal, DemeterError, EvaluatorEnum


class Evaluator(object):
    """
    calculate evaluator indicator for strategy.
    """

    def __init__(self, init_status, data):
        self.init_status = init_status
        self.init_net_value = init_status.base_balance + init_status.quote_balance * init_status.price
        self.end_status = data.iloc[-1]
        self.data: Union[pd.DataFrame] = data
        if len(data) < 2:
            raise DemeterError("not enough data")
        self.time_span_in_day = len(data.index) * (data.index[1] - data.index[0]).seconds / (60 * 60 * 24)
        self._result = None

    def run(self, enables: list[EvaluatorEnum]):
        if EvaluatorEnum.ALL in enables:
            enables = [x for x in EvaluatorEnum]
            enables = filter(lambda x: x.value > 0, enables)
        result_dict: dict[EvaluatorEnum:UnitDecimal] = {}
        for request in enables:
            match request:
                case EvaluatorEnum.ANNUALIZED_RETURNS:
                    result = UnitDecimal(self.get_annualized_returns(), "")
                case EvaluatorEnum.BENCHMARK_RETURNS:
                    result = UnitDecimal(self.get_benchmark_returns(), "")
                case EvaluatorEnum.MAX_DRAEDOWN:
                    result = UnitDecimal(Evaluator.get_max_drawdown_fast(self.data.net_value), "")
                case _:
                    raise DemeterError(f"{request} has not implied")
            result_dict[request] = result
        self._result = result_dict
        return result_dict

    def get_annualized_returns(self):
        """Annualized return rate"""
        return (self.end_status.pool_net_value / self.init_net_value) ** Decimal(365 / self.time_span_in_day) - 1

    def get_benchmark_returns(self):
        """
        Annualized benchmark return rate
        algorithm: swap token balance to 1:1, and hold those position to the end.
        :return:
        """
        base_amount, quote_amount = self.__get_benchmark_asset()
        final_benchmark_capital = base_amount + quote_amount * self.end_status.price
        return (final_benchmark_capital / self.init_net_value) ** Decimal(365 / self.time_span_in_day) - 1

    @staticmethod
    def get_max_drawdown(net_values: pd.Series):

        net_values.index = range(len(net_values.index))  # restruct index to access faster
        max_drawdown = 0
        for index, row in net_values.iteritems():
            current_max = net_values[index:].apply(lambda nv: 1 - nv / row).max()
            if current_max > max_drawdown:
                max_drawdown = current_max
        return max_drawdown

    @staticmethod
    def get_max_drawdown_fast(net_values: pd.Series):
        max_value, idx_h, idx_l = Evaluator._withdraw_with_high_low(net_values.to_list())
        return (net_values.iloc[idx_h] - net_values.iloc[idx_l]) / net_values.iloc[idx_h]

    @staticmethod
    def _withdraw_with_high_low(arr: list):
        """
        from : https://blog.csdn.net/Spade_/article/details/112341428
        """

        # 传入一个数组，返回最大回撤和对应的最高点索引、最低点索引
        _dp = 0  # 使用 _dp 表示 i 点的最大回撤
        i_high = 0  # 遍历时，0 ~ i - 1 中最高的点的索引，注意是索引

        # 全局最大回撤和对应的最高点和最低点的索引，注意是索引
        g_withdraw, g_high, g_low = float('-inf'), -1, -1

        for i in range(1, len(arr)):
            if arr[i_high] < arr[i - 1]:  # 若 0 ~ i - 1 中最高的点小于当前点
                i_high = i - 1  # 0 ~ i - 1 中最高的点的索引

            _dp = arr[i_high] - arr[i]  # _dp 表示 i 点的最大回撤
            if _dp > g_withdraw:  # 找到新的最大回撤，更新三个值
                g_withdraw = _dp
                g_high = i_high
                g_low = i

        return g_withdraw, g_high, g_low

    def __get_benchmark_asset(self):
        base_amount = self.init_net_value / 2
        quote_amount = (self.init_net_value - base_amount) / self.init_status.price
        return base_amount, quote_amount

    @property
    def result(self) -> dict[EvaluatorEnum:UnitDecimal]:
        return self._result
