import math
import time
import unittest
from datetime import timedelta

import numpy as np
import pandas as pd

from demeter import simple_moving_average, exponential_moving_average, realized_volatility


class TestIndicator(unittest.TestCase):
    def test_sma_minute(self):
        index = pd.date_range('2022-9-6 0:0:0', periods=10, freq='T')
        series = pd.Series(range(10), index=index)
        series_ma = simple_moving_average(series, timedelta(minutes=5))
        df = pd.DataFrame(index=index, data={"d1": series, "d2": series_ma})
        print(df)
        self.assertTrue(math.isnan(series_ma.iloc[0]))
        self.assertTrue(math.isnan(series_ma.iloc[3]))
        self.assertEqual(series_ma.iloc[4], 2)
        self.assertEqual(series_ma.iloc[8], 6)

    def test_ema_minute(self):
        index = pd.date_range('2022-9-6 0:0:0', periods=10, freq='T')
        series = pd.Series(range(10), index=index)
        series_ma = exponential_moving_average(series, alpha=1)
        df = pd.DataFrame(index=index, data={"d1": series, "d2": series_ma})
        print(df)
        self.assertEqual(series_ma.iloc[0], 0)
        self.assertEqual(series_ma.iloc[1], 1)
        self.assertEqual(series_ma.iloc[2], 2)
        self.assertEqual(series_ma.iloc[8], 8)

    def test_sma_hour(self):
        minutes = 840
        index = pd.date_range('2022-9-6 8:0:0', periods=minutes, freq='T')
        series = pd.Series(range(minutes), index=index)
        series_ma = simple_moving_average(series, timedelta(hours=5))
        df = pd.DataFrame(index=index, data={"d1": series, "d2": series_ma})
        print(df.iloc[60 * 5 - 5:].head(15))
        self.assertEqual(np.mean(range(300)), series_ma.iloc[299])
        self.assertTrue(math.isnan(float("nan")))

    def test_sma_performance(self):
        length = 1000000
        index = pd.date_range('2022-9-6 0:0:0', periods=length, freq='T')
        series = pd.Series(range(length), index=index)
        t1 = time.time()
        series_ma = simple_moving_average(series, timedelta(minutes=5))
        t2 = time.time()
        print(t2 - t1, "s")

    def test_actual_volatility(self):
        index = pd.date_range('2022-9-6 0:0:0', periods=10, freq='T')
        series = pd.Series(data=[1, 1, 1, 1, 1, math.e, 1, 1, 1, 1], index=index)
        series_v = realized_volatility(series, timedelta(minutes=2))
        df = pd.DataFrame(index=index, data={"d1": series, "d2": series_v})
        print(df)
        self.assertTrue(math.isnan(series_v.iloc[0]))
        self.assertTrue(math.isnan(series_v.iloc[1]))
        self.assertTrue(math.isnan(series_v.iloc[2]))
        self.assertEqual(series_v.iloc[3], 0.000000)
        self.assertEqual(series_v.iloc[4], 0.000000)
        self.assertEqual(series_v.iloc[5], 18.97366596101028)
        self.assertEqual(series_v.iloc[6], 18.97366596101028)
        self.assertEqual(series_v.iloc[7], 18.97366596101028)
        self.assertEqual(series_v.iloc[8], 18.97366596101028)
        self.assertEqual(series_v.iloc[9], 0.000000)
