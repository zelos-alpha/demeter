import unittest
import pandas as pd
import time
from demeter.core.evaluating_indicator import Evaluator


class EvaluatorTest(unittest.TestCase):
    def test_max_withdraw(self):
        DATA_SIZE = 100000
        data = range(DATA_SIZE, 0, -1)
        data = pd.Series(data=data)
        t1 = time.time()
        mw = Evaluator.get_max_drawdown_fast(data)

        print(f"result: {mw}, time : {time.time() - t1}s")
        self.assertEqual(mw, (data.iloc[0] - data.iloc[len(data.index) - 1]) / data.iloc[0])

    def test_max_withdraw_fast(self):
        DATA_SIZE = 100000
        data = range(DATA_SIZE, 0, -1)
        data = pd.Series(data=data)
        t1 = time.time()
        mw = Evaluator._withdraw_with_high_low(data.to_list())
        r = (data.iloc[mw[1]] - data.iloc[mw[2]]) / data.iloc[mw[1]]
        print(f"func out: {mw}, result: {r}, time : {time.time() - t1}s")
        self.assertEqual(r, (data.iloc[0] - data.iloc[len(data.index) - 1]) / data.iloc[0])

    def test_max_withdraw(self):
        data = pd.Series(data=[3, 1, 8, 5, 6, 2, 9, 4, 5])
        mw = Evaluator.get_max_drawdown(data)
        self.assertEqual(mw, (8 - 2) / 8)
