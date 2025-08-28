from datetime import date, datetime

import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, Snapshot, ChainType, MarketInfo, AtTimeTrigger, MarketTypeEnum
from demeter.gmx import GmxV2Market
from demeter.gmx._typing2 import GmxV2Pool

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class GmxV2PositionStrategy(Strategy):
    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2025, 7, 1, 0, 0, 0), do=self.work)
        self.triggers.append(new_trigger)
        pass

    def work(self, snapshot: Snapshot):
        gmx_market: GmxV2Market = self.markets[market_key]
        result = gmx_market.increase_position(
            initialCollateralToken=pool.short_token,
            initialCollateralDeltaAmount=3384,
            sizeDeltaUsd=3384,
            isLong=True
        )
        pass


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)
    weth = TokenInfo(name="weth", decimal=18)
    pool = GmxV2Pool(weth, usdc, weth)

    market_key = MarketInfo("GMX_ETH", MarketTypeEnum.gmx_v2)
    market = GmxV2Market(market_key, pool, data_path="../data")
    market.load_data(
        ChainType.arbitrum, "0x70d95587d40a2caf56bd97485ab3eec10bee6336", date(2025, 7, 1), date(2025, 7, 2)
    )

    actuator = Actuator()
    actuator.broker.add_market(market)
    actuator.broker.set_balance(usdc, 3384)
    actuator.broker.set_balance(weth, 1)
    actuator.strategy = GmxV2PositionStrategy()  # set strategy to actuator
    actuator.set_price(market.get_price_from_data())  # set actuator price
    actuator.run()
