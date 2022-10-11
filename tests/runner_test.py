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
    def next(self, row_data):
        if row_data.row_id == 2:
            self.buy(0.5)


class WithSMA(Strategy):
    def initialize(self):
        self._add_column("ma5", demeter.indicator.simple_moving_average(self.data.closeTick, 5))

    def next(self, row_data: Lines):
        pass


class TestRunner(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = PoolBaseInfo(usdc, eth, 0.05, usdc)
        super(TestRunner, self).__init__(*args, **kwargs)

    def test_new(self):
        runner = Runner(self.pool)
        print(runner)

    def get_one_runner(self) -> Runner:
        runner = Runner(self.pool)
        runner.strategy = EmptyStrategy()
        runner.set_assets([Asset(usdc, 1067), Asset(eth, 1)])
        runner.data_path = "../data"
        runner.load_data(ChainType.Polygon.name,
                         "0x45dda9cb7c25131df268515131f647d726f50608",
                         date(2022, 7, 1),
                         date(2022, 7, 1))
        return runner

    def test_simple_run(self):
        runner = self.get_one_runner()
        print(runner.data.head(5))
        print(runner)

    def test_lines(self):
        print(Lines())

    def test_run_empty_strategy(self):
        runner = self.get_one_runner()
        runner.run()

    def test_run_buy_on_second(self):
        runner = self.get_one_runner()
        runner.strategy = BuyOnSecond()
        runner.run()
        self.assertEqual(len(runner.actions), 1)

    def test_run_empty_with_indicator(self):
        runner = self.get_one_runner()
        runner.strategy = WithSMA()
        runner.run()

    def test_load_missing_data(self):
        runner = Runner(self.pool)
        runner.data_path = "../data"
        runner.load_data(ChainType.Polygon.name,
                         "0x45dda9cb7c25131df268515131f647d726f50608",
                         date(2022, 7, 23),
                         date(2022, 7, 24))
