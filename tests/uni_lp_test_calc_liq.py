import math
import unittest
from decimal import Decimal

import pandas as pd

from demeter import TokenInfo, Broker, MarketInfo, MarketStatus
from demeter.uniswap import UniLpMarket, UniV3Pool
from demeter.uniswap.liquitidy_math import estimate_ratio

test_market = MarketInfo("market1")


class TestLiqCalc(unittest.TestCase):
    def test_liq_calc_1_quote(self):
        print("==================== 1:1 ====================")
        TestLiqCalc.compare_liq_calc(18, 6, 3000)
        TestLiqCalc.compare_liq_calc(8, 6, 5000)
        TestLiqCalc.compare_liq_calc(8, 18, 6000)
        print("==================== -5000:10000 ====================")
        TestLiqCalc.compare_liq_calc(8, 6, 5000, True, 5000, 10000)
        TestLiqCalc.compare_liq_calc(8, 18, 6000, True, 5000, 10000)
        print("==================== -10000:1000 ====================")
        TestLiqCalc.compare_liq_calc(8, 6, 5000, True, 10000, 1000)
        TestLiqCalc.compare_liq_calc(8, 18, 6000, True, 10000, 1000)

    def test_liq_calc_0_quote(self):
        print("==================== 1:1 ====================")
        TestLiqCalc.compare_liq_calc(18, 6, 3000, False)
        TestLiqCalc.compare_liq_calc(8, 6, 5000, False)
        TestLiqCalc.compare_liq_calc(8, 18, 6000, False)
        print("==================== -5000:10000 ====================")
        TestLiqCalc.compare_liq_calc(8, 6, 5000, False, 5000, 10000)
        TestLiqCalc.compare_liq_calc(8, 18, 6000, False, 5000, 10000)
        print("==================== -1000:10000 ====================")
        TestLiqCalc.compare_liq_calc(8, 6, 5000, False, 1000, 10000)
        TestLiqCalc.compare_liq_calc(8, 18, 6000, False, 1000, 10000)
        print("==================== -10000:1000 ====================")
        TestLiqCalc.compare_liq_calc(8, 6, 5000, False, 10000, 1000)
        TestLiqCalc.compare_liq_calc(8, 18, 6000, False, 10000, 1000)
        TestLiqCalc.compare_liq_calc(4, 16, 1000, False, 10000, 1000)

    @staticmethod
    def compare_liq_calc(decimal0, decimal1, price, is_1_quote=True, lower_tick_diff=5000, upper_tick_diff=5000):
        token0 = TokenInfo(name="token0", decimal=decimal0)
        token1 = TokenInfo(name="token1", decimal=decimal1)
        quote_token = token1 if is_1_quote else token0
        pool = UniV3Pool(token0=token0, token1=token1, fee=0.3, quote_token=quote_token)
        broker = Broker()
        market = UniLpMarket(test_market, pool)
        broker.add_market(market)
        tick = market.price_to_tick(price)
        price_from_tick = market.tick_to_price(tick)
        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[0, 0, 0, tick, price_from_tick],
                    index=["inAmount0", "inAmount1", "currentLiquidity", "closeTick", "price"],
                ),
            ),
            price=None,
        )
        ratio = estimate_ratio(tick, tick - lower_tick_diff, tick + upper_tick_diff)
        ratio_in_amount = ratio * 10 ** (token1.decimal - token0.decimal)
        ratio_in_value = Decimal(ratio_in_amount) * price if is_1_quote else Decimal(ratio_in_amount) / price
        # ensure total value is 1 unit, and all token will be used in LP
        token1_value = 1 / (ratio_in_value + 1)
        token0_value = 1 - token1_value

        if is_1_quote:
            broker.set_balance(token0, token0_value / price_from_tick)
            broker.set_balance(token1, token1_value)
        else:
            broker.set_balance(token1, token1_value / price_from_tick)
            broker.set_balance(token0, token0_value)

        priceL = market.tick_to_price(market.market_status.data.closeTick - lower_tick_diff)
        priceH = market.tick_to_price(market.market_status.data.closeTick + upper_tick_diff)
        if not is_1_quote:
            priceL, priceH = priceH, priceL
        (new_position, base_used, quote_used, liquidity) = market.add_liquidity(priceL, priceH)
        # !!!!!!!!
        calc_liq_of_1_unit = 10 ** ((market.token0.decimal + market.token1.decimal) / 2) / (
            math.sqrt(price_from_tick)
            * (2 - math.sqrt(priceL / price_from_tick) - 1 / math.sqrt(priceH / price_from_tick))
        )
        print(f"----------{decimal0} - {decimal1} - {quote_token.name}-------------")
        print(f"liq calc : {calc_liq_of_1_unit}")
        print(f"liquidity: {liquidity}")
