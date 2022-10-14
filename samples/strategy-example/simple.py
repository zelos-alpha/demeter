import unittest
from typing import Union
from datetime import timedelta, date

from demeter import TokenInfo, PoolBaseInfo, Runner, Strategy, Asset, RowData, simple_moving_average, ChainType, \
    TimeUnitEnum
import pandas as pd

pd.options.display.max_columns = None
pd.options.display.max_rows = None
pd.set_option('display.width', 5000)


class MyFirstStrategy(Strategy):
    def next(self, row_data: Union[RowData, pd.Series]):
        # show how to access data
        if row_data.row_id == 1000:
            # access current row
            print(row_data.closeTick)
            print(self.data.get_by_cursor(0).closeTick)
            print(self.data.loc[row_data.timestamp].closeTick)

            # access the row by data index
            print(self.data.closeTick[0])  # first row
            print(self.data["closeTick"].iloc[0])  # first row
            print(self.data.closeTick[row_data.row_id])  # current row

            # access previous or after row
            print(self.data.get_by_cursor(-2).closeTick)  # previous 2 rows
            print(self.data.get_by_cursor(2).closeTick)  # after 2 rows
            print(self.data.loc[row_data.timestamp - timedelta(hours=1)].closeTick)  # data of an hour ago
            print(self.data.loc[row_data.timestamp + timedelta(hours=1)].closeTick)  # data of an hour later

            print(self.broker.asset0.balance, self.broker.asset1.balance)  # show balance in asset 0,1
            print(self.broker.base_asset.balance, self.broker.quote_asset.balance)  # show balance in base quote
            print(self.broker.get_account_status())  # get current capital status,
            for position_info, position in self.broker.positions.items():
                print(position_info, position)  # show all position


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)  # declare  token0
    eth = TokenInfo(name="eth", decimal=18)  # declare token1

    pool = PoolBaseInfo(usdc, eth, 0.05, usdc)  # declare pool

    runner = Runner(pool)  # declare runner
    runner.strategy = MyFirstStrategy()  # set strategy to runner
    runner.set_assets([Asset(usdc, 10000), Asset(eth, 10)])  # set primary balances

    runner.data_path = "../data"  # set data path
    runner.load_data(ChainType.Polygon.name,  # load data
                     "0x45dda9cb7c25131df268515131f647d726f50608",
                     date(2022, 8, 20),
                     date(2022, 8, 20))
    runner.data["ma5"] = simple_moving_average(runner.data.price, 5, unit=TimeUnitEnum.hour)  # add indicator

    runner.run()  # run test
    runner.output()  # print final status
