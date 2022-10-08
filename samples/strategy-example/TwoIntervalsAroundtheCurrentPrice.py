import demeter as zs
from demeter.utils.types import Token,Asset,PoolInfo
from demeter.utils.constant import MAX_TICK,MIN_TICK
from datetime import timedelta
# from demeter.line import periodize

ETH = Token(name="eth", decimal=18)
usdc = Token(name="usdc", decimal=6)
from datetime import timedelta
from demeter.line import periodize


class TwoIntervalsAroundtheCurrentPrice(zs.Strategy):
    def __init__(self,a=10,b=1,update_interval=timedelta(days=1)):
        self.a = a
        self.b = b
        token0,token1 = self.broker.getTokens()
        self.rebalance(token0,token1,mod="default")#rebalance all reserve token#
        P0 = self.data._price[0]
        self.lines.update_timestamps = periodize(update_interval)#生成line 对象 ture/false#TODO

        self.my_a_position =  self.add_liquidity(P0-a,P0+a)#尽可能。所以可以不用其他参数
        if self.broker.getAsset().base_token_amt>0:# 还剩更多的u
            self.my_b_position = self.add_liquidity(P0-b,P0)
        else:
            self.my_b_position = self.add_liquidity(P0,P0+b)

    def next(self):
        if self.lines.update_timestamps[0]:
            self.broker.withdraw_liquidity([self.my_b_position,self.my_a_position])
            current_price  = self.data._price[0]
            self.my_position = self.add_liquidity(current_price-self.a,current_price+self.a)

            if self.broker.getAsset().base_token_amt > 0:  # 还剩更多的u
                self.my_b_position = self.add_liquidity(current_price - self.b, current_price)
            else:
                self.my_b_position = self.add_liquidity(current_price, current_price + self.current_priceb)


detemer = zs.Detemer()
pool = PoolInfo(token0=usdc,token1 = ETH,isTokenBase = True)
data = zs.feeds.v3datafeed(pool,from_datetime="2022-05-18",to_datetime="2022-06-18")

init_asset = [Asset(usdc, 1000)  , Asset(ETH,1)]
#or init_asset = [Asset(usdc, 2000)  , Asset(ETH,0)]

detemer.setAsset(init_asset)

myStrategy = TwoIntervalsAroundtheCurrentPrice(a=100,b=10)
detemer.addStrategy(myStrategy)
detemer.run()