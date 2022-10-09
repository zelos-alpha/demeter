import pandas as pd

from .._typing import BarStatus, EvaluatingIndicator, DECIMAL_ZERO, UnitDecimal, ZelosError
from decimal import Decimal


class Evaluator(object):

    def __init__(self, init_status: BarStatus, data: pd.DataFrame):
        self.init_status: BarStatus = init_status
        self.init_capital = init_status.base_balance.number + init_status.quote_balance.number * init_status.price.number
        self.end_status = data.iloc[-1]
        self.data = data
        if len(data) < 2:
            raise ZelosError("not enought data")
        self.time_span_in_day = len(data.index) * (data.index[1] - data.index[0]).seconds / (60 * 60 * 24)
        self._evaluating_indicator: EvaluatingIndicator = None

    def run(self):
        self._evaluating_indicator = EvaluatingIndicator(DECIMAL_ZERO, DECIMAL_ZERO)
        self._evaluating_indicator.annualized_returns = UnitDecimal(self.get_annualized_returns(), "")
        self._evaluating_indicator.benchmark_returns = UnitDecimal(self.get_benchmark_returns(), "")
        return self._evaluating_indicator

    def get_annualized_returns(self):
        """年化收益率"""
        return (self.end_status.capital.number / self.init_capital) ** Decimal(365 / self.time_span_in_day) - 1

    def get_benchmark_returns(self):
        """
        基准收益率
        算法: 资产调仓成1:1的比例. 持有到最后.
        :return:
        """
        base_amount, quote_amount = self.__get_benchmark_asset()
        final_benchmark_capital = base_amount + quote_amount * self.end_status.price.number
        return (final_benchmark_capital / self.init_capital) ** Decimal(365 / self.time_span_in_day) - 1

    def __get_benchmark_asset(self):
        base_amount = self.init_capital / 2
        quote_amount = (self.init_capital - base_amount) / self.init_status.price.number
        return base_amount, quote_amount

    @property
    def evaluating_indicator(self):
        return self._evaluating_indicator
