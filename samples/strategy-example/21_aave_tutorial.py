from _decimal import Decimal
from datetime import date

import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, RowData, MarketInfo, MarketDict, MarketTypeEnum, ChainType
from demeter.aave import AaveBalance, InterestRateMode, AaveV3Market

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class MyFirstAaveStrategy(Strategy):
    def initialize(self):
        pass

    def on_bar(self, row_data: MarketDict[RowData], price: pd.Series):
        # row_data[market_key].
        balance: AaveBalance = aave_market.get_market_balance()
        local_market_var: AaveV3Market = self.broker.markets[market_key]

        if balance.supply_balance > Decimal(0):
            key1 = aave_market.supply(weth, 2)
        if balance.health_factor > 0.8:
            key2 = aave_market.supply(weth, 2, collateral=True)

        print(balance.supply_balance)
        print(balance.supplys)

        if balance.supplys[key1].apy < 0.1:  # 10%
            aave_market.withdraw(token_info=weth, amount=Decimal(10))

        key_borrow = aave_market.borrow(weth, Decimal(10), InterestRateMode.variable)

        if aave_market.borrows[key_borrow].apy < Decimal(0.1) or aave_market.get_borrow(key_borrow).apy < Decimal(0.1):
            aave_market.repay(amount=None, key=key_borrow)


if __name__ == "__main__":
    weth = TokenInfo(name="weth", decimal=18, address="0x7ceb23fd6bc0add59e62ac25578270cff1b9f619")  # declare token eth

    market_key = MarketInfo("aave_market", MarketTypeEnum.aave_v3)
    aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="../../tests/aave_risk_parameters/polygon.csv", tokens=[weth])
    aave_market.data_path = "../data"
    aave_market.load_data(ChainType.polygon.name, [weth], date(2023, 8, 14), date(2023, 8, 17))

    actuator = Actuator()
    actuator.broker.add_market(aave_market)
    actuator.broker.set_balance(weth, 10)
    actuator.strategy = MyFirstAaveStrategy()

    price_df = pd.read_csv("../data/price.csv", index_col=0, parse_dates=True)
    actuator.set_price(price_df)
    actuator.run()
