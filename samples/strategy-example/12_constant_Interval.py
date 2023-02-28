from datetime import date

import pandas as pd

from demeter import UniV3Pool, Actuator, MarketInfo, UniLpMarket, TokenInfo, Strategy
from demeter.download import ChainType
from strategy_ploter import plot_position_return_decomposition

pd.options.display.max_columns = None
pd.set_option('display.width', 5000)


class ConstantInterval(Strategy):
    def __init__(self, a=100):
        super().__init__()
        self.a = a

    def initialize(self):
        market: UniLpMarket = self.markets[market_key]
        init_price = market.market_status.price
        market.even_rebalance(init_price)  # rebalance all reserve token#
        # new_position(self, baseToken, quoteToken, usd_price_a, usd_price_b):
        # what is  base/quote "https://corporatefinanceinstitute.com/resources/knowledge/economics/currency-pair/"
        market.add_liquidity(init_price - self.a, init_price + self.a)
        super().__init__()


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)  # declare  token0
    eth = TokenInfo(name="eth", decimal=18)  # declare token1
    pool = UniV3Pool(usdc, eth, 0.05, usdc)  # declare pool
    market_key = MarketInfo("uni_market")

    actuator = Actuator()  # declare actuator
    broker = actuator.broker
    market = UniLpMarket(market_key, pool)

    broker.add_market(market)
    broker.set_balance(usdc, 2000)
    broker.set_balance(eth, 0)

    actuator.strategy = ConstantInterval(200)

    market.data_path = "../data"
    market.load_data(ChainType.Polygon.name,
                     "0x45dda9cb7c25131df268515131f647d726f50608",
                     date(2022, 8, 5),
                     date(2022, 8, 15))
    actuator.set_price(market.get_price_from_data())
    actuator.run()  # run test

    plot_position_return_decomposition(actuator.get_account_status_dataframe(),
                                       actuator.token_prices[eth.name],
                                       market_key)
