import demeter as dt
from demeter import PoolBaseInfo, Runner
from demeter._typing import TokenInfo, BrokerStatus, Asset
from datetime import date, datetime
from download import ChainType

ETH = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)
import  matplotlib.pylab as plt

class ConstantInterval(dt.Strategy):
    def __init__(self, a=100):
        super().__init__()
        self.a = a

    def initialize(self):
        P0 = self.broker.pool_status.price
        self.rebalance(P0)#rebalance all reserve token#
        # new_position(self, baseToken, quoteToken, usd_price_a, usd_price_b):
        #what is  base/quote "https://corporatefinanceinstitute.com/resources/knowledge/economics/currency-pair/"
        self.add_liquidity(self.broker.base_asset.balance,
                           self.broker.quote_asset.balance,
                           P0 - self.a,
                           P0 + self.a)
        super().__init__()


    def rebalance(self, price):
        status: BrokerStatus = self.broker.get_broker_status(price)
        base_amount = status.capital.number / 2
        quote_amount_diff = base_amount / price - status.quote_balance.number
        if quote_amount_diff > 0:
            self.buy(quote_amount_diff)
        elif quote_amount_diff < 0:
            self.sell(0 - quote_amount_diff)


if __name__ == "__main__":
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = PoolBaseInfo(usdc, eth, 0.05, usdc)

    runner_instance = Runner(pool)
    runner_instance.enable_notify = False
    runner_instance.strategy = ConstantInterval(200)
    runner_instance.set_assets([Asset(usdc, 2000)])
    runner_instance.data_path = "../data"
    runner_instance.load_data(ChainType.Polygon.name,
                              "0x45dda9cb7c25131df268515131f647d726f50608",
                              date(2022, 8, 5),
                              date(2022, 8, 15))
    runner_instance.run(enable_notify=False)

    print(runner_instance.final_status.net_value)

    runner_instance.broker.get_broker_status(runner_instance.final_status.price.number)
    net_value_ts = [status.net_value.number for status in runner_instance.bar_status]
    time_ts =  [status.timestamp for status in runner_instance.bar_status]
    plt.plot(time_ts,net_value_ts)

    plt.show()
    print(runner_instance.actions)