from datetime import datetime, date, timedelta

import pandas as pd

from demeter import Strategy, AtTimeTrigger, MarketInfo, Actuator, RowData, MarketTypeEnum
from demeter.deribit import DeribitOptionMarket

market_key = MarketInfo("option_test", MarketTypeEnum.deribit_option)

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class SimpleStrategy(Strategy):
    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2024, 2, 15, 12, 0, 0), do=self.buy)
        self.triggers.append(new_trigger)

    def buy(self, row_data: RowData):
        market: DeribitOptionMarket = self.broker.markets.default
        market.buy("ETH-26APR24-2700-C", 20)

    def notify(self, action):
        print(action)


if __name__ == "__main__":
    market = DeribitOptionMarket(market_key, DeribitOptionMarket.ETH, data_path="../../tests/data")
    market.load_data(date(2024, 2, 15), date(2024, 2, 16))
    actuator = Actuator()
    actuator.broker.add_market(market)
    actuator.broker.set_balance(DeribitOptionMarket.ETH, 10)
    market.deposit(10)
    actuator.strategy = SimpleStrategy()
    actuator.set_price(market.get_price_from_data())
    actuator.run()
    actuator.save_result(path="./result", file_name="deribit", decimals=3)
