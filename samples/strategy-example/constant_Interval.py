import demeter as dt
from demeter import PoolInfo, Actuator
from demeter._typing import TokenInfo, AccountStatus, Asset
from datetime import date
from demeter.download import ChainType

from strategy_ploter import  plot_position_return_decomposition
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
        self.add_liquidity(P0 - self.a,
                           P0 + self.a)
        print("eth_value",self.broker.quote_asset.balance)
        super().__init__()


    def rebalance(self, price):
        status: AccountStatus = self.broker.get_account_status(price)
        base_amount = status.net_value / 2
        quote_amount_diff = base_amount / price - status.quote_balance
        if quote_amount_diff > 0:
            self.buy(quote_amount_diff)
        elif quote_amount_diff < 0:
            self.sell(0 - quote_amount_diff)


if __name__ == "__main__":
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = PoolInfo(usdc, eth, 0.05, usdc)

    actuator_instance = Actuator(pool)
    actuator_instance.enable_notify = False
    actuator_instance.strategy = ConstantInterval(200)
    actuator_instance.set_assets([Asset(usdc, 2000)])
    actuator_instance.data_path = "../data"
    actuator_instance.load_data(ChainType.Polygon.name,
                              "0x45dda9cb7c25131df268515131f647d726f50608",
                                date(2022, 8, 5),
                                date(2022, 8, 15))
    actuator_instance.run(enable_notify=False)
    print(actuator_instance.final_status.net_value)

    plot_position_return_decomposition(actuator_instance.account_status_list)

