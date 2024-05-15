import unittest
from datetime import datetime, date
from decimal import Decimal

import pandas as pd

from demeter import (
    TokenInfo,
    MarketInfo,
    MarketTypeEnum,
    Strategy,
    Actuator,
    AtTimeTrigger,
    ActionTypeEnum,
    RowData,
)
from demeter.squeeth import SqueethMarket
from demeter.uniswap import UniLpMarket, UniV3Pool

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)

weth = TokenInfo("weth", 18)
oSQTH = TokenInfo("osqth", 18)

osqth_pool = MarketInfo("Uni", MarketTypeEnum.uniswap_v3)
squeeth_key = MarketInfo("Squeeth", MarketTypeEnum.squeeth)

d5 = Decimal("0.00001")


class EmptyStrategy(Strategy):
    pass


class SimpleStrategy(Strategy):
    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2023, 8, 17, 23, 56, 0), do=self.buy)
        self.triggers.append(new_trigger)

    def buy(self, row_data: RowData):
        market: SqueethMarket = self.broker.markets[squeeth_key]
        market.buy_squeeth(eth_amount=5)


class SimpleShortStrategy(Strategy):
    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2023, 8, 17, 23, 56, 0), do=self.short)
        self.triggers.append(new_trigger)

    def short(self, row_data: RowData):
        market: SqueethMarket = self.broker.markets[squeeth_key]
        market.open_deposit_mint_by_collat_rate(10)

    def notify(self, action):
        print(action)


def get_actuator():
    actuator = Actuator()

    uni_market = UniLpMarket(osqth_pool, UniV3Pool(weth, oSQTH, 0.3, weth), data_path="data")
    uni_market.load_data("ethereum", "0x82c427adfdf2d245ec51d8046b41c4ee87f0d29c", date(2023, 8, 14), date(2023, 8, 17))
    squeeth_market = SqueethMarket(squeeth_key, uni_market, data_path="data")
    squeeth_market.load_data(date(2023, 8, 14), date(2023, 8, 17))
    actuator.broker.add_market(uni_market)
    actuator.broker.add_market(squeeth_market)
    actuator.broker.set_balance(weth, 10)
    price_df = squeeth_market.get_price_from_data()
    actuator.set_price(price_df)
    return actuator


class SqueethStrategyTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(SqueethStrategyTest, self).__init__(*args, **kwargs)

    def test_empty_strategy(self):
        actuator = get_actuator()
        actuator.strategy = EmptyStrategy()
        actuator.run()
        self.assertEqual(len(actuator.account_status), 5760)

    def test_simple_strategy(self):
        actuator = get_actuator()
        actuator.strategy = SimpleStrategy()
        actuator.run()
        self.assertEqual(actuator.actions[0].action_type, ActionTypeEnum.uni_lp_buy)

    def test_simple_short(self):
        actuator = get_actuator()
        actuator.strategy = SimpleShortStrategy()
        actuator.run()
        self.assertEqual(len(actuator.actions), 3)
