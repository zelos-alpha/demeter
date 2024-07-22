from datetime import date, datetime, timedelta
from typing import List

import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, RowData, ChainType, MarketInfo, MarketDict, AtTimeTrigger, simple_moving_average, AccountStatus
from demeter.uniswap import UniLPData, UniV3Pool, UniLpMarket

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class DemoStrategy(Strategy):
    """
    this demo shows how to access markets and assets
    """

    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 12, 0, 0), do=self.work)
        self.triggers.append(new_trigger)  # add new trigger at 2023-8-15 12:00:00
        # add an indicator column, this column will be appended to corresponding market data
        self.add_column(market=market_key, name="sma", column_data=simple_moving_average(self.data[market_key].price))  # name,

    def work(self, row_data: RowData):
        # price set to actuator
        eth_price_external = row_data.prices["ETH"]
        eth_price_external = row_data.prices[eth.name]

        # current data row,
        eth_price_in_uniswap = row_data.market_status[market_key].price
        row: pd.Series | UniLPData = row_data.market_status[market_key]
        eth_price_in_uniswap = row.price
        eth_price_in_uniswap = row_data.market_status.market1.price
        eth_price_in_uniswap = row_data.market_status.default.price
        # access extra column by its name
        ma_value = row_data.market_status[market_key].sma

        # access data, every market has its own data, so data is also kept in MarketDict.
        data: pd.DataFrame = self.broker.markets[market_key].data
        data: pd.DataFrame = self.data[market_key]
        data: pd.DataFrame = self.data.default
        data: pd.DataFrame = self.data.market1
        # access current row
        assert data.loc[row_data.timestamp].netAmount0 == data.iloc[row_data.row_id].netAmount0
        # access one minute before
        assert data.loc[row_data.timestamp - timedelta(minutes=1)].price == data.iloc[row_data.row_id - 1].price
        # access extra column by its name
        ma = self.data[market_key].sma

        # account_status, it's very important as it contains net_value.
        # it is kept in a list. if you need a dataframe. you can call account_status_df
        # do not call account_status_df in on_bar because it will slow the backtesting.
        account_status: List[AccountStatus] = self.account_status
        account_status_df: pd.DataFrame = self.account_status_df


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)
    eth = TokenInfo(name="eth", decimal=18)
    pool = UniV3Pool(usdc, eth, 0.05, usdc)

    market_key = MarketInfo("market1")
    market = UniLpMarket(market_key, pool)
    market.data_path = "../data"
    market.load_data(ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", date(2023, 8, 15), date(2023, 8, 15))

    actuator = Actuator()
    actuator.broker.add_market(market)
    actuator.broker.set_balance(usdc, 10000)
    actuator.broker.set_balance(eth, 10)
    actuator.strategy = DemoStrategy()
    actuator.set_price(market.get_price_from_data())

    actuator.run()
