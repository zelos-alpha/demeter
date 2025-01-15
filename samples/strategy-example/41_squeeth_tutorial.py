from datetime import datetime, date

import pandas as pd

from demeter import TokenInfo, MarketInfo, MarketTypeEnum, Strategy, Actuator, AtTimeTrigger, Snapshot, ChainType
from demeter.squeeth import SqueethMarket
from demeter.squeeth.helper import load_squeeth_data
from demeter.uniswap import UniLpMarket, UniV3Pool, load_uni_v3_data

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)

weth = TokenInfo("weth", 18)
oSQTH = TokenInfo("osqth", 18)

osqth_pool = MarketInfo("Uni", MarketTypeEnum.uniswap_v3)
squeeth_key = MarketInfo("Squeeth", MarketTypeEnum.squeeth)


class SimpleShortStrategy(Strategy):
    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2023, 8, 17, 23, 56, 0), do=self.short)
        self.triggers.append(new_trigger)

    def short(self, row_data: Snapshot):
        market: SqueethMarket = self.broker.markets[squeeth_key]
        market.open_deposit_mint_by_collat_rate(10)

    def notify(self, action):
        print(action)


if __name__ == "__main__":
    actuator = Actuator()

    pool = UniV3Pool(weth, oSQTH, 0.3, weth)
    uni_market = UniLpMarket(osqth_pool, pool)
    uni_market.data = load_uni_v3_data(
        pool,
        ChainType.ethereum.name,
        "0x82c427adfdf2d245ec51d8046b41c4ee87f0d29c",
        date(2023, 8, 17),
        date(2023, 8, 17),
        data_path="../../tests/data",
    )
    squeeth_market = SqueethMarket(squeeth_key, uni_market)
    squeeth_market.data = load_squeeth_data(date(2023, 8, 17), date(2023, 8, 17), data_path="../../tests/data")
    actuator.broker.add_market(uni_market)
    actuator.broker.add_market(squeeth_market)
    actuator.broker.set_balance(weth, 10)
    price_df = squeeth_market.get_price_from_data()
    actuator.set_price(price_df)
    actuator.strategy = SimpleShortStrategy()
    actuator.run()
