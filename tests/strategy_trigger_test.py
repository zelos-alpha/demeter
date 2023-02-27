from datetime import date, datetime, timedelta
from typing import Union

import pandas as pd

from demeter import TokenInfo, UniV3Pool, Actuator, Strategy, Asset, RowData, ChainType, AtTimeTrigger, PeriodTrigger, \
    UniLpMarket, MarketInfo, MarketDict


class TestStrategy(Strategy):

    def initialize(self):
        self.triggers.append(AtTimeTrigger(datetime(2022, 8, 19, 0, 30),  # trigger time
                                           self.sell_1,  # action
                                           5, 5,  # *arg
                                           amount=0.01  # **kwargs
                                           ))
        self.triggers.append(PeriodTrigger(timedelta(hours=6),
                                           self.adjust_position,
                                           trigger_immediately=True,
                                           price_range=100))

    def on_bar(self, row_data: MarketDict[RowData | pd.Series]):
        pass

    def sell_1(self, row_data, *args, **kwargs):
        assert args[0] == args[1]
        self.broker.markets[test_market].sell(kwargs["amount"])

    def adjust_position(self, row_data: MarketDict[RowData | pd.Series], *args, **kwargs):
        market: UniLpMarket = self.broker.markets.uni_market
        market.remove_all_liquidity()
        market.even_rebalance(row_data.uni_market.price)
        market.add_liquidity(market.market_status.price - kwargs["price_range"],
                             market.market_status.price + kwargs["price_range"])


if __name__ == "__main__":
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = UniV3Pool(usdc, eth, 0.05, usdc)

    actuator_instance = Actuator()
    broker = actuator_instance.broker
    test_market = MarketInfo("uni_market")

    market = UniLpMarket(test_market, pool)
    broker.add_market(market)
    actuator_instance.strategy = TestStrategy()
    broker.set_balance(usdc, 5000)
    broker.set_balance(eth, 3)
    market.data_path = "../data"
    market.load_data(ChainType.Polygon.name,
                     "0x45dda9cb7c25131df268515131f647d726f50608",
                     date(2022, 8, 19),
                     date(2022, 8, 19))
    actuator_instance.set_price(market.get_price_from_data())
    actuator_instance.run()
