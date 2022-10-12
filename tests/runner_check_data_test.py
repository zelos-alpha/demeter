from decimal import Decimal

from demeter import TokenInfo, PoolBaseInfo, Runner, Strategy, Asset, Lines, ChainType
from datetime import datetime, date


# https://polygonscan.com/tx/0x288f2e2d123ffa2b041cce53962c064c134a14bb2be1793b2e5b0c518f4eb00f
class ActualStrategy(Strategy):
    def next(self, row_data):
        if row_data.timestamp == datetime(2022, 6, 6, 11, 5):
            p, lower, upper = self.broker._add_liquidity_by_tick(Decimal("315.218605"),
                                                                 Decimal("0.135641006407938685"),
                                                                 200670,
                                                                 200930,
                                                                 200786)
            print(p)


if __name__ == "__main__":
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = PoolBaseInfo(usdc, eth, 0.05, usdc)

    runner = Runner(pool)
    runner.strategy = ActualStrategy()
    runner.set_assets([Asset(usdc, Decimal("315.218605")), Asset(eth, Decimal("0.135641006407938685"))])
    runner.data_path = "../data"
    runner.load_data(ChainType.Polygon.name,
                     "0x45dda9cb7c25131df268515131f647d726f50608",
                     date(2022, 6, 6),
                     date(2022, 10, 11))
    runner.run()
    runner.output()
    # for status: AccountStatus in runner.account_status_list:
    #     print(status)
