from datetime import date, datetime
from typing import Union
from demeter import TokenInfo, PoolBaseInfo, Runner, Strategy, Asset, AccountStatus, BuyAction, SellAction, RowData, \
    ChainType
import pandas as pd


class TestStrategy(Strategy):

    def initialize(self):
        pass

    def rebalance(self, price):
        status: AccountStatus = self.broker.get_account_status(price)
        base_amount = status.net_value / 2
        quote_amount_diff = base_amount / price - status.quote_balance
        if quote_amount_diff > 0:
            self.buy(quote_amount_diff)
        elif quote_amount_diff < 0:
            self.sell(0 - quote_amount_diff)

    def next(self, row_data: Union[RowData, pd.Series]):
        if row_data.timestamp.minute != 0:
            return
        if len(self.broker.positions) > 0:
            keys = list(self.broker.positions.keys())
            for k in keys:
                self.remove_liquidity(k)
            self.rebalance(row_data.price)
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
