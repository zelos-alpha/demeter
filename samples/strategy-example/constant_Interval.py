import demeter as dt
from demeter._typing import TokenInfo, BrokerStatus, Asset
from datetime import timedelta
# from demeter.line import periodize
from download import ChainType

ETH = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)

class ConstantInterval(dt.Strategy):
    def __init__(self,a=10):
        token0,token1 = self.broker.getTokens()
        self.rebalance(token0,token1,mod="default")#rebalance all reserve token#
        P0 = self.data._price[0]
        # new_position(self, baseToken, quoteToken, usd_price_a, usd_price_b):
        #what is  base/quote "https://corporatefinanceinstitute.com/resources/knowledge/economics/currency-pair/"
        self.add_liquidity(P0-a,P0+a)#


    def next(self):
        pass

    def rebalance(self, price):
        status: BrokerStatus = self.broker.get_status(price)
        base_amount = status.capital.number / 2
        quote_amount_diff = base_amount / price - status.quote_balance.number
        if quote_amount_diff > 0:
            self.buy(quote_amount_diff)
        elif quote_amount_diff < 0:
            self.sell(0 - quote_amount_diff)


pool = dt.PoolBaseInfo(token0=usdc, token1 = ETH,fee=.05,base_token=usdc)
runner = dt.Runner(pool)
runner.strategy = ConstantInterval()
runner.set_assets([Asset(usdc, 1000)  , Asset(ETH,1)])
runner.data_path = "../../data"
runner.load_data(ChainType.Polygon.name,
                          "0x45dda9cb7c25131df268515131f647d726f50608",
                          date(2022, 8, 19),
                          date(2022, 8, 20))
#or init_asset = [Asset(usdc, 2000)  , Asset(ETH,0)]

detemer.setAsset(init_asset)

myStrategy = ConstantInterval(a=100)
detemer.addStrategy(myStrategy)
detemer.run()