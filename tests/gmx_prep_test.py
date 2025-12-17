import unittest
import datetime

from demeter import TokenInfo, MarketInfo, MarketTypeEnum, ChainType
from demeter.gmx import GmxV2Pool, GmxV2PerpMarket, load_gmx_v2_data, get_price_from_v2_data


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
            datetime.date(2025, 12, 15),
            datetime.date(2025, 12, 15),
            "/data/gmx_v2/arbitrum",
        )
        price = get_price_from_v2_data(data, self.pool)
        return market, data, price

    def test_position_balance(self):
        market, data, price = self._get_market()
