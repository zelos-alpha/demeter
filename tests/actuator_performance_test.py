from datetime import datetime, date
from decimal import Decimal

from demeter import TokenInfo, UniV3Pool, Actuator, Strategy, Asset, ChainType, UniLpMarket, MarketInfo
from demeter.broker.uni_lp_liquitidy_math import get_sqrt_ratio_at_tick
import time

test_market = MarketInfo("uni_market")


# https://polygonscan.com/tx/0x288f2e2d123ffa2b041cce53962c064c134a14bb2be1793b2e5b0c518f4eb00f
class ActualStrategy(Strategy):
    def on_bar(self, row_data):
        if row_data[test_market].timestamp == datetime(2022, 6, 6, 11, 5):
            p, lower, upper, l = self.uni_market.add_liquidity_by_tick(200670,
                                                                   200930,
                                                                   Decimal("315.218605"),
                                                                   Decimal("0.135641006407938685"),
                                                                   get_sqrt_ratio_at_tick(200786))


if __name__ == "__main__":
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = UniV3Pool(usdc, eth, 0.05, usdc)
    market = UniLpMarket(test_market, pool)
    actuator: Actuator = Actuator()  # declare actuator
    actuator.strategy = ActualStrategy()

    broker = actuator.broker
    broker.add_market(market)
    broker.set_balance(usdc, Decimal("315.218605"))
    broker.set_balance(eth, Decimal("0.135641006407938685"))
    market.data_path = "../data"
    t1 = time.time()
    market.load_data(ChainType.Polygon.name,
                     "0x45dda9cb7c25131df268515131f647d726f50608",
                     date(2022, 6, 6),
                     date(2022, 10, 11))

    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = UniV3Pool(usdc, eth, 0.05, usdc)
    actuator.run()
    t2 = time.time()
    print(f"process time {t2 - t1}s")
    actuator.output()
    # for status: AccountStatus in actuator.account_status_list:
    #     print(status)
