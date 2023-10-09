import unittest
from datetime import timedelta, datetime

import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, MarketInfo, MarketDict, MarketStatus, RowData
from demeter.uniswap import UniV3Pool, UniLpMarket
from .common import assert_equal
from .utils import get_mock_data

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)
test_market = MarketInfo("uni_market")

pd.options.display.max_columns = None
pd.options.display.max_rows = None
pd.set_option("display.width", 5000)

"""
test access data in different ways
"""


class WithSMA(Strategy):
    def on_bar(self, row_data: RowData):
        if row_data.timestamp == datetime(2022, 10, 8, 8, 0, 1):
            # access current row, method is provided by demeter
            assert_equal(row_data.uni_market.closeTick, 2)
            assert_equal(id(self.data.uni_market), id(self.data[test_market]))
            assert_equal(id(self.data.default), id(self.data[test_market]))
            assert_equal(id(row_data.uni_market), id(row_data[test_market]))
            assert_equal(id(row_data.default), id(row_data[test_market]))

            # access current row, method is provided by pandas
            assert_equal(self.data[test_market].closeTick[0], 0)
            assert_equal(self.data[test_market].loc[row_data[test_market].timestamp].closeTick, 2)
            assert_equal(self.data[test_market]["closeTick"].iloc[0], 0)

            # access previous or after row
            assert_equal(self.data.default.iloc[row_data.row_id - 2].closeTick, 0)
            assert_equal(self.data.default.loc[row_data.default.timestamp - timedelta(minutes=2)].closeTick, 0)
            assert_equal(self.data.default.loc[row_data.default.timestamp + timedelta(minutes=2)].closeTick, 4)


class TestActuator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = UniV3Pool(usdc, eth, 0.05, usdc)
        super(TestActuator, self).__init__(*args, **kwargs)

    def test_load_clean_data(self):
        actuator = Actuator()
        actuator.strategy = WithSMA()
        broker = actuator.broker
        market = UniLpMarket(test_market, self.pool)
        broker.add_market(market)
        broker.set_balance(usdc, 1000)
        broker.set_balance(eth, 1)

        tick = market.price_to_tick(1000)  # 207243
        market.data = get_mock_data(market, tick, 1000 * 10**usdc.decimal, 1 * 10**eth.decimal, "10000000000000000")
        market.data["closeTick"] = pd.Series(data=range(5), index=market.data.index)
        actuator.run()
