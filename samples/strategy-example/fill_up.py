import demeter as dt
from datetime import timedelta, date

from demeter import TokenInfo, PoolBaseInfo, Runner, Asset, AccountStatus

from demeter.download import ChainType


class FillUp(dt.Strategy):

    def __init__(self, a=10, b=1, update_interval=timedelta(days=1)):
        super().__init__()
        self.a = a
        # self.lines.update_timestamps = periodize(update_interval)#生成line 对象 ture/false#TODO

    def initialize(self):
        a = self.a
        P0 = self.broker.pool_status.price
        self.rebalance(P0)#rebalance all reserve token#

        self.my_a_position =  self.add_liquidity(P0-self.a,P0+self.a)
        if self.broker.base_asset.balance>0:
            self.my_b_position = self.add_liquidity(P0-a,P0)
        else:
            self.my_b_position = self.add_liquidity(P0,P0+a)

    def next(self,row_data):
        a = self.a
        if row_data.timestamp.hour != 0 or row_data.timestamp.minute != 0: #every day. need a tool function to set in the future.
            return
        if len(self.broker.positions) > 0:
            keys = list(self.broker.positions.keys())
            for k in keys:
                self.remove_liquidity(k)
            self.rebalance(row_data.price)
        current_price = self.broker.pool_status.price
        self.my_a_position =  self.add_liquidity(current_price-self.a,current_price+self.a)
        if self.broker.base_asset.balance>0:
            self.my_b_position = self.add_liquidity(current_price-a,current_price)
        else:
            self.my_b_position = self.add_liquidity(current_price,current_price+a)

    def rebalance(self, price):
        status: AccountStatus = self.broker.get_account_status(price)
        base_amount = status.net_value / 2
        quote_amount_diff = base_amount / price - status.quote_balance
        if quote_amount_diff > 0:
            self.buy(quote_amount_diff)
        elif quote_amount_diff < 0:
            self.sell(0 - quote_amount_diff)

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)
pool = PoolBaseInfo(usdc, eth, 0.05, usdc)

runner_instance = Runner(pool)
runner_instance.enable_notify = False
runner_instance.strategy = FillUp(200)
runner_instance.set_assets([Asset(usdc, 2000)])

runner_instance.data_path = "../data"
runner_instance.load_data(ChainType.Polygon.name,
                          "0x45dda9cb7c25131df268515131f647d726f50608",
                          date(2022, 8, 5),
                          date(2022, 8, 20))
runner_instance.run(enable_notify=False)
print(runner_instance.final_status.net_value)


