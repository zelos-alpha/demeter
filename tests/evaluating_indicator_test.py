import unittest
import pandas as pd
import time
from demeter.core.math_helper import max_draw_down_fast


class EvaluatorTest(unittest.TestCase):
    def test_max_withdraw(self):
        DATA_SIZE = 100000
        data = range(DATA_SIZE, 0, -1)
        data = pd.Series(data=data)
        t1 = time.time()
        mw = max_draw_down_fast(data)

        print(f"result: {mw}, time : {time.time() - t1}s")
        self.assertEqual(mw, (data.iloc[0] - data.iloc[len(data.index) - 1]) / data.iloc[0])

    def test_max_withdraw_predefined_data(self):
        data = pd.Series(data=[3, 1, 8, 5, 6, 2, 9, 4, 5])
        mw = max_draw_down_fast(data)
        self.assertEqual(mw, (8 - 2) / 8)
