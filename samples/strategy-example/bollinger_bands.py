import math
from datetime import date, timedelta

from demeter import TokenInfo, PoolBaseInfo, Actuator, Strategy, Asset, ChainType, PeriodTrigger, actual_volatility, \
    simple_moving_average

c = 2


class AddByVolatility(Strategy):
    """
    We will provide liquidity inside the Bollinger Bands.
    These bands are made up of a lower band BOLL = pa − c · v
    and an upper band BOLU = pa + c · v.
    The liquidity position will be [pa − v · c, pa + v · c].

    * pa is simple moving average
    * c is a constant value, =2
    * v is volatility

    we will adjust liquidity every 4 hours, by remove all the liquidity, then even split all the capital into two assets,
    and provide liquidity by the rules above.

    """
    def initialize(self):
        self._add_column("sma_1_day", simple_moving_average(self.data.price, timedelta(days=1)))
        self._add_column("volatility", actual_volatility(self.data.price, timedelta(days=1), timedelta(days=1)))
        self.triggers.append(PeriodTrigger(time_delta=timedelta(hours=4),
                                           trigger_immediately=True,
                                           do=self.work))
        self.broker.even_rebalance(self.data.price[0])

    def work(self, row_data):
        if len(self.broker.positions) > 0:
            self.broker.remove_all_liquidity()
            self.broker.even_rebalance(row_data.price)
        if math.isnan(row_data.volatility):
            return
        limit = c * float(row_data.price) * row_data.volatility
        self.add_liquidity(row_data.sma_1_day - limit,
                           row_data.sma_1_day + limit)


if __name__ == "__main__":
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = PoolBaseInfo(usdc, eth, 0.05, usdc)

    actuator = Actuator(pool)
    actuator.strategy = AddByVolatility()
    actuator.set_assets([Asset(usdc, 5000)])
    actuator.data_path = "../data"
    actuator.load_data(ChainType.Polygon.name,
                       "0x45dda9cb7c25131df268515131f647d726f50608",
                       date(2022, 8, 5),
                       date(2022, 8, 10))
    actuator.run()
    actuator.output()
