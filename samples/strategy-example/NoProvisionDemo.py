import demeter as zs
from demeter.utils.types import Token,Asset,PoolInfo


class NoProvision(zs.Strategy):
    def __init__(self):
        token0,token1 = self.broker.getTokens()
        self.rebalance(token0,token1,mod="default")#rebalance all
    def next(self):
        pass


ETH = Token(name="eth", decimal=18)
usdc = Token(name="usdc", decimal=6)


detemer = zs.Detemer()
pool = PoolInfo(token0=usdc,token1 = ETH,isTokenBase = True)
data = zs.feeds.v3datafeed(pool,from_datetime="2022-05-18",to_datetime="2022-06-18")

init_asset = [Asset(usdc, 1000)  , Asset(ETH,1)]
#or init_asset = [Asset(usdc, 2000)  , Asset(ETH,0)]

detemer.setAsset(init_asset)

myStrategy = NoProvision()
detemer.addStrategy(myStrategy)
detemer.run()