import unittest
from datetime import date

import pandas as pd

import demeter.indicator
from demeter import TokenInfo, UniV3Pool, Actuator, Strategy, Asset, UniLpMarket, MarketInfo
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

    def on_bar(self, row_data):
        pass


class TestActuator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = UniV3Pool(usdc, eth, 0.05, usdc)
        super(TestActuator, self).__init__(*args, **kwargs)

    def test_new(self):
        actuator = Actuator(self.pool)
        print(actuator)

    def get_one_actuator(self) -> Actuator:
        pool = UniV3Pool(usdc, eth, 0.05, usdc)
        test_market = MarketInfo("market1")
        market = UniLpMarket(test_market, pool)
        actuator: Actuator = Actuator()  # declare actuator
        broker = actuator.broker
        broker.add_market(market)
        broker.set_asset(usdc, 1067)
        broker.set_asset(eth, 1)

        actuator.strategy = EmptyStrategy()  # set strategy to actuator

        market.data_path = "../data"
        market.load_data(ChainType.Polygon.name,
                         "0x45dda9cb7c25131df268515131f647d726f50608",
                         date(2022, 7, 1),
                         date(2022, 7, 1))
        actuator.run()  # run test
        # actuator.output()  # print final status

        return actuator

    def test_simple_run(self):
        actuator = self.get_one_actuator()
        print(actuator.account_status_dataframe().head(5))
        print(actuator)

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
