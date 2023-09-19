from _decimal import Decimal
from datetime import date, datetime

import pandas as pd

from demeter import TokenInfo, UniV3Pool, Actuator, Strategy, RowData, ChainType, MarketInfo, UniLpMarket, MarketDict, AtTimeTrigger
from demeter.aave._typing import AaveBalance, InterestRateMode
from demeter.aave.market import AaveV3Market
from demeter.broker._typing import MarketTypeEnum

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class MyFirstStrategy(Strategy):
    def initialize(self):
        pass

    def on_bar(self, row_data: MarketDict[RowData]):
        # row_data[market_key].
        balance: AaveBalance = aave_market.get_market_balance()
        local_market_var: AaveV3Market = self.broker.markets[market_key]

        if balance.supply_balance > Decimal(0):
            key1 = aave_market.supply(usdc, Decimal(200))
        if balance.health_factor > 0.8:
            key2 = aave_market.supply(usdc, Decimal(200), collateral=True)

        print(balance.supply_balance)
        print(balance.supplys)

        if balance.supplys[key1].apy < 0.1:  # 10%
            aave_market.withdraw(token=usdc, amount=Decimal(10))

        key_borrow = aave_market.borrow(usdc, Decimal(10), InterestRateMode.variable)

        if aave_market.borrows[key_borrow].apy < Decimal(0.1) or aave_market.get_borrow(key_borrow).apy < Decimal(0.1):
            aave_market.repay(amount=None, key=key_borrow)


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)  # declare token usdc
    eth = TokenInfo(name="eth", decimal=18)  # declare token eth

    market_key = MarketInfo("aave_market", MarketTypeEnum.aave_v3)
    aave_market = AaveV3Market(market_info=market_key, risk_parameters_path="../../tests/aave_risk_parameters/polygon.csv", tokens=[usdc, eth])
    aave_market.load_data()

    actuator = Actuator()  # declare actuator, Demeter Actuator (broker:assets: ; markets: )
    actuator.broker.add_market(aave_market)
    actuator.broker.set_balance(usdc, 10000)
    actuator.broker.set_balance(eth, 10)
    actuator.strategy = MyFirstStrategy()
    actuator.set_price(how_to_get_price())
    actuator.run()
