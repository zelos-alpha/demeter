import unittest
import pandas as pd
from decimal import Decimal
from datetime import datetime, date
from demeter import TokenInfo, Actuator, Strategy, RowData, ChainType, MarketInfo, AtTimeTrigger, MarketTypeEnum
from demeter.gmx import GmxMarket

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)

market_key = MarketInfo("gmx", MarketTypeEnum.gmx)
weth = TokenInfo(name="weth", decimal=18)


class GmxBasicStrategy(Strategy):
    def initialize(self):
        buy_trigger = AtTimeTrigger(time=datetime(2024, 10, 15, 1, 52, 0), do=self.buy_glp)
        sell_trigger = AtTimeTrigger(time=datetime(2024, 10, 16, 14, 25, 0), do=self.sell_glp)
        self.triggers.extend([buy_trigger, sell_trigger])

    def buy_glp(self, row_data: RowData):
        market: GmxMarket = self.broker.markets[market_key]
        market.buy_glp(weth, Decimal('0.000455889485162217'))

    def sell_glp(self, row_data: RowData):
        market: GmxMarket = self.broker.markets[market_key]
        market.sell_glp(weth)

    def on_bar(self, row_data: RowData):
        pass


class TestActuator(unittest.TestCase):
    def test_basic(self):
        tokens = [
            TokenInfo(name='btc.b', decimal=8, address='0x152b9d0fdc40c096757f570a51e494bd4b943e50'),
            TokenInfo(name='weth', decimal=18, address='0x49d5c2bdffac6ce2bfdb6640f4f80f226bc10bab'),
            TokenInfo(name='wbtc', decimal=8, address='0x50b7545627a5162f82a992c33b87adc75187b218'),
            TokenInfo(name='wavax', decimal=18, address='0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7'),
            TokenInfo(name='mim', decimal=18, address='0x130966628846bfd36ff31a822705796e8cb8c18d'),
            TokenInfo(name='usdc.e', decimal=6, address='0xa7d7079b0fead91f3e65f86e8915cb59c1a4c664'),
            TokenInfo(name='usdc', decimal=6, address='0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e'),
        ]
        market = GmxMarket(market_key, tokens=tokens)
        market.data_path = "./data"
        market.load_data(
            chain=ChainType.avalanche,
            start_date=date(2024, 10, 15),
            end_date=date(2024, 10, 16)
        )
        actuator = Actuator()
        actuator.broker.add_market(market)
        weth = TokenInfo(name="weth", decimal=18, address="0x49d5c2bdffac6ce2bfdb6640f4f80f226bc10bab")
        actuator.broker.set_balance(weth, 0.000455889485162217)
        actuator.strategy = GmxBasicStrategy()
        actuator.set_price(market.get_price_from_data())
        actuator.run()
        prices = market.get_price_from_data()
        self.assertEqual(len(prices.index), 1440 * 2)
        account_status = actuator.account_status_df
        self.assertEqual(account_status.tail(1).iloc[0]["net_value"][''], Decimal('1.1823594465467726952570803410036347'))
