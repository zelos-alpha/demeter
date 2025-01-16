import unittest
from datetime import datetime, date

import pandas as pd

from demeter import Strategy, AtTimeTrigger, MarketInfo, Actuator, Snapshot, TokenInfo, ChainType, DemeterError
from demeter.deribit import DeribitOptionMarket
from demeter.uniswap import UniV3Pool, UniLpMarket

market_u = MarketInfo("uni")
market_d = MarketInfo("deribit")
usdc = TokenInfo(name="usdc", decimal=6)  # declare token usdc
eth = TokenInfo(name="eth", decimal=18)  # declare token eth
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class EmptyStrategy(Strategy):
    pass


class SimpleStrategy(Strategy):
    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2024, 2, 16, 23, 0, 0), do=self.buy)
        self.triggers.append(new_trigger)

    def buy(self, snapshot: Snapshot):
        market_deribit: DeribitOptionMarket = self.broker.markets[market_d]
        market_deribit.buy("ETH-26APR24-2700-C", 20)
        market_uni: UniLpMarket = self.broker.markets[market_u]
        market_uni.add_liquidity(2500, 3200, 5000, 3)


class BuyWhenNotOpenStrategy(Strategy):
    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2024, 2, 15, 0, 30, 0), do=self.buy)
        self.triggers.append(new_trigger)

    def buy(self, snapshot: Snapshot):
        market_deribit: DeribitOptionMarket = self.broker.markets[market_d]
        market_deribit.buy("ETH-26APR24-2700-C", 20)


class OptionStrategyTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(OptionStrategyTest, self).__init__(*args, **kwargs)

    def _get_actuator(self):
        market_deribit = DeribitOptionMarket(market_d, DeribitOptionMarket.ETH, data_path="data")
        market_deribit.load_data(date(2024, 2, 15), date(2024, 2, 16))

        pool = UniV3Pool(token0=usdc, token1=eth, fee=0.05, quote_token=usdc)
        market_uni = UniLpMarket(market_u, pool)
        market_uni.data_path = "data"  # set data path
        market_uni.load_data(
            chain=ChainType.polygon.name,  # load data
            contract_addr="0x45dda9cb7c25131df268515131f647d726f50608",
            start_date=date(2024, 2, 15),
            end_date=date(2024, 2, 16),
        )
        actuator = Actuator()
        actuator.broker.add_market(market_deribit)
        actuator.broker.add_market(market_uni)

        actuator.broker.set_balance(eth, 10)
        actuator.broker.set_balance(usdc, 20000)
        market_deribit.deposit(3)
        actuator.set_price(market_uni.get_price_from_data())
        return actuator

    def test_empty(self):
        """
        ensure no exception thrown
        """
        actuator = self._get_actuator()
        actuator.strategy = EmptyStrategy()
        actuator.run()

    def test_buy(self):

        actuator = self._get_actuator()
        actuator.strategy = SimpleStrategy()
        actuator.run()

    def test_BuyWhenNotOpenStrategy(self):

        actuator = self._get_actuator()
        actuator.strategy = BuyWhenNotOpenStrategy()
        try:
            actuator.run()
        except DemeterError as e:
            self.assertEqual(e.message, "deribit is not open.")
