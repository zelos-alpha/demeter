import unittest
from _decimal import Decimal
from datetime import date, datetime
from io import StringIO
from typing import Union

import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, RowData, MarketInfo, MarketDict, MarketTypeEnum, ChainType, AtTimeTrigger
from demeter.aave import AaveBalance, InterestRateMode, AaveV3Market, AaveTokenStatus

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


weth = TokenInfo(name="weth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)

market_key = MarketInfo("aave", MarketTypeEnum.aave_v3)

eth_data_csv = """
block_timestamp,liquidity_rate,stable_borrow_rate,variable_borrow_rate,liquidity_index,variable_borrow_index\n
2023-08-15 00:00:00,0,0,0,1.000,1.000\n
2023-08-15 00:01:00,0,0,0,1.001,1.001\n
2023-08-15 00:02:00,0,0,0,1.002,1.002\n
2023-08-15 00:03:00,0,0,0,1.003,1.003\n
2023-08-15 00:04:00,0,0,0,1.004,1.004\n
2023-08-15 00:05:00,0,0,0,1.005,1.005\n
2023-08-15 00:06:00,0,0,0,1.006,1.006\n
2023-08-15 00:07:00,0,0,0,1.007,1.007\n
2023-08-15 00:08:00,0,0,0,1.008,1.008\n
2023-08-15 00:09:00,0,0,0,1.009,1.009\n
"""
usdc_data_csv = """
block_timestamp,liquidity_rate,stable_borrow_rate,variable_borrow_rate,liquidity_index,variable_borrow_index\n
2023-08-15 00:00:00,0,0,0,1.000,1.000\n
2023-08-15 00:01:00,0,0,0,1.001,1.001\n
2023-08-15 00:02:00,0,0,0,1.002,1.002\n
2023-08-15 00:03:00,0,0,0,1.003,1.003\n
2023-08-15 00:04:00,0,0,0,1.004,1.004\n
2023-08-15 00:05:00,0,0,0,1.005,1.005\n
2023-08-15 00:06:00,0,0,0,1.006,1.006\n
2023-08-15 00:07:00,0,0,0,1.007,1.007\n
2023-08-15 00:08:00,0,0,0,1.008,1.008\n
2023-08-15 00:09:00,0,0,0,1.009,1.009\n
"""
price_csv = """
,WETH,USDC
2023-08-15 00:00:00,1000,1
2023-08-15 00:01:00,1000,1
2023-08-15 00:02:00,1000,1
2023-08-15 00:03:00,1000,1
2023-08-15 00:04:00,1000,1
2023-08-15 00:05:00,1000,1
2023-08-15 00:06:00,1000,1
2023-08-15 00:07:00,1000,1
2023-08-15 00:08:00,1000,1
2023-08-15 00:09:00,1000,1
"""


class BasicStrategy(Strategy):
    def initialize(self):
        supply_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 0, 0), do=self.supply_and_borrow)
        self.triggers.extend([supply_trigger])

    def supply_and_borrow(self, row_data: RowData):
        aave_market: AaveV3Market = self.broker.markets[market_key]
        supply_key = aave_market.supply(weth, 10, True)
        borrow_key = aave_market.borrow(weth, 7)


class AllOperationStrategy(Strategy):
    def initialize(self):
        supply_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 0, 0), do=self.supply_and_borrow)
        repay_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 0, 7), do=self.repay)
        withdraw_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 0, 8), do=self.withdraw)
        self.triggers.extend([supply_trigger, repay_trigger, withdraw_trigger])

    def supply_and_borrow(self, row_data: RowData):
        aave_market: AaveV3Market = self.broker.markets[market_key]
        supply_key = aave_market.supply(weth, 10, True)
        borrow_key = aave_market.borrow(weth, 7)

    def repay(self, row_data: RowData):
        aave_market: AaveV3Market = self.broker.markets[market_key]
        for key in aave_market.borrow_keys:
            aave_market.repay(key)

    def withdraw(self, row_data: RowData):
        aave_market: AaveV3Market = self.broker.markets[market_key]
        for key in aave_market.supply_keys:
            aave_market.withdraw(key)


class RepayWithCollateralStrategy(Strategy):
    def initialize(self):
        supply_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 0, 0), do=self.supply_and_borrow)
        repay_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 0, 7), do=self.repay)
        self.triggers.extend([supply_trigger, repay_trigger])

    def supply_and_borrow(self, row_data: RowData):
        aave_market: AaveV3Market = self.broker.markets[market_key]
        supply_key = aave_market.supply(weth, 10, True)
        borrow_key = aave_market.borrow(weth, aave_market.get_max_borrow_amount(weth))

    def repay(self, row_data: RowData):
        aave_market: AaveV3Market = self.broker.markets[market_key]
        aave_market.repay(borrow_token=weth, interest_rate_mode=InterestRateMode.variable, repay_with_collateral=True)


class TestActuator(unittest.TestCase):
    def test_basic(self):
        aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="./aave_risk_parameters/polygon.csv", tokens=[weth])

        aave_market.set_token_data(weth, pd.read_csv(StringIO(eth_data_csv), index_col=0, parse_dates=True))

        actuator = Actuator()
        actuator.broker.add_market(aave_market)
        actuator.broker.set_balance(weth, 10)
        actuator.strategy = BasicStrategy()

        actuator.set_price(pd.read_csv(StringIO(price_csv), index_col=0, parse_dates=True))
        actuator.run()
        account_status = actuator.get_account_status_dataframe()
        self.assertEqual(account_status.tail(1).iloc[0].net_value, Decimal("10027"))
        self.assertEqual(account_status.tail(1).iloc[0].aave_borrows_value, Decimal("7063"))
        self.assertEqual(account_status.tail(1).iloc[0].aave_supplies_value, Decimal("10090"))

    def test_all_operation(self):
        aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="./aave_risk_parameters/polygon.csv", tokens=[weth])

        aave_market.set_token_data(weth, pd.read_csv(StringIO(eth_data_csv), index_col=0, parse_dates=True))

        actuator = Actuator()
        actuator.broker.add_market(aave_market)
        actuator.broker.set_balance(weth, 15)
        actuator.strategy = AllOperationStrategy()

        actuator.set_price(pd.read_csv(StringIO(price_csv), index_col=0, parse_dates=True))
        actuator.run()
        account_status = actuator.get_account_status_dataframe()

        self.assertEqual(account_status.iloc[0].aave_borrows_value, Decimal("7000"))
        self.assertEqual(account_status.iloc[6].aave_borrows_value, Decimal("7042"))

        self.assertEqual(account_status.iloc[7].aave_health_factor, Decimal("inf"))
        self.assertEqual(account_status.iloc[7].aave_supplies_value, Decimal("10070.0000"))
        self.assertEqual(account_status.iloc[7].aave_borrows_value, Decimal("0"))
        self.assertEqual(account_status.iloc[7].aave_health_factor, Decimal("inf"))

        self.assertEqual(account_status.iloc[8].aave_supplies_value, Decimal("0"))
        self.assertEqual(account_status.iloc[9].net_value, Decimal("15031.00000000000080468964825"))

    def test_repay_with_collateral(self):
        aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="./aave_risk_parameters/polygon.csv", tokens=[weth])

        aave_market.set_token_data(weth, pd.read_csv(StringIO(eth_data_csv), index_col=0, parse_dates=True))

        actuator = Actuator()
        actuator.broker.add_market(aave_market)
        actuator.broker.set_balance(weth, 10)
        actuator.strategy = RepayWithCollateralStrategy()

        actuator.set_price(pd.read_csv(StringIO(price_csv), index_col=0, parse_dates=True))
        actuator.run()
        account_status = actuator.get_account_status_dataframe()

        self.assertEqual(account_status.iloc[0].aave_borrows_value, Decimal("7920"))
        self.assertEqual(account_status.iloc[6].aave_borrows_value, Decimal("7967.5200"))
        self.assertEqual(account_status.iloc[6].aave_supplies_value, Decimal("10060"))
        self.assertEqual(account_status.iloc[6].WETH, Decimal("7.92"))

        self.assertEqual(account_status.iloc[7].aave_health_factor, Decimal("inf"))
        self.assertEqual(account_status.iloc[7].aave_supplies_value, Decimal("2094.5600"))
        self.assertEqual(account_status.iloc[7].aave_borrows_value, Decimal("0"))
        self.assertEqual(account_status.iloc[7].WETH, Decimal("7.92"))

        self.assertEqual(actuator.broker.get_token_balance(weth), Decimal("7.92"))
