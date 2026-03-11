# Quickstart

## Preparation


1. Install demeter will pip or clone the repo.
2. Download data in a certain date range.

## Simple example

Here is a simple example of backtesting on uniswap.

```python
from datetime import date
from demeter import TokenInfo, Actuator, Strategy, Snapshot, ChainType, MarketInfo
from demeter.uniswap import UniV3Pool, UniLpMarket


class MyFirstStrategy(Strategy):

    def on_bar(self, row_data: Snapshot):
        if row_data.prices[eth] > 1500:
            market.add_liquidity(1000, 4000)


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)
    eth = TokenInfo(name="eth", decimal=18)

    pool = UniV3Pool(token0=usdc, token1=eth, fee=0.05, quote_token=usdc)

    market_key = MarketInfo("U2EthPool")
    market = UniLpMarket(market_key, pool)

    market.data_path = "../data"
    market.load_data(
        chain=ChainType.polygon.name,
        contract_addr="0x45dda9cb7c25131df268515131f647d726f50608",
        start_date=date(2023, 8, 15),
        end_date=date(2023, 8, 15),
    )

    actuator = Actuator()
    broker = actuator.broker
    broker.set_balance(usdc, 10000)
    broker.set_balance(eth, 10)

    broker.add_market(market)

    actuator.strategy = MyFirstStrategy()
    actuator.set_price(market.get_price_from_data())

    actuator.run()

```

1. In import section, you need to import classes from demeter. As we will test a strategy on uniswap, we also need to
   import some class from demeter.uniswap.
1. This script will run from ```if __name__ == "__main__":```
1. Suppose we will backtest on usdc/eth(fee=0.05%) pool. First, we define two tokens. eth and usdc. Then the pool
1. ```market_key = MarketInfo("U2EthPool")``` Declare a market key, which will be used to find the corresponding market
   in broker
1. ```market = UniLpMarket(market_key, pool)``` Declare the market, it's the place to invest positions.
1. ```market.data_path = "../data"``` Set data folder for uniswap markets. data_path is the target folder path for
   demeter-fetch.
1. Call market.load_data. The most important parameter is start_date and end_date. It decides the time range of
   backtesting. Since time range in this example is one day(1440 minutes), actuator will iterate 1440 times in
   backtesting.
1. ```actuator = Actuator()``` Define actuator which controls the whole test process, and keeps backtest result.
1. ```broker = actuator.broker```. Actuator instance has a preset broker. Now you can set initial token balance to broker. These assets are the principal of
   your investment.
1. ```broker.add_market(market)```, now broker will have a market to invest.
1. ```actuator.strategy = MyFirstStrategy()```, set strategy for actuator.
1. ```actuator.set_price(market.get_price_from_data())```. Set price. Those prices will be used in all markets. Usually,
   you will have to find the price list from an outer source. Luckily, Swap event log of uniswap contains price
   information. So UniLpMarket provides a function to retrieve a price list.
1. ```actuator.run()```. now start backtesting.

Now let's look into the strategy

1. ```class MyFirstStrategy(Strategy):```. A strategy is a python class, and must inherit from demeter.Strategy.
2. ```def on_bar(self, row_data: RowData)```. Override the on_bar function. This function will be called on every
   iteration. Because the interval of market data is minute, one iteration means one minute.
3. Parameter row_data contains timestamp, price and market status at this minute.
4. We make a simple strategy, if the price of eth is above 1500, then provide liquidity with all assets.

After back test, demeter will print a result in console. Those results include:

* Final account status: Account status at the end moment of backtesting. include token balance in broker, and position
  value in all markets.
* Account balance history: list the change of net value, cash, position values during backtesting. Note: the column name
  of market positions is combined by "market name" + "attribute name"

## Start with `BacktestManager`

```python
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
    # 3. backtest config
    bk_config = BacktestConfig()
    # 3. Create a BacktestManager instance, set your strategy, configs and data.
    backtest = BacktestManager(
        config=strategy_config,
        data=BacktestData({market_key: data_df}, price_df),
        strategies=[DemoStrategy()],
        backtest_config=bk_config,
    )
    # As we have only on strategy, backtest will run in main process.
    backtest.run()
    pass

```

For more samples, [check here](https://github.com/zelos-alpha/demeter/tree/master/samples)