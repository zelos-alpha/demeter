import pandas as pd
from datetime import date, datetime
from typing import Union

from demeter import TokenInfo, Actuator, Strategy, RowData, MarketInfo, MarketTypeEnum, ChainType, AtTimeTrigger
from demeter.aave import AaveBalance, AaveV3Market, AaveTokenStatus

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class MyFirstAaveStrategy(Strategy):
    def initialize(self):
        supply_trigger = AtTimeTrigger(time=datetime(2023, 8, 14, 0, 1, 0), do=self.supply)
        withdraw_trigger = AtTimeTrigger(time=datetime(2023, 8, 14, 23, 58, 0), do=self.withdraw)
        borrow_trigger = AtTimeTrigger(time=datetime(2023, 8, 14, 0, 2, 0), do=self.borrow)
        repay_trigger = AtTimeTrigger(time=datetime(2023, 8, 14, 23, 57, 0), do=self.repay)

        self.triggers.extend([supply_trigger, withdraw_trigger, borrow_trigger, repay_trigger])

    def supply(self, row_data: RowData):
        supply_key = aave_market.supply(weth, 10, True)

    def borrow(self, row_data: RowData):
        borrow_key = aave_market.borrow(weth, 3)

    def repay(self, row_data: RowData):
        for key in aave_market.borrow_keys:
            aave_market.repay(key)

    def withdraw(self, row_data: RowData):
        for key in aave_market.supply_keys:
            aave_market.withdraw(key)

    def on_bar(self, row_data: RowData):
        balance: AaveBalance = aave_market.get_market_balance()
        market_status: Union[pd.Series, AaveTokenStatus] = row_data.market_status[market_key]

        pass


if __name__ == "__main__":
    weth = TokenInfo(name="weth", decimal=18, address="0x7ceb23fd6bc0add59e62ac25578270cff1b9f619")  # declare token eth

    market_key = MarketInfo("aave", MarketTypeEnum.aave_v3)
    aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="../../tests/aave_risk_parameters/polygon.csv", tokens=[weth])
    aave_market.data_path = "../data"
    aave_market.load_data(ChainType.polygon, [weth], date(2023, 8, 14), date(2023, 8, 14))
    actuator = Actuator()
    actuator.broker.add_market(aave_market)
    actuator.broker.set_balance(weth, 15)
    actuator.strategy = MyFirstAaveStrategy()

    price_df = pd.read_csv("../data/price_weth_usdc_0813_0817.csv", index_col=0, parse_dates=True)
    actuator.set_price(price_df)
    actuator.run()
