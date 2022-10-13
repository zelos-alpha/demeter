import unittest
from typing import Union
from datetime import timedelta
from demeter import TokenInfo, PoolBaseInfo, Runner, Strategy, Asset, RowData
import pandas as pd
from .runner_simulate_data_test import get_clean_data
from .common import assert_equal

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)

pd.options.display.max_columns = None
pd.options.display.max_rows = None
pd.set_option('display.width', 5000)


class WithSMA(Strategy):
    def next(self, row_data: Union[RowData, pd.Series]):

        if row_data.row_id == 2:
            # access current row, method is provided by demeter
            assert_equal(row_data.closeTick, 2)
            assert_equal(self.data.get_by_cursor(0).closeTick, 2)

            # access current row, method is provided by pandas
            assert_equal(self.data.closeTick[0], 0)
            assert_equal(self.data.loc[row_data.timestamp].closeTick, 2)
            assert_equal(self.data["closeTick"].iloc[0], 0)

            # access previous or after row
            assert_equal(self.data.get_by_cursor(-2).closeTick, 0)
            assert_equal(self.data.get_by_cursor(2).closeTick, 4)
            assert_equal(self.data.loc[row_data.timestamp - timedelta(minutes=2)].closeTick, 0)
            assert_equal(self.data.loc[row_data.timestamp + timedelta(minutes=2)].closeTick, 4)


class TestRunner(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = PoolBaseInfo(usdc, eth, 0.05, usdc)
        super(TestRunner, self).__init__(*args, **kwargs)

    def test_load_clean_data(self):
        runner = Runner(self.pool)
        runner.strategy = WithSMA()
        runner.set_assets([Asset(usdc, 1000), Asset(eth, 1)])
        tick = runner.broker.price_to_tick(1000)  # 207243
        runner.data = get_clean_data(runner,
                                     tick,
                                     1000 * 10 ** usdc.decimal,
                                     1 * 10 ** eth.decimal,
                                     "10000000000000000")
        runner.data["closeTick"] = pd.Series(data=range(5), index=runner.data.index)
        runner.run()
        runner.output()
