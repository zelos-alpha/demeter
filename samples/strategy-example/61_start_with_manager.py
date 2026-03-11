from datetime import date, datetime

import pandas as pd

import demeter.uniswap as uniswap
from demeter import (
    TokenInfo,
    Strategy,
    Snapshot,
    ChainType,
    MarketInfo,
    AtTimeTrigger,
    BacktestManager,
    StrategyConfig,
    BacktestConfig,
    BacktestData,
)

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class DemoStrategy(Strategy):

    def __init__(self):
        super().__init__()
        self.some_record = []

    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 12, 0, 0), do=self.add)
        self.triggers.append(new_trigger)


    def on_bar(self, snapshot: Snapshot):
        self.some_record.append({"custom1": snapshot.market_status[market_key]["openTick"]})

    def add(self, snapshot: Snapshot):
        lp_market: uniswap.UniLpMarket = self.markets[market_key]  # pick our market.
        self.new_position, amount0_used, amount1_used, liquidity = lp_market.add_liquidity(1000, 4000)  # add liquidity
        self.comment_last_action("Add liquidity because ...")  # add comment to last transaction

"""
This demo shows how to work with BacktestManager. 
BacktestManager is a backtesting engine that allows multiple strategies to be executed concurrently, 
reducing the overall backtesting time.

"""

if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)
    eth = TokenInfo(name="eth", decimal=18)
    pool = uniswap.UniV3Pool(usdc, eth, 0.05, usdc)

    market_key = MarketInfo("market1")  # market1
    market = uniswap.UniLpMarket(market_key, pool)

    # We have several things to config:
    # 1. StrategyConfig, you can set initial asset and market here
    strategy_config = StrategyConfig(
        assets={usdc: 10000, eth: 10},
        markets=[market],
    )
    # 2. data.
    # As data is shared in all subprocess, it should be loaded outside the market.
    data_df = uniswap.load_uni_v3_data(
        pool,
        ChainType.polygon.name,
        "0x45dda9cb7c25131df268515131f647d726f50608",
        date(2023, 8, 15),
        date(2023, 8, 16),
        "../data",
    )
    price_df = uniswap.get_price_from_data(data_df, pool)

    # 3. Create a BacktestManager instance, set your strategy, configs and data.
    backtest = BacktestManager(
        config=strategy_config,
        data=BacktestData({market_key: data_df}, price_df),
        strategies=[DemoStrategy()],
        backtest_config=BacktestConfig(),
    )
    # As we have only on strategy, backtest will run in main process.
    backtest.run()
    pass
