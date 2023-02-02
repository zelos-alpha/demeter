from datetime import date, datetime, timedelta
from typing import Union

import pandas as pd

from demeter import TokenInfo, PoolInfo, Actuator, Strategy, Asset, RowData, \
    ChainType, AtTimeTrigger, PeriodTrigger


class TestStrategy(Strategy):

    def initialize(self):
        self.triggers.append(AtTimeTrigger(
            datetime(2022, 8, 19, 0, 30),  # trigger time
            self.sell_1,  # action
            5, 5,  # *arg
            amount=0.01  # **kwargs
        ))
        self.triggers.append(
            PeriodTrigger(timedelta(hours=6), self.adjust_position, trigger_immediately=True, price_range=100))

    def on_bar(self, row_data: Union[RowData, pd.Series]):
        pass

    def sell_1(self, row_data: RowData, *args, **kwargs):
        assert args[0] == args[1]
        self.sell(kwargs["amount"])

    def adjust_position(self, row_data: Union[RowData, pd.Series], *args, **kwargs):
        self.broker.remove_all_liquidity()
        self.broker.even_rebalance(row_data.price)
        self.add_liquidity(self.broker.pool_status.price - kwargs["price_range"],
                           self.broker.pool_status.price + kwargs["price_range"])


if __name__ == "__main__":
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = PoolInfo(usdc, eth, 0.05, usdc)

    actuator_instance = Actuator(pool)
    actuator_instance.strategy = TestStrategy()
    actuator_instance.set_assets([Asset(usdc, 5000), Asset(eth, 3)])
    actuator_instance.data_path = "../data"
    actuator_instance.load_data(ChainType.Polygon.name,
                              "0x45dda9cb7c25131df268515131f647d726f50608",
                                date(2022, 8, 19),
                                date(2022, 8, 19))
    actuator_instance.run()
    actuator_instance.output()
