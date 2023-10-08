import pickle
import unittest
from datetime import date

import pandas as pd

import demeter.indicator
from demeter import TokenInfo, UniV3Pool, Actuator, Strategy, UniLpMarket, MarketInfo, RowData, MarketDict, ChainType

pd.options.display.max_columns = None
# pd.options.display.max_rows = None
pd.set_option("display.width", 5000)
pd.options.display.max_colwidth = 100

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)
test_market = MarketInfo("market1")


class EmptyStrategy(Strategy):
    pass


class BuyOnSecond(Strategy):
    def on_bar(self, row_data: MarketDict[RowData]):
        if row_data[test_market].row_id == 2:
            self.market1.buy(0.5)
            pass


class AddLiquidity(Strategy):
    def on_bar(self, row_data: MarketDict[RowData]):
        if row_data[test_market].row_id == 2:
            assert row_data.market1.row_id == row_data[test_market].row_id
            market: UniLpMarket = self.broker.markets[test_market]
            market.add_liquidity(1000, 2000)
            pass


class WithSMA(Strategy):
    def initialize(self):
        self._add_column(self.market1, "ma5", demeter.indicator.simple_moving_average(self.market1.data.closeTick))

    def on_bar(self, row_data):
        pass


class TestActuator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestActuator, self).__init__(*args, **kwargs)

    def test_empty_actuator(self):
        actuator = Actuator()
        print(actuator)
        self.assertTrue(len(actuator.broker.markets) == 0)
        self.assertTrue(len(actuator.broker.assets) == 0)

    @staticmethod
    def get_actuator_with_uni_market() -> Actuator:
        pool = UniV3Pool(usdc, eth, 0.05, usdc)
        market = UniLpMarket(test_market, pool)
        actuator: Actuator = Actuator()  # declare actuator
        broker = actuator.broker
        broker.add_market(market)
        broker.set_balance(usdc, 1067)
        broker.set_balance(eth, 1)

        actuator.strategy = EmptyStrategy()  # set strategy to actuator

        market.data_path = "data"
        market.load_data(ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", date(2023, 8, 14), date(2023, 8, 14))
        # actuator.output()  # print final status

        return actuator

    def test_run_empty_strategy(self):
        actuator = TestActuator.get_actuator_with_uni_market()
        actuator.run()  # Observe the format and content of the output log
        print(actuator)
        self.assertEqual(
            str(actuator),
            """{"broker":{"assets":[{"name": "USDC", "value": 1067.0},{"name": "ETH", "value": 1.0}],"markets":[{"type": "UniLpMarket", "name": "market1", "position_count": 0, "total_liquidity": 0}]}, "action_count":0, "timestamp":"2023-08-14 23:59:00", "strategy":"EmptyStrategy", "price_df_rows":1439, "price_assets":["ETH","USDC"] }""",
        )


    # TODO
    def test_run_buy_on_second(self):
        actuator = TestActuator.get_actuator_with_uni_market()
        actuator.strategy = BuyOnSecond()
        actuator.run()
        self.assertEqual(len(actuator.actions), 1)

    def test_run_empty_with_indicator(self):
        actuator = TestActuator.get_actuator_with_uni_market()
        actuator.strategy = WithSMA()
        actuator.run()

    def test_load_missing_data(self):
        pool = UniV3Pool(usdc, eth, 0.05, usdc)
        market = UniLpMarket(test_market, pool)
        actuator: Actuator = Actuator()  # declare actuator
        broker = actuator.broker
        broker.add_market(market)

        market.data_path = "../data"
        market.load_data(ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", date(2022, 7, 23), date(2022, 7, 24))

    def test_add_liquidity(self):
        actuator = TestActuator.get_actuator_with_uni_market()
        actuator.strategy = AddLiquidity()
        actuator.run()

    def test_save_result(self):
        actuator = TestActuator.get_actuator_with_uni_market()
        actuator.strategy = AddLiquidity()
        actuator.run()
        actuator.save_result("./result", account=False)

    def test_load_pkl(self):
        actuator = TestActuator.get_actuator_with_uni_market()
        actuator.strategy = AddLiquidity()
        actuator.run()
        files = actuator.save_result("./result", account=False)
        file = filter(lambda x: ".pkl" in x, files)
        with open(list(file)[0], "rb") as f:
            xxx = pickle.load(f)
            self.assertEqual(actuator._action_list[0].lower_quote_price, xxx[0].lower_quote_price)
            self.assertEqual(actuator._action_list[0].action_type, xxx[0].action_type)
            self.assertEqual(actuator._action_list[0].timestamp, xxx[0].timestamp)
