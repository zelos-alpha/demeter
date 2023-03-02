import unittest
from decimal import Decimal

import pandas as pd

from demeter import TokenInfo, UniV3Pool, Actuator, Strategy, MarketDict, RowData, MarketInfo, UniLpMarket
from demeter.uniswap import UniLpBalance
from demeter.uniswap.core import V3CoreLib
from demeter.uniswap.liquitidy_math import get_sqrt_ratio_at_tick

pd.options.display.max_columns = None
pd.options.display.max_rows = None
pd.set_option('display.width', 5000)

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)
test_market = MarketInfo("uni_market")


class WithSMA(Strategy):

    def on_bar(self, row_data: MarketDict[RowData | pd.Series]):
        if row_data[test_market].row_id == 0:
            market: UniLpMarket = self.broker.markets[test_market]
            tick = market.price_to_tick(row_data[test_market].price)
            price_high = market.tick_to_price(tick - 1000)
            price_low = market.tick_to_price(tick + 1000)
            market.add_liquidity(price_low,
                                 price_high)


def get_clean_data(market: UniLpMarket, tick, amount0=0, amount1=0, total_l=Decimal(0)):
    DATA_SIZE = 5
    index = pd.date_range('2022-10-8 8:0:0', periods=DATA_SIZE, freq='T')
    netAmount0 = pd.Series(data=[0] * DATA_SIZE, index=index)
    netAmount1 = pd.Series(data=[0] * DATA_SIZE, index=index)
    closeTick = pd.Series(data=[tick] * DATA_SIZE, index=index)
    openTick = pd.Series(data=[tick] * DATA_SIZE, index=index)
    lowestTick = pd.Series(data=[tick] * DATA_SIZE, index=index)
    highestTick = pd.Series(data=[tick] * DATA_SIZE, index=index)
    inAmount0 = pd.Series(data=[amount0] * DATA_SIZE, index=index)
    inAmount1 = pd.Series(data=[amount1] * DATA_SIZE, index=index)
    currentLiquidity = pd.Series(data=[Decimal(total_l)] * DATA_SIZE, index=index)
    df = pd.DataFrame(index=index)
    df["netAmount0"] = netAmount0
    df["netAmount1"] = netAmount1
    df["closeTick"] = closeTick
    df["openTick"] = openTick
    df["lowestTick"] = lowestTick
    df["highestTick"] = highestTick
    df["inAmount0"] = inAmount0
    df["inAmount1"] = inAmount1
    df["currentLiquidity"] = currentLiquidity
    market.add_statistic_column(df)
    return df


class TestActuator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = UniV3Pool(usdc, eth, 0.05, usdc)

        super(TestActuator, self).__init__(*args, **kwargs)

    def test_load_clean_data(self):
        eth = TokenInfo(name="eth", decimal=18)
        usdc = TokenInfo(name="usdc", decimal=6)

        actuator: Actuator = Actuator()  # declare actuator
        actuator.strategy = WithSMA()

        broker = actuator.broker
        market = UniLpMarket(test_market, self.pool)
        tick = market.price_to_tick(1000)

        broker.add_market(market)
        broker.set_balance(usdc, 1000)
        broker.set_balance(eth, 1)

        token0_used, token1_used, liquidity, position_info = V3CoreLib.new_position(self.pool,
                                                                                    Decimal(100000),
                                                                                    Decimal(100),
                                                                                    tick - 1000,
                                                                                    tick + 1000,
                                                                                    get_sqrt_ratio_at_tick(tick))
        print(token0_used, token1_used, position_info, liquidity)
        market.data = get_clean_data(market,
                                     tick,
                                     1000 * 10 ** usdc.decimal,
                                     1 * 10 ** eth.decimal,
                                     liquidity)
        actuator.set_price(market.get_price_from_data())
        actuator.run()

        status: UniLpBalance = broker.get_account_status(actuator.token_prices.iloc[-1]).market_status[test_market]
        self.assertEqual(status.base_uncollected.quantize(Decimal('1.0000')), Decimal("0.025"))
        self.assertEqual(status.quote_uncollected.quantize(Decimal('1.0000000')), Decimal("0.0000250"))
