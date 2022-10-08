import demeter as zs
from demeter.utils.types import Token,Asset,PoolInfo
from demeter.utils.constant import MAX_TICK,MIN_TICK


class UniswapV2(zs.Strategy):
    def __init__(self):
        token0,token1 = self.broker.getTokens()
        self.rebalance(token0,token1,mod="default")#rebalance all reserve token
        # 直接使用tick，所以需要直接调用最底层封装。
        #(self,token0_amount:float,token1_amount:float,lower_tick,upper_tick,current_tick=None)
        self.broker.__add_liquidity(lower_tick = MIN_TICK,upper_tick = MAX_TICK)#默认try max

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

myStrategy = UniswapV2()
detemer.addStrategy(myStrategy)
detemer.run()