# Concurrent

Backtesting can often be time-consuming, and there may only be minor adjustments between different strategies. 
Therefore, concurrent execution is crucial for backtesting. 
Before version 1.0.0, to run backtests for multiple strategies in parallel, users had to manually start multiple processes. 
This approach was not only cumbersome but also resulted in high memory consumption due to the data being loaded multiple times. 
In version 1.0.0, we introduced the BacktestManager to address both of these issues.

The first function of the BacktestManager is to enable parallel execution of backtests. 
You can create different strategy instances and set the number of concurrent processes, allowing these strategies to run together in a process pool.

Another major benefit of the BacktestManager is reducing memory consumption during parallel backtesting. 
On Linux and macOS, multiple backtest processes can share a single copy of the backtest data, significantly reducing memory usage. 
However, on Windows, due to the subprocess spawning model, Windows cannot benefit from this optimization.

Here is an example of parallel execution

```python
class DemoStrategy(Strategy):
    """
    this demo shows how to handle backtest results.
    """

    def __init__(self, lp_range: Tuple[float, float]):
        super().__init__()
        self.some_record = []
        self.lp_range = lp_range

    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 12, 0, 0), do=self.add)
        self.triggers.append(new_trigger)

    def on_bar(self, snapshot: Snapshot):
        self.some_record.append({"custom1": snapshot.market_status[market_key]["openTick"]})

    def add(self, snapshot: Snapshot):
        lp_market: uniswap.UniLpMarket = self.markets[market_key]  # pick our market.
        self.new_position, amount0_used, amount1_used, liquidity = lp_market.add_liquidity(
            self.lp_range[0], self.lp_range[1]
        )  # add liquidity
        self.comment_last_action("Add liquidity because ...")  # add comment to last transaction


    def finalize(self):
        # save result and etc.
        files = self.actuator.save_result(path="./result", file_name=f"strategy-{self.lp_range}")
        pass


"""
Now, let's take a look at the true power of BacktestManager. 
Here, we will backtest two strategies, which differ only in their parameters (although they could also be two completely different strategies). 
They will be executed in parallel.

"""
from datetime import date, datetime
from typing import Tuple

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
    Actuator,
)

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class DemoStrategy(Strategy):
    """
    this demo shows how to handle backtest results.
    """

    def __init__(self, lp_range: Tuple[float, float]):
        super().__init__()
        self.some_record = []
        self.lp_range = lp_range

    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 12, 0, 0), do=self.add)
        self.triggers.append(new_trigger)

    def on_bar(self, snapshot: Snapshot):
        self.some_record.append({"custom1": snapshot.market_status[market_key]["openTick"]})

    def add(self, snapshot: Snapshot):
        lp_market: uniswap.UniLpMarket = self.markets[market_key]  # pick our market.
        self.new_position, amount0_used, amount1_used, liquidity = lp_market.add_liquidity(
            self.lp_range[0], self.lp_range[1]
        )  # add liquidity
        self.comment_last_action("Add liquidity because ...")  # add comment to last transaction


def after_backtest(actuator: Actuator):
    # save result and etc.
    files = actuator.save_result(path="./result", file_name=f"strategy-{actuator.strategy.lp_range}")
    pass


"""
Now, let's take a look at the true power of BacktestManager. 
Here, we will backtest two strategies, which differ only in their parameters (although they could also be two completely different strategies). 
They will be executed in parallel.

"""

if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)
    eth = TokenInfo(name="eth", decimal=18)
    pool = uniswap.UniV3Pool(usdc, eth, 0.05, usdc)

    market_key = MarketInfo("market1")  # market1
    market = uniswap.UniLpMarket(market_key, pool)

    strategy_config = StrategyConfig(
        assets={usdc: 10000, eth: 10},
        markets=[market],
    )
    data_df = uniswap.load_uni_v3_data(
        pool,
        ChainType.polygon.name,
        "0x45dda9cb7c25131df268515131f647d726f50608",
        date(2023, 8, 15),
        date(2023, 8, 16),
        "../data",
    )
    price_data = uniswap.get_price_from_data(data_df, pool)

    backtest = BacktestManager(
        config=strategy_config,
        data=BacktestData({market_key: data_df}, price_data),
        strategies=[DemoStrategy((1000, 3000)), DemoStrategy((1500, 2500))], # two strategies
        backtest_config=BacktestConfig(callback=after_backtest),
        threads=2, # concurrent number
    )
    backtest.run()

```

> Note: If there is only one strategy or the number of concurrent processes is set to 1, the backtest will be executed in the main process.