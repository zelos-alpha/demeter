import unittest
import datetime
from decimal import Decimal

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

    def _get_market(self):
        market = GmxV2PerpMarket(self.market_info, self.pool)
        data = load_gmx_v2_data(
            ChainType.arbitrum,
            "0x70d95587d40a2caf56bd97485ab3eec10bee6336",
            datetime.date(2025, 6, 22),
            datetime.date(2025, 6, 24),
            "/data/gmx_v2/arbitrum",
        )
        price = get_price_from_v2_data(data, self.pool)
        return market, data, price

    def test_swap(self):
        # https://arbiscan.io/tx/0x27a582fa983d4c9a6d052f1d0b645763557ac2ac40b405fc4efc3d5c19bdb3f8
        # usdc to eth, price impact is positive
        market, data, price = self._get_market()
        t = pd.Timestamp("2025-6-22 23:37:00")
        market.data = data
        market.set_market_status(GmxV2LpMarketStatus(timestamp=t, data=data.loc[t]), price.loc[t])

        token, amount, param = market._do_swap(self.usdc, 1237.5)
        print(token, amount, param)
        error = 1 - amount / Decimal("0.555599441")
        self.assertLess(abs(error), 0.00001)
        print(error)
        pass

    def test_swap2(self):
        # https://arbiscan.io/tx/0x68cf7d2aac40cb0ab2c92a95f74bdde9aa1ffaf7634654efca786d3c7f3d4e0b
        # eth to usdc, price impact is negative, virtual inventory price impact is involved
        market, data, price = self._get_market()
        t = pd.Timestamp("2025-6-24 15:20:00")
        market.data = data
        # As price was resampled to minute, the price in data is not exactly same to the price in this transaction
        # this would lead to some error, to verify the calcation I replace resampled price to accurate price.
        data.loc[t, "longPrice"] = 2432.049511609755
        data.loc[t, "shortPrice"] = 0.999922596191246750000000
        market.set_market_status(GmxV2LpMarketStatus(timestamp=t, data=data.loc[t]), price.loc[t])

        token, amount, param = market._do_swap(self.weth, 50.518610000000000000)
        print(token, amount, param)

        error = 1 - amount / Decimal("122651.632171")
        self.assertLess(abs(error), 0.00001)
        print(error)
        pass
