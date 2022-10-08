import unittest
from datetime import date

import demeter.indicator
from download import ChainType
from demeter import Broker, TokenInfo, PoolBaseInfo, Runner, Strategy, Asset, Lines
import pandas as pd
from decimal import Decimal

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)


class EmptyStrategy(Strategy):
    pass


class BuyOnSecond(Strategy):
    def next(self, time, row_data):
        if row_data.row_id == 2:
            self.buy(0.5)


class WithSMA(Strategy):
    def initialize(self):
        self._add_column("ma5", demeter.indicator.simple_moving_average(self.data.closeTick, 5))

    def next(self, time, row_data: Lines):
        pass


class TestDemeter(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = PoolBaseInfo(usdc, eth, 0.05, usdc)
        super(TestDemeter, self).__init__(*args, **kwargs)

    def test_new(self):
        demeter = Runner(self.pool)
        print(demeter)

    def get_one_demeter(self) -> Runner:
        demeter = Runner(self.pool)
        demeter.strategy = EmptyStrategy()
        demeter.set_assets([Asset(usdc, 1067), Asset(eth, 1)])
        demeter.data_path = "../data"
        demeter.load_data(ChainType.Polygon.name,
                          "0x45dda9cb7c25131df268515131f647d726f50608",
                          date(2022, 7, 1),
                          date(2022, 7, 1))
        return demeter

    def test_simple_run(self):
        demeter = self.get_one_demeter()
        print(demeter.data.head(5))
        print(demeter)

    def test_lines(self):
        print(Lines())

    def test_run_empty_strategy(self):
        demeter = self.get_one_demeter()
        demeter.run()

    def test_run_buy_on_second(self):
        demeter = self.get_one_demeter()
        demeter.strategy = BuyOnSecond()
        demeter.run()
        self.assertEqual(len(demeter.actions), 1)

    def test_run_empty_with_indicator(self):
        demeter = self.get_one_demeter()
        demeter.strategy = WithSMA()
        demeter.run()

    def test_load_missing_data(self):
        demeter = Runner(self.pool)
        demeter.data_path = "../data"
        demeter.load_data(ChainType.Polygon.name,
                          "0x45dda9cb7c25131df268515131f647d726f50608",
                          date(2022, 7, 23),
                          date(2022, 7, 24))