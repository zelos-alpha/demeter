import unittest
import pandas as pd

from demeter.core.evaluating_indicator import Evaluator


class EvaluatorTest(unittest.TestCase):
    def test_max_withdraw(self):
        DATA_SIZE = 500
        index = pd.date_range('2022-10-8 8:0:0', periods=DATA_SIZE, freq='T')
        data = range(DATA_SIZE, 0, -1)
        data = pd.Series(data=data, index=index)
        mw = Evaluator.get_max_drawdown(data)
        print(mw)
        self.assertEqual(mw, 0.998)
