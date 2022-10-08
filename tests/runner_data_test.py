import unittest
from datetime import date
import numpy as np
import demeter.indicator
from demeter.broker.v3_core import V3CoreLib
from download import ChainType
from demeter import Broker, TokenInfo, PoolBaseInfo, Runner, Strategy, Asset, Lines
import pandas as pd
from decimal import Decimal

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)

pd.options.display.max_columns = None
pd.options.display.max_rows = None
pd.set_option('display.width', 5000)


class WithSMA(Strategy):

    def next(self, time, row_data: Lines):
        if row_data.row_id == 0:
            tick = self.broker.price_to_tick(row_data.price)
            price_high = self.broker.tick_to_price(tick - 1000)
            price_low = self.broker.tick_to_price(tick + 1000)
            self.add_liquidity(self.broker.base_asset.balance,
                               self.broker.quote_asset.balance,
                               price_low, price_high)


class TestRunner(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = PoolBaseInfo(usdc, eth, 0.05, usdc)
        super(TestRunner, self).__init__(*args, **kwargs)

    def get_clean_data(self, runner: Runner, tick, amount0=0, amount1=0, total_l=0):
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
        runner.add_statistic_column(df)
        lines = Lines.from_dataframe(df)
        return lines

    def test_load_clean_data(self):
        runner = Runner(self.pool)
        runner.strategy = WithSMA()
        runner.set_assets([Asset(usdc, 1000), Asset(eth, 1)])
        tick = runner.broker.price_to_tick(1000)
        token0_used, token1_used, position_info = V3CoreLib.new_position(self.pool,
                                                                         Decimal(100000),
                                                                         Decimal(100),
                                                                         tick - 1000,
                                                                         tick + 1000,
                                                                         tick)
        print(token0_used, token1_used, position_info)
        runner.data = self.get_clean_data(runner,
                                          tick,
                                          1000 * 10 ** usdc.decimal,
                                          1 * 10 ** eth.decimal,
                                          int(position_info.liquidity))

        runner.run()
        runner.output()
