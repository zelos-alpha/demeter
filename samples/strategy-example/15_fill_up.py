from datetime import date, timedelta

import pandas as pd

from demeter import TokenInfo, Actuator, ChainType, MarketInfo, Strategy, PeriodTrigger, MarketDict, RowData
from demeter.uniswap import UniLpMarket, UniV3Pool
from strategy_ploter import plot_position_return_decomposition

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class FillUp(Strategy):
    def __init__(self, a=10):
        super().__init__()
        self.a = a

    def initialize(self):
        lp_market: UniLpMarket = self.broker.markets[market_key]
        init_price = lp_market.market_status.data.price

        lp_market.even_rebalance(init_price)  # rebalance all reserve token#
        lp_market.add_liquidity(init_price - self.a, init_price + self.a)
        if self.broker.assets[market.base_token].balance > 0:
            lp_market.add_liquidity(init_price - self.a, init_price)
        else:
            lp_market.add_liquidity(init_price, init_price + self.a)
        self.triggers.append(PeriodTrigger(time_delta=timedelta(days=1), do=self.work))

    def work(self, row_data: RowData):
        lp_market: UniLpMarket = self.broker.markets[market_key]
        if len(lp_market.positions) > 0:
            lp_market.remove_all_liquidity()
            lp_market.even_rebalance(row_data.prices[eth.name])
        lp_market.add_liquidity(row_data.prices[eth.name] - self.a, row_data.prices[eth.name] + self.a)
        if self.broker.assets[market.base_token].balance > 0:
            lp_market.add_liquidity(row_data.prices[eth.name] - self.a, row_data.prices[eth.name])
        else:
            lp_market.add_liquidity(row_data.prices[eth.name], row_data.prices[eth.name] + self.a)


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)  # declare  token0
    eth = TokenInfo(name="eth", decimal=18)  # declare token1
    pool = UniV3Pool(usdc, eth, 0.05, usdc)  # declare pool
    market_key = MarketInfo("lp")

    actuator = Actuator()  # declare actuator
    broker = actuator.broker
    market = UniLpMarket(market_key, pool)

    broker.add_market(market)
    broker.set_balance(usdc, 2000)
    broker.set_balance(eth, 0)

    actuator.strategy = FillUp(200)

    market.data_path = "../data"
    market.load_data(ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", date(2023, 8, 13), date(2023, 8, 17))
    actuator.set_price(market.get_price_from_data())
    actuator.run()  # run test
    plot_position_return_decomposition(actuator.get_account_status_dataframe(), actuator.token_prices[eth.name], market_key)
