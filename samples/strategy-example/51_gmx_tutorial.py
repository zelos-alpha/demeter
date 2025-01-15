from datetime import date, datetime
from decimal import Decimal
import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, Snapshot, ChainType, MarketInfo, AtTimeTrigger, MarketTypeEnum
from demeter.gmx import GmxMarket, load_gmx_v1_data

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class GmxStrategy(Strategy):
    def initialize(self):
        buy_trigger = AtTimeTrigger(time=datetime(2024, 10, 15, 1, 52, 0), do=self.buy_glp)
        sell_trigger = AtTimeTrigger(time=datetime(2024, 10, 16, 14, 25, 0), do=self.sell_glp)
        self.triggers.extend([buy_trigger, sell_trigger])

    def buy_glp(self, _: Snapshot):
        market.buy_glp(weth, Decimal("0.000455889485162217"))

    def sell_glp(self, _: Snapshot):
        market.sell_glp(weth)



if __name__ == "__main__":
    market_key = MarketInfo("gmx", MarketTypeEnum.gmx_v1)
    tokens = [
        TokenInfo(name="btc.b", decimal=8),
        TokenInfo(name="weth", decimal=18),
        TokenInfo(name="wbtc", decimal=8),
        TokenInfo(name="wavax", decimal=18),
        TokenInfo(name="mim", decimal=18),
        TokenInfo(name="usdc.e", decimal=6),
        TokenInfo(name="usdc", decimal=6),
    ]
    market = GmxMarket(market_key, tokens=tokens)

    market.data = load_gmx_v1_data(
        chain=ChainType.avalanche,
        start_date=date(2024, 10, 15),
        end_date=date(2024, 10, 16),
        data_path="../data",
    )
    actuator = Actuator()
    actuator.broker.add_market(market)
    weth = TokenInfo(name="weth", decimal=18)
    actuator.broker.set_balance(weth, 0.000455889485162217)
    actuator.strategy = GmxStrategy()
    actuator.set_price(market.get_price_from_data())
    actuator.run()
