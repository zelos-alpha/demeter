from datetime import datetime
import pandas as pd
from datetime import datetime
from io import StringIO

from demeter import TokenInfo, Actuator, Strategy, RowData, MarketInfo, MarketTypeEnum, AtTimeTrigger, BaseAction
from demeter.aave import AaveV3Market, LiquidationAction

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)

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
2023-08-15 00:07:00,800,1
2023-08-15 00:08:00,800,1
2023-08-15 00:09:00,800,1
"""


class LiquidiateStrategy(Strategy):
    def initialize(self):
        supply_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 0, 0), do=self.supply_and_borrow)
        self.triggers.extend([supply_trigger])

    def supply_and_borrow(self, row_data: RowData):
        supply_key = aave_market.supply(weth, 10, True)
        borrow_key = aave_market.borrow(usdc, 7500)

    def notify(self, action: BaseAction):
        if isinstance(action, LiquidationAction):
            print(action)


if __name__ == "__main__":
    weth = TokenInfo(name="weth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)

    market_key = MarketInfo("aave", MarketTypeEnum.aave_v3)
    aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="../../tests/aave_risk_parameters/polygon.csv", tokens=[weth, usdc])

    aave_market.set_token_data(weth, pd.read_csv(StringIO(eth_data_csv), index_col=0, parse_dates=True))
    aave_market.set_token_data(usdc, pd.read_csv(StringIO(usdc_data_csv), index_col=0, parse_dates=True))

    actuator = Actuator()
    actuator.broker.add_market(aave_market)
    actuator.broker.set_balance(weth, 10)
    actuator.strategy = LiquidiateStrategy()

    actuator.set_price(pd.read_csv(StringIO(price_csv), index_col=0, parse_dates=True))
    actuator.run()
