import pandas as pd
import unittest
from _decimal import Decimal
from datetime import datetime
from io import StringIO

from demeter import TokenInfo, Actuator, Strategy, RowData, MarketInfo, MarketTypeEnum, AtTimeTrigger, BaseAction
from demeter.aave import AaveV3Market, LiquidationAction

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)

simple_data_csv = """
block_timestamp,liquidity_rate,stable_borrow_rate,variable_borrow_rate,liquidity_index,variable_borrow_index\n
2023-08-15 00:00:00,0,0,0,1,1\n
2023-08-15 00:01:00,0,0,0,1,1\n
2023-08-15 00:02:00,0,0,0,1,1\n
2023-08-15 00:03:00,0,0,0,1,1\n
2023-08-15 00:04:00,0,0,0,1,1\n
"""
simple_data_growing_index_csv = """
block_timestamp,liquidity_rate,stable_borrow_rate,variable_borrow_rate,liquidity_index,variable_borrow_index\n
2023-08-15 00:00:00,0,0,0,1.001,1.001\n
2023-08-15 00:01:00,0,0,0,1.002,1.002\n
2023-08-15 00:02:00,0,0,0,1.003,1.003\n
2023-08-15 00:03:00,0,0,0,1.004,1.004\n
2023-08-15 00:04:00,0,0,0,1.005,1.005\n
"""
# will cause delt larger than collateral
sudden_falling_price_csv = """
,WETH,USDC
2023-08-15 00:00:00,1000,1
2023-08-15 00:01:00,1000,1
2023-08-15 00:02:00,1000,1
2023-08-15 00:03:00,500,1
2023-08-15 00:04:00,1000,1

"""

liquidate_half_price_csv = """
,WETH,USDC
2023-08-15 00:00:00,1000,1
2023-08-15 00:01:00,1000,1
2023-08-15 00:02:00,1000,1
2023-08-15 00:03:00,900,1
2023-08-15 00:04:00,1000,1

"""

liquidate_all_price_csv = """
,WETH,USDC
2023-08-15 00:00:00,1000,1
2023-08-15 00:01:00,1000,1
2023-08-15 00:02:00,1000,1
2023-08-15 00:03:00,800,1
2023-08-15 00:04:00,1000,1

"""

weth = TokenInfo(name="weth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)

market_key = MarketInfo("aave", MarketTypeEnum.aave_v3)


class LiquidiateStrategy(Strategy):
    def initialize(self):
        supply_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 0, 0), do=self.supply_and_borrow)
        self.triggers.extend([supply_trigger])

    def supply_and_borrow(self, row_data: RowData):
        aave_market: AaveV3Market = self.broker.markets[market_key]
        supply_key = aave_market.supply(weth, 10, True)
        borrow_key = aave_market.borrow(usdc, 7500)

    def notify(self, action: BaseAction):
        if isinstance(action, LiquidationAction):
            print(action)


class TestActuator(unittest.TestCase):
    def test_delt_larger_than_collateral(self):
        aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="aave_risk_parameters/polygon.csv", tokens=[weth, usdc])

        aave_market.set_token_data(weth, pd.read_csv(StringIO(simple_data_csv), index_col=0, parse_dates=True))
        aave_market.set_token_data(usdc, pd.read_csv(StringIO(simple_data_csv), index_col=0, parse_dates=True))

        actuator = Actuator()
        actuator.broker.add_market(aave_market)
        actuator.broker.set_balance(weth, 10)
        actuator.strategy = LiquidiateStrategy()

        actuator.set_price(pd.read_csv(StringIO(sudden_falling_price_csv), index_col=0, parse_dates=True))
        actuator.run()
        self.assertEqual(aave_market.health_factor, 0)
        self.assertEqual(len(aave_market.supplies), 0)
        self.assertEqual(len(aave_market.borrows), 1)
        pass

    def test_delt_larger_than_collateral_with_growing_liqindex(self):
        aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="aave_risk_parameters/polygon.csv", tokens=[weth, usdc])

        aave_market.set_token_data(weth, pd.read_csv(StringIO(simple_data_growing_index_csv), index_col=0, parse_dates=True))
        aave_market.set_token_data(usdc, pd.read_csv(StringIO(simple_data_growing_index_csv), index_col=0, parse_dates=True))

        actuator = Actuator()
        actuator.broker.add_market(aave_market)
        actuator.broker.set_balance(weth, 10)
        actuator.strategy = LiquidiateStrategy()

        actuator.set_price(pd.read_csv(StringIO(sudden_falling_price_csv), index_col=0, parse_dates=True))
        actuator.run()
        self.assertEqual(aave_market.health_factor, 0)
        self.assertEqual(len(aave_market.supplies), 0)
        self.assertEqual(len(aave_market.borrows), 1)
        pass

    def test_liquidate_all(self):
        aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="aave_risk_parameters/polygon.csv", tokens=[weth, usdc])

        aave_market.set_token_data(weth, pd.read_csv(StringIO(simple_data_csv), index_col=0, parse_dates=True))
        aave_market.set_token_data(usdc, pd.read_csv(StringIO(simple_data_csv), index_col=0, parse_dates=True))

        actuator = Actuator()
        actuator.broker.add_market(aave_market)
        actuator.broker.set_balance(weth, 10)
        actuator.strategy = LiquidiateStrategy()

        actuator.set_price(pd.read_csv(StringIO(liquidate_all_price_csv), index_col=0, parse_dates=True))
        actuator.run()
        self.assertEqual(aave_market.health_factor, Decimal("inf"))
        self.assertEqual(len(aave_market.supplies), 1)
        self.assertEqual(len(aave_market.borrows), 0)
        pass

    def test_liquidate_half(self):
        aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="aave_risk_parameters/polygon.csv", tokens=[weth, usdc])

        aave_market.set_token_data(weth, pd.read_csv(StringIO(simple_data_csv), index_col=0, parse_dates=True))
        aave_market.set_token_data(usdc, pd.read_csv(StringIO(simple_data_csv), index_col=0, parse_dates=True))

        actuator = Actuator()
        actuator.broker.add_market(aave_market)
        actuator.broker.set_balance(weth, 10)
        actuator.strategy = LiquidiateStrategy()

        actuator.set_price(pd.read_csv(StringIO(liquidate_half_price_csv), index_col=0, parse_dates=True))
        actuator.run()
        self.assertEqual(aave_market.health_factor, Decimal("1.2375"))
        self.assertEqual(len(aave_market.supplies), 1)
        self.assertEqual(len(aave_market.borrows), 1)
        pass