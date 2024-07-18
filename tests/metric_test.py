import pandas as pd
import unittest
from datetime import datetime
from decimal import Decimal

from demeter import AccountStatus
from demeter.metrics.calculator import get_return_rate, annualized_return, max_draw_down, sharpe_ratio


class TestMetric(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestMetric, self).__init__(*args, **kwargs)
        start = pd.Timestamp(datetime(2000, 1, 1))
        end = pd.Timestamp(datetime(2000, 1, 10, 0, 0))
        self.data = pd.DataFrame(
            index=pd.date_range(start, end, freq="1D"),
            data={"net_value": [100, 100.1, 99.8, 99.5, 99.3, 99, 99.5, 99.8, 100, 100.3]},
        )
        self.data_decimal = self.data.map(lambda x: Decimal(str(x)))
        self.timespan_in_day = (end - start).value / 1e9 / 86400
        self.init = self.data["net_value"].iloc[0]
        self.final = self.data["net_value"].iloc[-1]

    def test_annual_return(self):
        a11 = annualized_return(self.timespan_in_day, self.init, self.final, type="single")
        a12 = annualized_return(self.timespan_in_day, net_values=self.data["net_value"], type="single")
        a21 = annualized_return(self.timespan_in_day, self.init, self.final)
        a22 = annualized_return(self.timespan_in_day, net_values=self.data["net_value"])
        print(a11, a12, a21, a22)
        pass

    def test_annual_return_2(self):
        a11 = annualized_return(365 / 2, 1, 1.1, type="single")
        a21 = annualized_return(365 / 2, 1, 1.1)
        self.assertEqual(round(a11, 6), 0.2)
        self.assertEqual(round(a21, 6), 0.21)
        print(a11, a21)

        a12 = annualized_return(365, net_values=pd.Series([1, 1.1, 1.2]), type="single")
        a22 = annualized_return(365, net_values=pd.Series([1, 1.1, 1.21]))
        self.assertEqual(round(a12, 6), 0.2)
        self.assertEqual(round(a22, 6), 0.21)
        a23 = annualized_return(365, return_rates=pd.Series([0, 0.1, 0.1]))
        self.assertEqual(round(a23, 6), 0.21)

        print(a12, a22,a23)

    def test_return_rate(self):

        res = get_return_rate(pd.Series([1, 1.1, 1.21]))
        print(res)
        res=res.round(5)
        self.assertEqual(res.iloc[1],0.1)
        self.assertEqual(res.iloc[2],0.1)

    def test_max_drawdown(self):
        val = max_draw_down(self.data["net_value"])
        print(val)

    def test_sharp_ratio(self):
        val = sharpe_ratio(self.timespan_in_day, self.data["net_value"], 0.01)
        print(val)
