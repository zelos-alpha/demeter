from datetime import date, datetime

import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, Snapshot, ChainType, MarketInfo, AtTimeTrigger
from demeter.gmx import GmxV2Market
from demeter.gmx._typing2 import GmxV2Pool
from demeter.uniswap import UniV3Pool, UniLpMarket, load_uni_v3_data, get_price_from_data

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class GmxV2LpStrategy(Strategy):
    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2025, 1, 8, 0, 0, 0), do=self.work)
        self.triggers.append(new_trigger)

    def work(self, snapshot: Snapshot):
        """
        When time is up, work function will be called.
        """
        lp_market: UniLpMarket = self.markets[market_key]  # pick our market.
        new_position, amount0_used, amount1_used, liquidity = lp_market.add_liquidity(1000, 4000)  # add liquidity
        pass


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)
    weth = TokenInfo(name="weth", decimal=18)
    pool = GmxV2Pool(weth, usdc, weth)

    market_key = MarketInfo("ETHUSDC")
    market = GmxV2Market(market_key, pool, data_path="../data")
    market.load_data(
        ChainType.arbitrum.name, "0x70d95587d40a2caf56bd97485ab3eec10bee6336", date(2025, 1, 8), date(2025, 1, 8)
    )

    actuator = Actuator()
    actuator.broker.add_market(market)
    actuator.broker.set_balance(usdc, 2000)
    actuator.broker.set_balance(weth, 1)
    actuator.strategy = GmxV2LpStrategy()  # set strategy to actuator
    actuator.set_price(market.get_price_from_data())  # set actuator price
    actuator.run()
