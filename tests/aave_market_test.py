import unittest

import pandas as pd

from demeter import MarketInfo, ChainType
from demeter.aave.market import AaveV3Market
from demeter.broker._typing import MarketTypeEnum


class UniLpDataTest(unittest.TestCase):
    def test_load_risk_parameter(self):
        market = AaveV3Market(MarketInfo("aave_test", MarketTypeEnum.aave_v3), ChainType.polygon)
        pass
