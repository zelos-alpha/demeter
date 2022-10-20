from decimal import Decimal

import pandas as pd

from .._typing import AccountStatus, EvaluatingIndicator, DECIMAL_ZERO, UnitDecimal, ZelosError


class Evaluator(object):
    """
    calculate evaluator indicator for strategy.
    """
    def __init__(self, init_status: AccountStatus, data: pd.DataFrame):
        self.init_status: AccountStatus = init_status
        self.init_net_value = init_status.base_balance + init_status.quote_balance * init_status.price
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
        """Annualized return rate"""
        return (self.end_status.net_value / self.init_net_value) ** Decimal(365 / self.time_span_in_day) - 1

    def get_benchmark_returns(self):
        """
        Annualized benchmark return rate
        algorithm: swap token balance to 1:1, and hold those position to the end.
        :return:
        """
        base_amount, quote_amount = self.__get_benchmark_asset()
        final_benchmark_capital = base_amount + quote_amount * self.end_status.price
        return (final_benchmark_capital / self.init_net_value) ** Decimal(365 / self.time_span_in_day) - 1

    def __get_benchmark_asset(self):
        base_amount = self.init_net_value / 2
        quote_amount = (self.init_net_value - base_amount) / self.init_status.price
        return base_amount, quote_amount

    @property
    def evaluating_indicator(self):
        return self._evaluating_indicator
