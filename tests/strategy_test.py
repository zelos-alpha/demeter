from datetime import date, datetime, timedelta
from typing import Union
from demeter import TokenInfo, PoolBaseInfo, Runner, Strategy, Asset, AccountStatus, BuyAction, SellAction, RowData, \
    ChainType, Trigger, AtTimesTrigger, AtTimeTrigger, PeriodTrigger
import pandas as pd


class TestStrategy(Strategy):

    def initialize(self):
        self.triggers.append(AtTimeTrigger(datetime(2022, 8, 19, 0, 30), self.sell_1))
        self.triggers.append(PeriodTrigger(timedelta(hours=1), self.adjust_position, trigger_immediately=True))

    def sell_1(self, row_data: RowData):
        self.sell(0.01)

    def adjust_position(self, row_data: Union[RowData, pd.Series]):
        self.broker.remove_all_liquidity()
        self.broker.divide_balance_equally(row_data.price)
        self.add_liquidity(self.broker.pool_status.price - 100,
                           self.broker.pool_status.price + 100)


if __name__ == "__main__":
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = PoolBaseInfo(usdc, eth, 0.05, usdc)

    runner_instance = Runner(pool)
    runner_instance.strategy = TestStrategy()
    runner_instance.set_assets([Asset(usdc, 5000), Asset(eth, 3)])
    runner_instance.data_path = "../data"
    runner_instance.load_data(ChainType.Polygon.name,
                              "0x45dda9cb7c25131df268515131f647d726f50608",
                              date(2022, 8, 19),
                              date(2022, 8, 20))
    runner_instance.run()
    runner_instance.output()
