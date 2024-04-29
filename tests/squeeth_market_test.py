from datetime import datetime
from unittest import TestCase

import numpy as np
import pandas as pd

from demeter import MarketStatus, TokenInfo
from demeter.squeeth.market import SqueethMarket


class TestSqueethMarket(TestCase):
    def test_get_twap_price(self):
        t = pd.date_range(datetime(2024, 1, 1), datetime(2024, 1, 1, 0, 7), freq="min")
        data = pd.DataFrame(index=t, data={"norm_factor": [0, 0, 0, 0, 0, 0, 0, 0],
                                           "ETH": [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007],
                                           "OSQTH": [100, 101, 102, 103, 104, 105, 106, 107]})
        market = SqueethMarket(None, None, data)
        market.set_market_status(MarketStatus(datetime(2024, 1, 1, 0, 7)), None)
        price = market._get_twap_price(TokenInfo("eth", 18))
        self.assertEqual(price, 1003.9980079631864)

    def test_get_twap_price_short(self):
        t = pd.date_range(datetime(2024, 1, 1), datetime(2024, 1, 1, 0, 7), freq="min")
        data = pd.DataFrame(index=t, data={"norm_factor": [0, 0, 0, 0, 0, 0, 0, 0],
                                           "ETH": [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007],
                                           "OSQTH": [100, 101, 102, 103, 104, 105, 106, 107]})
        market = SqueethMarket(None, None, data)
        market.set_market_status(MarketStatus(datetime(2024, 1, 1, 0, 1)), None)
        price = market._get_twap_price(TokenInfo("eth", 18))
        self.assertEqual(price, 1000.49987506246)
