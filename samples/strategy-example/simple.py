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
        if row_data.price > 1500:
            self.buy(100, row_data.price)
        if row_data.row_id == 2:
            # access current row, method is provided by demeter
            row_data.closeTick == 2
            self.data.get_by_cursor(0).closeTick == 2

            # access current row, method is provided by pandas
            self.data.closeTick[0] == 0
            self.data.loc[row_data.timestamp].closeTick == 2
            self.data["closeTick"].iloc[0] == 0

            # access previous or after row
            self.data.get_by_cursor(-2).closeTick == 0
            self.data.get_by_cursor(2).closeTick == 4
            self.data.loc[row_data.timestamp - timedelta(minutes=2)].closeTick == 0
            self.data.loc[row_data.timestamp + timedelta(minutes=2)].closeTick == 4


if __name__ == "__main__":
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = PoolBaseInfo(usdc, eth, 0.05, usdc)

    runner = Runner(pool)
    runner.strategy = MyFirstStrategy()
    runner.set_assets([Asset(usdc, 1000), Asset(eth, 1)])

    runner.data_path = "../data"
    runner.load_data(ChainType.Polygon.name,
                     "0x45dda9cb7c25131df268515131f647d726f50608",
                     date(2022, 8, 20),
                     date(2022, 8, 20))
    runner.data["ma5"] = simple_moving_average(runner.data.price, 5, unit=TimeUnitEnum.hour)

    runner.run()
    runner.output()
