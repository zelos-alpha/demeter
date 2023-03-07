from datetime import date, timedelta

import pandas as pd

import demeter.indicator
from demeter import TokenInfo, UniV3Pool, Actuator, Strategy, ChainType, PeriodTrigger, \
    MarketInfo, UniLpMarket, MarketDict, RowData
from strategy_ploter import plot_position_return_decomposition

pd.options.display.max_columns = None
pd.set_option('display.width', 5000)


class AddLiquidityByMA(Strategy):
    """
    We will provide liquidity according simple moving average,
    The liquidity position will be [pa − price_width, pa + price_width].

    * pa is simple moving average
    * price_width is a constant value, default value is 100

    we will adjust liquidity every hours, by remove all the liquidity, then even split all the capital into two assets,
    and provide liquidity by the rules above.

    """

    def __init__(self, price_width=100):
        super().__init__()
        self.price_width = price_width

    def initialize(self):
        lp_market: UniLpMarket = self.broker.markets[market_key]
        self._add_column(lp_market, "ma5",
                         demeter.indicator.simple_moving_average(self.data.default.price, timedelta(hours=5)))
        self.triggers.append(PeriodTrigger(time_delta=timedelta(hours=1),
                                           trigger_immediately=True,
                                           do=self.work))

    def work(self, row_data: MarketDict[RowData]):
        lp_market: UniLpMarket = self.broker.markets[market_key]
        if len(lp_market.positions) > 0:
            lp_market.remove_all_liquidity()
            lp_market.even_rebalance(row_data.default.price)
        ma_price = row_data.default.ma5 if row_data.default.ma5 > 0 else row_data.default.price
        lp_market.add_liquidity(ma_price - self.price_width,
                                ma_price + self.price_width)


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

    actuator.strategy = AddLiquidityByMA(200)

    market.data_path = "../data"
    market.load_data(ChainType.Polygon.name,
                     "0x45dda9cb7c25131df268515131f647d726f50608",
                     date(2022, 8, 5),
                     date(2022, 8, 20))
    actuator.set_price(market.get_price_from_data())
    actuator.run()  # run test

    plot_position_return_decomposition(actuator.get_account_status_dataframe(),
                                       actuator.token_prices[eth.name],
                                       market_key)
