import unittest
from datetime import date

import demeter.indicator
from demeter import TokenInfo, PoolInfo, Actuator, Strategy, Asset, Lines
from demeter.download import ChainType

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)


class EmptyStrategy(Strategy):
    pass


class BuyOnSecond(Strategy):
    def on_bar(self, row_data):
        if row_data.row_id == 2:
            self.buy(0.5)


class WithSMA(Strategy):
    def initialize(self):
        self._add_column("ma5", demeter.indicator.simple_moving_average(self.data.closeTick))

    def on_bar(self, row_data: Lines):
        pass


class TestActuator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = PoolInfo(usdc, eth, 0.05, usdc)
        super(TestActuator, self).__init__(*args, **kwargs)

    def test_new(self):
        actuator = Actuator(self.pool)
        print(actuator)

    def get_one_actuator(self) -> Actuator:
        actuator = Actuator(self.pool)
        actuator.strategy = EmptyStrategy()
        actuator.set_assets([Asset(usdc, 1067), Asset(eth, 1)])
        actuator.data_path = "../data"
        actuator.load_data(ChainType.Polygon.name,
                           "0x45dda9cb7c25131df268515131f647d726f50608",
                           date(2022, 7, 1),
                           date(2022, 7, 1))
        return actuator

    def test_simple_run(self):
        actuator = self.get_one_actuator()
        print(actuator.data.head(5))
        print(actuator)

    def test_lines(self):
        print(Lines())

    def test_run_empty_strategy(self):
        actuator = self.get_one_actuator()
        actuator.run()

    def test_run_buy_on_second(self):
        actuator = self.get_one_actuator()
        actuator.strategy = BuyOnSecond()
        actuator.run()
        self.assertEqual(len(actuator.actions), 1)

    def test_run_empty_with_indicator(self):
        actuator = self.get_one_actuator()
        actuator.strategy = WithSMA()
        actuator.run()

    def test_load_missing_data(self):
        actuator = Actuator(self.pool)
        actuator.data_path = "../data"
        actuator.load_data(ChainType.Polygon.name,
                           "0x45dda9cb7c25131df268515131f647d726f50608",
                           date(2022, 7, 23),
                           date(2022, 7, 24))
