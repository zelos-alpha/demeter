from datetime import date, timedelta

import pandas as pd

import demeter.indicator
from demeter import TokenInfo, Actuator, Strategy, ChainType, PeriodTrigger, MarketInfo, Snapshot
from demeter.uniswap import UniLpMarket, UniV3Pool
from strategy_ploter import plot_position_return_decomposition

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class AddLiquidityByMA(Strategy):
    """
    We will provide liquidity according simple moving average,
    The liquidity get_position will be [pa − price_width, pa + price_width].

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
        self.add_column(lp_market, "ma5", demeter.indicator.simple_moving_average(self.data.default.price, timedelta(hours=5)))
        self.triggers.append(PeriodTrigger(time_delta=timedelta(hours=1), trigger_immediately=True, do=self.work))

    def work(self, row_data: Snapshot):
        lp_market: UniLpMarket = self.broker.markets[market_key]
        if len(lp_market.positions) > 0:
            lp_market.remove_all_liquidity()
            lp_market.even_rebalance(row_data.prices[eth.name])
        ma_price = row_data.market_status.default.ma5 if row_data.market_status.default.ma5 > 0 else row_data.prices[eth.name]
        lp_market.add_liquidity(ma_price - self.price_width, ma_price + self.price_width)


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)  # TokenInfo(name='usdc', decimal=6)
    eth = TokenInfo(name="eth", decimal=18)  # TokenInfo(name='eth', decimal=18)
    pool = UniV3Pool(
        usdc, eth, 0.05, usdc
    )  # PoolBaseInfo(Token0: TokenInfo(name='usdc', decimal=6),Token1: TokenInfo(name='eth', decimal=18),fee: 0.0500,base token: usdc)
    market_key = MarketInfo("lp")  # uni_market

    actuator = (
        Actuator()
    )  # Demeter Actuator (broker:assets: (usdc: 0),(eth: 0.0649656829313074758270199536); markets: (uni_market:UniLpMarket, positions: 1, total liquidity: 376273903830523))
    broker = (
        actuator.broker
    )  # assets: (usdc: 0),(eth: 0.0649656829313074758270199536); markets: (uni_market:UniLpMarket, positions: 1, total liquidity: 376273903830523)
    market = UniLpMarket(market_key, pool)  # uni_market:UniLpMarket, positions: 1, total liquidity: 376273903830523

    broker.add_market(market)  # add market
    broker.set_balance(usdc, 2000)  # set balance
    broker.set_balance(eth, 0)  # set balance

    actuator.strategy = AddLiquidityByMA(200)  # set strategy

    market.data_path = "../data"  # set data_path
    market.load_data(ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", date(2023, 8, 13), date(2023, 8, 17))
    actuator.set_price(market.get_price_from_data())  # set price

    actuator.run()  # run test

    plot_position_return_decomposition(actuator.account_status_df, actuator.token_prices[eth.name], market_key)
