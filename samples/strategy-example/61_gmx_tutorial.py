from datetime import date, datetime

import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, RowData, ChainType, MarketInfo, AtTimeTrigger, MarketTypeEnum
from demeter.gmx import GmxMarket

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class GmxStrategy(Strategy):
    def initialize(self):
        buy_trigger = AtTimeTrigger(time=datetime(2024, 10, 1, 12, 0, 0), do=self.buy_glp)
        sell_trigger = AtTimeTrigger(time=datetime(2024, 10, 3, 12, 0, 0), do=self.sell_glp)
        self.triggers.extend([buy_trigger, sell_trigger])

    def buy_glp(self, row_data: RowData):
        market.buy_glp(weth, 5)

    def sell_glp(self, row_data: RowData):
        market.sell_glp(weth, 1000)

    def on_bar(self, row_data: RowData):
        pass


if __name__ == '__main__':
    market_key = MarketInfo("gmx", MarketTypeEnum.gmx)
    market = GmxMarket(market_key)
    market.data_path = "../data"
    market.load_data(
        chain=ChainType.avalanche,
        start_date=date(2024, 10, 1),
        end_date=date(2024, 10, 5)
    )
    actuator = Actuator()
    actuator.broker.add_market(market)
    weth = TokenInfo(name="weth", decimal=18, address="0x49d5c2bdffac6ce2bfdb6640f4f80f226bc10bab")
    actuator.broker.set_balance(weth, 10)
    actuator.strategy = GmxStrategy()
    actuator.set_price(market.get_price_from_data())
    actuator.run()
