import numpy as np
import pandas as pd
import unittest
from datetime import datetime
from decimal import Decimal
import time
from demeter import AccountStatus
from demeter.metrics.calculator import return_rate_series, annualized_return, max_draw_down, sharpe_ratio, alpha_beta


class TestMetric(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestMetric, self).__init__(*args, **kwargs)
        start = pd.Timestamp(datetime(2000, 1, 1))
        end = pd.Timestamp(datetime(2000, 1, 10, 0, 0))
        index = pd.date_range(start, end, freq="1D")
        self.data = pd.Series(
            index=index,
            data=[100, 100.1, 99.8, 99.5, 99.3, 99, 99.5, 99.8, 100, 100.3],
        )
        self.data_decimal = self.data.map(lambda x: Decimal(str(x)))
        benchmark_arr = np.random.normal(loc=0, scale=0.1, size=10).cumsum() + 100
        self.benchmark = pd.Series(index=index, data=benchmark_arr)
        self.duration_in_day = (end - start).value / 1e9 / 86400
        self.init = self.data.iloc[0]
        self.final = self.data.iloc[-1]

    def test_annual_return(self):
        a11 = round(annualized_return(self.duration_in_day, self.init, self.final), 6)
        a12 = round(annualized_return(self.duration_in_day, net_values=self.data), 6)
        a21 = round(annualized_return(self.duration_in_day, self.init, self.final), 6)
        a22 = round(annualized_return(self.duration_in_day, net_values=self.data), 6)
        print(a11, a12, a21, a22)
        pass

    def test_annual_return_2(self):
        a11 = round(annualized_return(365 / 2, 1, 1.1, interest_type="single"), 6)
        a21 = round(annualized_return(365 / 2, 1, 1.1), 6)
        self.assertEqual(a11, 0.2)
        self.assertEqual(a21, 0.21)
        print(a11, a21)

        a12 = round(annualized_return(365, net_values=pd.Series([1, 1.1, 1.2])), 6)
        a22 = round(annualized_return(365, net_values=pd.Series([1, 1.1, 1.21])), 6)
        self.assertEqual(a12, 0.2)
        self.assertEqual(a22, 0.21)
        a23 = round(annualized_return(365, return_rates=pd.Series([0, 0.1, 0.1])), 6)
        self.assertEqual(a23, 0.21)

        print(a12, a22, a23)

    def test_return_rate(self):

        res = return_rate_series(pd.Series([1, 1.1, 1.21]))
        print(res)
        res = res.round(5)
        self.assertEqual(res.iloc[1], 0.1)
        self.assertEqual(res.iloc[2], 0.1)

    def test_max_drawdown(self):
        val = max_draw_down(self.data)
        print(val)

    def test_max_withdraw(self):
        DATA_SIZE = 100000
        data = range(DATA_SIZE, 0, -1)
        data = pd.Series(data=data)
        t1 = time.time()
        mw = max_draw_down(data)

        print(f"result: {mw}, time : {time.time() - t1}s")
        self.assertEqual(mw, (data.iloc[0] - data.iloc[len(data.index) - 1]) / data.iloc[0])

    def test_max_withdraw_predefined_data(self):
        data = pd.Series(data=[3, 1, 8, 5, 6, 2, 9, 4, 5])
        mw = max_draw_down(data)
        self.assertEqual(mw, (8 - 2) / 8)

    def test_sharp_ratio(self):
        daily_returns = pd.Series([1.0, 1.01, 0.96, 1.00, 1.02, 1.01])
        risk_free_rate = 0.05
        val = sharpe_ratio(1, self.duration_in_day, daily_returns, risk_free_rate)
        print("sharpe ratio", val)
        self.assertEqual(0.6789644166270484, val)

    def test_alpha_beta(self):
        print(alpha_beta(self.data, self.benchmark, self.duration_in_day))
