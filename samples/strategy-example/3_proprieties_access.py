from datetime import date, datetime
from typing import List

import pandas as pd

from demeter import TokenInfo, UniV3Pool, Actuator, Strategy, RowData, ChainType, \
    MarketInfo, UniLpMarket, MarketDict, AtTimeTrigger, simple_moving_average, AccountStatus
from demeter.uniswap import UniLPData

pd.options.display.max_columns = None
pd.set_option('display.width', 5000)


class DemoStrategy(Strategy):
    """
    this demo shows how to access markets and assets
    """

    def initialize(self):
        new_trigger = AtTimeTrigger(
            time=datetime(2022, 8, 20, 12, 0, 0),
            do=self.work)
        self.triggers.append(new_trigger)
        # add a indicator column, this column will be appended to corresponding market data
        self._add_column(market=market_key,
                         name="sma",  # name,
                         line=simple_moving_average(self.data[market_key].price))

    def work(self, row_data: MarketDict[RowData]):
        # access market, all market are stored in a property, whose type is MarketDict.
        # you can access elements of MarketDict by
        # 1. market key as index
        # 2. market name as property
        market: UniLpMarket = self.broker.markets[market_key]
        market: UniLpMarket = self.broker.markets.market1
        # Default market is the first market added, If there is only one market, it's useful simplify the code.
        # default market can be changed.
        market: UniLpMarket = self.broker.markets.default
        # to simplify the code, we provide a shortcut of broker.markets in strategy
        market: UniLpMarket = self.markets[market_key]
        market: UniLpMarket = self.markets.market1
        market: UniLpMarket = self.markets.default

        # assets
        # You can access asset by token key,
        asset_usdc = self.broker.assets[usdc]
        # UniLpMarket keeps token key as token0 or base token. It can be used to access asset, too
        asset_usdc = self.broker.assets[market.base_token]
        asset_usdc = self.broker.assets[market.token0]
        # shortcut for broker.assets
        asset_usdc = self.assets[usdc]

        # current row of data,
        price = row_data[market_key].price
        row: UniLPData = row_data[market_key]
        price = row.price
        price = row_data.market1.price
        price = row_data.default.price
        # access extra column by its name
        ma_value = row_data[market_key].sma

        # access data, data is also kept in MarketDict. and it's type is Dataframe
        data: pd.DataFrame = self.broker.markets[market_key].data
        data: pd.DataFrame = self.data[market_key]
        data: pd.DataFrame = self.data.default
        data: pd.DataFrame = self.data.market1
        ma = self.data[market_key].sma

        # account_status, it's very important as it contains net_value.
        # it is kept in a list. if you need a dataframe. you can call get_account_status_dataframe()
        # do not call get_account_status_dataframe in on_bar because it will slow the backtesting.
        account_status: List[AccountStatus] = self.account_status
        account_status_df: pd.DataFrame = self.get_account_status_dataframe()


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)
    eth = TokenInfo(name="eth", decimal=18)
    pool = UniV3Pool(usdc, eth, 0.05, usdc)

    market_key = MarketInfo("market1")
    market = UniLpMarket(market_key, pool)
    market.data_path = "../data"
    market.load_data(ChainType.Polygon.name,
                     "0x45dda9cb7c25131df268515131f647d726f50608",
                     date(2022, 8, 20),
                     date(2022, 8, 20))

    actuator = Actuator()
    actuator.broker.add_market(market)
    actuator.broker.set_balance(usdc, 10000)
    actuator.broker.set_balance(eth, 10)
    actuator.strategy = DemoStrategy()
    actuator.set_price(market.get_price_from_data())

    actuator.run()
