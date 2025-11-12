import unittest
import datetime

import pandas as pd

from demeter import MarketInfo, MarketTypeEnum, TokenInfo, ChainType
from demeter.gmx import GmxV2PerpMarket, GmxV2Pool, load_gmx_v2_data, get_price_from_v2_data
from demeter.gmx._typing2 import GmxV2LpMarketStatus


class TestActuator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestActuator, self).__init__(*args, **kwargs)
        self.market_info: MarketInfo = MarketInfo("GMX", MarketTypeEnum.gmx_v2_prep)
        self.usdc = TokenInfo(name="usdc", decimal=6)
        self.weth = TokenInfo(name="weth", decimal=18)
        self.pool: GmxV2Pool = GmxV2Pool(self.weth, self.usdc, self.weth)

    def test_swap(self):
        # https://arbiscan.io/tx/0x27a582fa983d4c9a6d052f1d0b645763557ac2ac40b405fc4efc3d5c19bdb3f8

        market = GmxV2PerpMarket(self.market_info, self.pool)
        data = load_gmx_v2_data(
            ChainType.arbitrum,
            "0x70d95587d40a2caf56bd97485ab3eec10bee6336",
            datetime.date(2025, 6, 22),
            datetime.date(2025, 6, 22),
            "/data/gmx_v2/arbitrum",
        )
        price = get_price_from_v2_data(data, self.pool)

        t = pd.Timestamp("2025-6-22 11:38:00")
        market.data = data
        market.set_market_status(GmxV2LpMarketStatus(timestamp=t, data=data.loc[t]), price.loc[t])

        market.swap(self.usdc, 1237.5)
        pass
