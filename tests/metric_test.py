import pandas as pd
import unittest
from datetime import datetime
from decimal import Decimal

from demeter import AccountStatus
from demeter.metrics.calculator import get_return_rate, annualized_return, max_draw_down_fast


class TestMetric(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestMetric, self).__init__(*args, **kwargs)
        start = pd.Timestamp(datetime(2000, 1, 1))
        end = pd.Timestamp(datetime(2000, 1, 10, 0, 0))
        self.data = pd.DataFrame(
            index=pd.date_range(start, end, freq="1D"),
            data={"net_value": [100, 100.1, 99.8, 99.5, 99.3, 99, 99.5, 99.8, 100, 100.3]},
        )
        self.data = self.data.map(lambda x: Decimal(str(x)))
        self.net_value = self.data["net_value"]
        self.init = AccountStatus(start, Decimal(100))
        self.final = self.data.iloc[-1]
        self.timespan_in_day = ((self.data.index[-1] - self.init.timestamp).value / 1e9) / 86400 + 1
        self.return_rate = get_return_rate(self.net_value)

    def test_annual_return(self):
        a11 = annualized_return(self.timespan_in_day, self.init.net_value, self.final["net_value"])
        a12 = annualized_return(self.timespan_in_day, return_rate=self.return_rate)
        a21 = annualized_return(self.timespan_in_day, self.init.net_value, self.final["net_value"], type="compound")
        a22 = annualized_return(self.timespan_in_day, return_rate=self.return_rate, type="compound")
        print(a11, a12, a21, a22)
        pass

    def test_max_drawdown(self):
        val = max_draw_down_fast(self.net_value)
        print(val)
