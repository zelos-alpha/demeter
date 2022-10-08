import unittest
import pandas as pd
import numpy as np

from demeter import simple_moving_average, TimeUnitEnum


class TestIndicator(unittest.TestCase):
    def test_sma_minute(self):
        index = pd.date_range('2022-9-6 0:0:0', periods=10, freq='T')
        series = pd.Series(range(10), index=index)
        series_ma = simple_moving_average(series, 5, unit=TimeUnitEnum.minute)
        df = pd.DataFrame(index=index, data={"d1": series, "d2": series_ma})
        print(df)
        self.assertEqual(series_ma.iloc[0], 0)
        self.assertEqual(series_ma.iloc[3], 0)
        self.assertEqual(series_ma.iloc[4], 2)
        self.assertEqual(series_ma.iloc[8], 6)

    def test_sma_hour(self):
        minutes = 840
        index = pd.date_range('2022-9-6 8:0:0', periods=minutes, freq='T')
        series = pd.Series(range(minutes), index=index)
        series_ma = simple_moving_average(series, 5, unit=TimeUnitEnum.hour)
        df = pd.DataFrame(index=index, data={"d1": series, "d2": series_ma})
        print(df.iloc[60 * 5 - 5:].head(15))
        self.assertEqual(np.mean(range(300)), series_ma.iloc[299])
        self.assertEqual(0, series_ma.iloc[298])
