import pandas as pd
from datetime import date, datetime
from typing import List

from demeter import (
    TokenInfo,
    Actuator,
    Strategy,
    Snapshot,
    ChainType,
    MarketInfo,
    AtTimeTrigger,
    AccountStatus,
    BaseAction,
)
from demeter.result import performance_metrics
from demeter.uniswap import UniLpMarket, UniV3Pool
from demeter.utils import load_account_status

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class DemoStrategy(Strategy):
    """
    This demo shows how to estimate gas used. First you need to prepare a gas price list in every minute.
    Then gas for every transaction. As gas used is different between users(someone may add liquidity through router
    contract while others call pool contract directly), you have to set up a dictionary to keep gas used for
    every transaction type yourself.
    """

    def __init__(self):
        super().__init__()
        self.some_record = []

    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 12, 0, 0), do=self.add)
        self.triggers.append(new_trigger)


    def add(self, snapshot: Snapshot):
        market.add_liquidity(1600, 2000)  # add liquidity
        # estimate gas used
        gas_fee = gas_used["add_liquidity"] * gas_price_df.loc[snapshot.timestamp]["gas_price"] / 1e9
        self.comment_last_action(f"gas fee: {gas_fee} OP")



if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)
    eth = TokenInfo(name="eth", decimal=18)
    pool = UniV3Pool(usdc, eth, 0.05, usdc)

    market_key = MarketInfo("market1")  # market1
    market = UniLpMarket(market_key, pool)
    market.data_path = "../data"
    market.load_data(
        ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", date(2023, 8, 15), date(2023, 8, 16)
    )

    gas_used = {
        "add_liquidity": 430000,
        "swap": 440000,
        "remove_liquidity": 290000,
    }
    # Prepare a gas price list in every minute.
    gas_price_df = pd.read_csv("../data/gas_price.csv", parse_dates=["block_timestamp"], index_col=[0])

    actuator = Actuator()
    actuator.broker.add_market(market)  # add market
    actuator.broker.set_balance(usdc, 10000)  # set balance
    actuator.broker.set_balance(eth, 10)  # set balance
    actuator.strategy = DemoStrategy()  # add strategy
    actuator.set_price(market.get_price_from_data())  # set price

    actuator.print_action = True
    actuator.run()
