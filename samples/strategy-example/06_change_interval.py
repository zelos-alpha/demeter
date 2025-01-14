import math
from datetime import timedelta, date

import pandas as pd

from demeter import (
    TokenInfo,
    Actuator,
    Strategy,
    Snapshot,
    simple_moving_average,
    ChainType,
    MarketInfo,
    PeriodTrigger,
    BaseAction,
)
from demeter.uniswap import UniV3Pool, UniLpMarket

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class DemoStrategy(Strategy):
    pass


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)
    eth = TokenInfo(name="eth", decimal=18)
    pool = UniV3Pool(usdc, eth, 0.05, usdc)

    market_key = MarketInfo("market1")  # market1
    market = UniLpMarket(market_key, pool)
    market.data_path = "../data"
    market.load_data(
        ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", date(2023, 8, 15), date(2023, 8, 15)
    )

    actuator = Actuator()  # init actuator
    actuator.broker.add_market(market)  # add market to actuator
    actuator.broker.set_balance(usdc, 10000)  # set balance
    actuator.broker.set_balance(eth, 10)  # set balance
    actuator.strategy = DemoStrategy()  # set strategy
    actuator.set_price(market.get_price_from_data())  # set actuator price

    # print transactions during backtesting
    actuator.print_action = True
    actuator.interval = "1h"  # change frequency, so backtest will run hourly instead of minutely
    actuator.run()  # run actuator
