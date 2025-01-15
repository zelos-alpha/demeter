from datetime import date, datetime

import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, Snapshot, ChainType, MarketInfo, AtTimeTrigger
from demeter.uniswap import UniV3Pool, UniLpMarket, load_uni_v3_data, get_price_from_data

# To print all the columns of dataframe, we should set up display option.
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


"""
This is a simple demo for strategy. In this strategy, We will provide liquidity at specific time.
"""


class MyFirstStrategy(Strategy):
    def initialize(self):
        """
        Initialize function will be called right before a backtest start.
        You can do various things here, e.g. register a trigger, or add a simple moving average line.
        """
        new_trigger = AtTimeTrigger(  # define a new trigger
            time=datetime(2022, 8, 20, 12, 0, 0), do=self.work  # we will make the action happen at 12:00 20/8/22
        )  # This is a callback function, defines what to do at this time.
        self.triggers.append(new_trigger)  # Register our trigger

    def work(self, row_data: Snapshot):
        """
        When time is up, work function will be called.
        """
        lp_market: UniLpMarket = self.markets[market_key]  # pick our market.
        new_position, amount0_used, amount1_used, liquidity = lp_market.add_liquidity(1000, 4000)  # add liquidity
        pass


if __name__ == "__main__":
    """
    Here shows how to start a back test. Demeter has 4 components.
    * Actuator: It controls the whole test process, and keeps backtest result.
    * Broker: Broker manage assets(token balance in wallet) and markets(e.g. uniswap or aave). When you declare an actuator, you will have a default broker inside.
    * Market: Market is the place you execute transactions. There are various market type, and we support Uniswap V3 Liquid Provider market and AAVE now.
    * Strategy: It's a class designed for test different market making strategies. Users need to inherit the strategy class and test returns of different strategies through on_bar processing or triggers.
    """

    # Declare a token, and it's name will be used as unit of amounts.
    usdc = TokenInfo(name="usdc", decimal=6)  # declare token usdc
    eth = TokenInfo(name="eth", decimal=18)  # declare token eth
    # Declare an Uniswap V3 pool. We will set the parameters according to the real pool on chain.
    pool = UniV3Pool(token0=usdc, token1=eth, fee=0.05, quote_token=usdc)

    # Declare a market key, which will be used to find the corresponding market in broker
    market_key = MarketInfo("U2EthPool")
    # Declare the market,
    market = UniLpMarket(market_key, pool)  # uni_market:UniLpMarket, positions: 0, total liquidity: 0
    # load data for market. those data is prepared by download tool
    market.data_path = "../data"  # set data path

    data_df = load_uni_v3_data(
        pool,
        ChainType.polygon.name,
        "0x45dda9cb7c25131df268515131f647d726f50608",
        date(2023, 8, 15),
        date(2023, 8, 16),
        "../data",
    )
    price_data = get_price_from_data(data_df, pool)

    market.data = data_df

    # Declare the Actuator, which controls the whole process
    actuator = Actuator()  # declare actuator, Demeter Actuator (broker:assets: ; markets: )
    # add market to broker
    actuator.broker.add_market(market)
    # Initial some fund to broker.
    actuator.broker.set_balance(usdc, 10000)
    actuator.broker.set_balance(eth, 10)
    # Set strategy to actuator
    actuator.strategy = MyFirstStrategy()  # set strategy to actuator
    # Set price. Those price will be used in all markets.
    # Usually, you will have to find the price list from outer source.
    # Luckily, uniswap pool data contains price information. So UniLpMarket provides a function to retrieve price list.
    actuator.set_price(price_data)
    # run test, If you use default parameter, final fund status will be printed in console.
    actuator.run()
