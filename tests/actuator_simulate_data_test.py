import unittest
from decimal import Decimal

import numpy as np
import pandas as pd

from demeter import TokenInfo, PoolInfo, Actuator, Strategy, Asset, Lines, AccountStatus
from demeter.broker.liquitidymath import get_sqrt_ratio_at_tick
from demeter.broker.v3_core import V3CoreLib

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)

pd.options.display.max_columns = None
pd.options.display.max_rows = None
pd.set_option('display.width', 5000)


class WithSMA(Strategy):

    def on_bar(self, row_data: Lines):
        if row_data.row_id == 0:
            tick = self.broker.price_to_tick(row_data.price)
            price_high = self.broker.tick_to_price(tick - 1000)
            price_low = self.broker.tick_to_price(tick + 1000)
            self.add_liquidity(price_low, price_high, self.broker.base_asset.balance,
                               self.broker.quote_asset.balance)


def get_clean_data(actuator: Actuator, tick, amount0=0, amount1=0, total_l=0):
    DATA_SIZE = 5
    index = pd.date_range('2022-10-8 8:0:0', periods=DATA_SIZE, freq='T')
    netAmount0 = pd.Series(data=np.full(DATA_SIZE, 0), index=index)
    netAmount1 = pd.Series(data=np.full(DATA_SIZE, 0), index=index)
    closeTick = pd.Series(data=np.full(DATA_SIZE, tick), index=index)
    openTick = pd.Series(data=np.full(DATA_SIZE, tick), index=index)
    lowestTick = pd.Series(data=np.full(DATA_SIZE, tick), index=index)
    highestTick = pd.Series(data=np.full(DATA_SIZE, tick), index=index)
    inAmount0 = pd.Series(data=np.full(DATA_SIZE, amount0), index=index)
    inAmount1 = pd.Series(data=np.full(DATA_SIZE, amount1), index=index)
    currentLiquidity = pd.Series(data=np.full(DATA_SIZE, total_l), index=index)
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
    actuator.add_statistic_column(df)
    lines = Lines.from_dataframe(df)
    return lines


class TestActuator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = PoolInfo(usdc, eth, 0.05, usdc)
        super(TestActuator, self).__init__(*args, **kwargs)

    def test_load_clean_data(self):
        actuator = Actuator(self.pool)
        actuator.strategy = WithSMA()
        actuator.set_assets([Asset(usdc, 1000), Asset(eth, 1)])
        tick = actuator.broker.price_to_tick(1000)
        token0_used, token1_used, liquidity, position_info = \
            V3CoreLib.new_position(self.pool,
                                   Decimal(100000),
                                   Decimal(100),
                                   tick - 1000,
                                   tick + 1000,
                                   get_sqrt_ratio_at_tick(tick))
        print(token0_used, token1_used, position_info, liquidity)
        actuator.data = get_clean_data(actuator,
                                     tick,
                                     1000 * 10 ** usdc.decimal,
                                     1 * 10 ** eth.decimal,
                                     liquidity)

        actuator.run()
        # actuator.output()
        status: AccountStatus = actuator.final_status
        self.assertEqual(status.base_uncollected.quantize(Decimal('1.0000')), Decimal("0.025"))
        self.assertEqual(status.quote_uncollected.quantize(Decimal('1.0000000')), Decimal("0.0000250"))
