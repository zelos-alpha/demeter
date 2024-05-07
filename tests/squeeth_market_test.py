from datetime import datetime, date
from decimal import Decimal
from unittest import TestCase

import numpy as np
import pandas as pd

from demeter import MarketStatus, TokenInfo, Broker, MarketInfo, MarketTypeEnum
from demeter.squeeth.market import SqueethMarket
from demeter.uniswap import UniLpMarket, UniV3Pool, UniswapMarketStatus

weth = TokenInfo("weth", 18)
oSQTH = TokenInfo("osqth", 18)

osqth_pool = MarketInfo("Uni", MarketTypeEnum.uniswap_v3)
squeeth_key = MarketInfo("Squeeth", MarketTypeEnum.squeeth)

d4 = Decimal("0.0001")
OSQTH_ETH = Decimal("18.65573666468601")  # osqth/eth, osqth is base
ETH_OSQTH = Decimal("0.05360281493964960270664351043")


class TestSqueethMarket(TestCase):
    def test_get_twap_price(self):
        t = pd.date_range(datetime(2024, 1, 1), datetime(2024, 1, 1, 0, 7), freq="min")
        data = pd.DataFrame(
            index=t,
            data={
                "norm_factor": [0, 0, 0, 0, 0, 0, 0, 0],
                "ETH": [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007],
                "OSQTH": [100, 101, 102, 103, 104, 105, 106, 107],
            },
        )
        market = SqueethMarket(squeeth_key, None, data)
        market.set_market_status(MarketStatus(datetime(2024, 1, 1, 0, 7)), None)
        price = market._get_twap_price(TokenInfo("eth", 18))
        self.assertEqual(price, 1003.9980079631864)

    def test_get_twap_price_short(self):
        t = pd.date_range(datetime(2024, 1, 1), datetime(2024, 1, 1, 0, 7), freq="min")
        data = pd.DataFrame(
            index=t,
            data={
                "norm_factor": [0, 0, 0, 0, 0, 0, 0, 0],
                "ETH": [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007],
                "OSQTH": [100, 101, 102, 103, 104, 105, 106, 107],
            },
        )
        market = SqueethMarket(squeeth_key, None, data)
        market.set_market_status(MarketStatus(datetime(2024, 1, 1, 0, 1)), None)
        price = market._get_twap_price(TokenInfo("eth", 18))
        self.assertEqual(price, 1000.49987506246)

    def test_load_data(self):
        market = SqueethMarket(squeeth_key, None)
        market.load_data(date(2023, 8, 14), date(2023, 8, 17))
        self.assertEqual(len(market.data.index), 5760)
        self.assertEqual(market.data.head(1).index[0], datetime(2023, 8, 14))
        self.assertEqual(market.data.tail(1).index[0], datetime(2023, 8, 17, 23, 59))
        pass

    def test_get_price(self):
        market = SqueethMarket(squeeth_key, None)
        market.load_data(date(2023, 8, 14), date(2023, 8, 17))
        price_df = market.get_price_from_data()
        self.assertEqual(price_df.iloc[0]["WETH"], 1839.222732716025)
        self.assertEqual(price_df.iloc[0]["OSQTH"], 98.64923946816276)
        pass

    def test_long_buy(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        from_amount = OSQTH_ETH
        fee, eth_amount, osqth_amount = market.buy_squeeth(from_amount)
        self.assertEqual(osqth_amount, from_amount)
        self.assertEqual(eth_amount.quantize(d4), Decimal(1).quantize(d4))
        self.assertEqual(fee.quantize(d4), Decimal("0.003").quantize(d4))
        self.assertEqual(broker.get_token_balance(weth).quantize(d4), (10 - fee - eth_amount).quantize(d4))
        self.assertEqual(broker.get_token_balance(oSQTH).quantize(d4), (OSQTH_ETH * 10 + osqth_amount).quantize(d4))

    def test_long_sell(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        from_amount = OSQTH_ETH
        fee, eth_amount, osqth_amount = market.sell_squeeth(from_amount)
        # self.assertEqual(osqth_amount, from_amount)
        self.assertEqual(eth_amount.quantize(d4), Decimal("0.997").quantize(d4))
        self.assertEqual(fee.quantize(d4), Decimal("0.003").quantize(d4))
        self.assertEqual(broker.get_token_balance(weth).quantize(d4), Decimal(10.997).quantize(d4))
        self.assertEqual(broker.get_token_balance(oSQTH).quantize(d4), (OSQTH_ETH * 10 - from_amount).quantize(d4))

    def get_broker(self):
        broker = Broker()
        uni_market = UniLpMarket(
            osqth_pool,
            UniV3Pool(weth, oSQTH, 0.3, weth),
        )
        squeeth_market = SqueethMarket(squeeth_key, uni_market)
        broker.add_market(uni_market)
        broker.add_market(squeeth_market)
        tick = 29263  # uni_market.price_to_tick(0.0536)
        price = uni_market.tick_to_price(tick)  # Decimal('0.05360281493964960270664351043')
        uni_market.set_market_status(
            UniswapMarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[0, 0, 0, tick, price],
                    index=["inAmount0", "inAmount1", "currentLiquidity", "closeTick", "price"],
                ),
            ),
            price=None,
        )
        squeeth_market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[0.2894, 1839.2227, float(ETH_OSQTH)],
                    index=["norm_factor", "WETH", "OSQTH"],
                ),
            ),
            price=None,
        )
        broker.set_balance(weth, 10)
        broker.set_balance(oSQTH, OSQTH_ETH * 10)  # almost 1:1 in value
        return broker
