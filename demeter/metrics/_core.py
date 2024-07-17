from typing import List

from demeter import AccountStatus
from demeter.metrics._typing import MetricEnum
from .calculator import *

DECIMAL_1 = Decimal(1)


class MetricsCalculator:
    def __init__(self, initial_equity: AccountStatus, account_status: pd.DataFrame):
        self.data = account_status
        self.net_value = self.data["net_value"]
        self.init = initial_equity
        self.final = account_status.iloc[-1]
        self.timespan_in_day = ((self.data.index[-1] - self.init.timestamp).value / 1e9 + 60) / 86400
        self.return_rate = get_return_rate(self.net_value)
        pass

    def run(self, metrics: List[MetricEnum] = None):
        if metrics is None:
            metrics = [MetricEnum.return_value, MetricEnum.annualized_return]

        result = {}
        for metric in metrics:
            match metric:
                case MetricEnum.return_value:
                    result[metric] = return_value(self.init.net_value, self.net_value.iloc[-1])
                case MetricEnum.return_rate:
                    result[metric] = return_rate(self.init.net_value, self.net_value.iloc[-1])
                case MetricEnum.annualized_return:
                    result[metric] = annualized_return(
                        self.timespan_in_day, self.init.net_value, self.net_value.iloc[-1]
                    )
                case MetricEnum.benchmark_return:
                    token_return = {}
                    for column in self.data["price"].columns:
                        token_return[column] = annualized_return(
                            self.timespan_in_day,
                            self.data["price"][column].iloc[0],
                            self.data["price"][column].iloc[-1],
                        )
                    result[metric] = token_return
                case MetricEnum.max_drawdown:
                    result[metric] = max_draw_down_fast(self.net_value)
        return result
