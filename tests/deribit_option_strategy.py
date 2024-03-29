import unittest
from datetime import datetime, date

import pandas as pd

from demeter import Strategy, AtTimeTrigger, MarketInfo, Actuator
from demeter.deribit import DeribitOptionMarket

market_key = MarketInfo("option_test")

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)

class EmptyStrategy(Strategy):
    pass


class SimpleStrategy(Strategy):
    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2022, 8, 20, 12, 0, 0), do=self.buy)
        self.triggers.append(new_trigger)

    def buy(self):
        pass


class OptionStrategyTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(OptionStrategyTest, self).__init__(*args, **kwargs)

    def test_empty_strategy(self):
        market = DeribitOptionMarket(market_key, DeribitOptionMarket.ETH, data_path="data")
        market.load_data(date(2024, 2, 15), date(2024, 2, 16))
        actuator = Actuator()
        actuator.broker.add_market(market)
        actuator.broker.set_balance(DeribitOptionMarket.ETH, 10)
        actuator.strategy = EmptyStrategy()
        actuator.set_price(market.get_price_from_data())
        actuator.run()
