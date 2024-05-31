import unittest
from datetime import date
from decimal import Decimal

import pandas as pd

import demeter
from demeter import TokenInfo, Broker, MarketInfo, ChainType, MarketStatus
from demeter.uniswap import UniLpMarket, UniV3Pool, UniV3PoolStatus, UniswapMarketStatus

test_market = MarketInfo("market1")

d4 = Decimal("0.0001")
d2 = Decimal("0.01")

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)
pool = UniV3Pool(eth, usdc, 0.05, usdc)

tick = -207243
price = None


class TestAddLiqByValueToken1IsQuote(unittest.TestCase):
    def __init__(self, *args, **kwargs):

        super(TestAddLiqByValueToken1IsQuote, self).__init__(*args, **kwargs)

    def get_broker(self):
        broker = Broker()
        market = UniLpMarket(test_market, pool)
        broker.add_market(market)
        global price
        price = market.tick_to_price(tick)  # 1000.002
        market.set_market_status(
            UniswapMarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[0, 0, 0, tick, price],
                    index=["inAmount0", "inAmount1", "currentLiquidity", "closeTick", "price"],
                ),
            ),
            price=None,
        )
        # balance : 1 eth + 1 eth worth usdc
        broker.set_balance(eth, 1)
        broker.set_balance(usdc, price * 1)
        return broker

    def add_liq_by_value(self, lower_tick_diff, upper_tick_diff, eth_amount):

        broker = self.get_broker()
        market: UniLpMarket = broker.markets.market1
        tick = market.market_status.data["closeTick"]
        price = market.tick_to_price(tick)
        old_amount0 = broker.get_token_balance(pool.token0)
        old_amount1 = broker.get_token_balance(pool.token1)
        lower_tick = tick + lower_tick_diff
        upper_tick = tick + upper_tick_diff

        created_position, base_used, quote_used, liquidity = market.add_liquidity_by_value(
            lower_tick, upper_tick, eth_amount * price
        )
        new_amount0, new_amount1 = broker.get_token_balance(pool.token0), broker.get_token_balance(pool.token1)
        print("==============================================")
        print(f"tick and range {tick} ({lower_tick}, {upper_tick})")
        print("old balance", old_amount0, old_amount1)
        print("used", quote_used, base_used)
        print("new balance", new_amount0, new_amount1)
        return broker, market, old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1

    def test_higher_than_upper(self):
        broker, market, old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1 = (
            self.add_liq_by_value(-20000, -10000, Decimal(1))
        )
        # broker balance eth:1 eth, usdc:1eth
        # will add 1 eth liquidity, so eth balance will be 0, usdc not change
        self.assertEqual(old_amount0, new_amount0)
        self.assertEqual(new_amount1, Decimal(0))

    def test_lower_than_lower(self):
        broker, market, old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1 = (
            self.add_liq_by_value(10000, 20000, Decimal(1))
        )
        # broker balance eth:1 eth, usdc:1eth
        # will add usdc (value is 1 eth) liquidity, so usdc balance will be 0, eth not change
        self.assertEqual(new_amount0, Decimal(0))

        self.assertEqual(old_amount1, new_amount1)

    @staticmethod
    def get_fee(old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1):
        return old_amount0 * price + old_amount1 - base_used * price - quote_used - new_amount0 * price - new_amount1

    def test_higher_than_upper_all_balance(self):
        broker, market, old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1 = (
            self.add_liq_by_value(-20000, -10000, Decimal(2))
        )
        # broker balance eth:1 eth, usdc:1eth
        # will add 2 eth, so all eth and usdc will be used.
        # but tick is higher than upper, so this time will add usdc. We have to convert eth to usdc first
        # fee will be charged
        self.assertEqual(new_amount0, Decimal(0))
        self.assertEqual(new_amount1, Decimal(0))
        self.assertEqual(quote_used.quantize(d2), Decimal("1999.5"))
        self.assertEqual(base_used, Decimal(0))
        # fee
        self.assertEqual(
            (price * pool.fee_rate).quantize(d4),
            TestAddLiqByValueToken1IsQuote.get_fee(
                old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1
            ).quantize(d4),
        )

    def test_lower_than_lower_all_balance(self):
        broker, market, old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1 = (
            self.add_liq_by_value(10000, 20000, Decimal(2))
        )
        # broker balance eth:1 eth, usdc:1eth
        # will add 2 eth, so all eth and usdc will be used.
        # but tick is lower than lower, so this time will add eth. We have to convert usdc to eth first
        # fee will be charged
        self.assertEqual(new_amount0, Decimal(0))
        self.assertEqual(new_amount1, Decimal(0))
        self.assertEqual(base_used.quantize(d4), Decimal("1.9995"))
        self.assertEqual(quote_used, Decimal(0))

    def test_in_range_token0_token1_enough_1_1(self):
        broker, market, old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1 = (
            self.add_liq_by_value(-10000, 10000, Decimal(1))  # will use usdc:eth=1:1
        )
        self.assertEqual(new_amount1.quantize(d4), (Decimal("0.5") * price).quantize(d4))
        self.assertEqual(new_amount0.quantize(d4), Decimal("0.5"))
        self.assertEqual(base_used.quantize(d4), Decimal("0.5"))
        self.assertEqual(quote_used.quantize(d4), (Decimal("0.5") * price).quantize(d4))

    def test_in_range_token0_token1_enough_1_3(self):
        broker, market, old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1 = (
            self.add_liq_by_value(-29990, 5993, Decimal(1))  # will use usdc:eth=3:1
        )
        self.assertEqual(new_amount0.quantize(d4), (Decimal(0.75)).quantize(d4))
        self.assertEqual(new_amount1.quantize(d2), (Decimal(0.25) * price).quantize(d2))
        self.assertEqual(quote_used.quantize(d2), (Decimal(0.75) * price).quantize(d2))
        self.assertEqual(base_used.quantize(d4), (Decimal(0.25)).quantize(d4))
        self.assertEqual(
            Decimal(0),
            TestAddLiqByValueToken1IsQuote.get_fee(
                old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1
            ).quantize(d4),
        )

    def test_in_range_token0_token1_not_enough_1_3(self):
        # will use usdc:eth=3:1
        # so transfer some eth to usdc, and eth will be left
        broker, market, old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1 = (
            self.add_liq_by_value(-29990, 5993, Decimal(1.6))  # will use usdc:eth=3:1
        )
        self.assertEqual(new_amount0.quantize(d4), Decimal(0.4).quantize(d4))
        self.assertEqual(new_amount1.quantize(d4), Decimal(0).quantize(d4))
        self.assertEqual((quote_used / base_used / price).quantize(d4), Decimal(3).quantize(d4))
        self.assertEqual(
            self.get_fee(old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1).quantize(d4),
            (price * Decimal("0.2") * pool.fee_rate).quantize(d4),
        )

    def test_in_range_token0_token1_use_all_1_3(self):
        # will use usdc:eth=3:1
        # so transfer some 0.5 eth to usdc
        # fee is (0.5 * fee_rate) eth
        broker, market, old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1 = (
            self.add_liq_by_value(-29990, 5993, Decimal(2))
        )
        self.assertEqual(new_amount0, Decimal(0))
        self.assertEqual(new_amount1, Decimal(0))
        self.assertEqual((quote_used / base_used / price).quantize(d4), Decimal(3).quantize(d4))
        self.assertEqual(  # check fee
            (Decimal(2) * price - base_used * price - quote_used).quantize(d4), (price / 2 * pool.fee_rate).quantize(d4)
        )

    def test_in_range_token0_token1_use_all_3_1(self):
        # will use usdc:eth=1:3
        # so transfer some 0.5 usdc to eth
        # fee is (0.5 * fee_rate) eth
        broker, market, old_amount0, old_amount1, base_used, quote_used, new_amount0, new_amount1 = (
            self.add_liq_by_value(-5993,29990 , Decimal(2))
        )
        self.assertEqual(new_amount0, Decimal(0))
        self.assertEqual(new_amount1, Decimal(0))
        self.assertEqual((quote_used / base_used / price).quantize(d4), Decimal(1/3).quantize(d4))
        self.assertEqual(  # check fee
            (Decimal(2) * price - base_used * price - quote_used).quantize(d4), (price / 2 * pool.fee_rate).quantize(d4)
        )