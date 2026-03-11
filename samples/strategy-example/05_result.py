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
    this demo shows how to handle backtest results.
    """

    def __init__(self):
        super().__init__()
        self.some_record = []

    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 12, 0, 0), do=self.work)
        self.triggers.append(new_trigger)
        remove_trigger = AtTimeTrigger(time=datetime(2023, 8, 16, 12, 0, 0), do=self.remove_liquidity)
        self.triggers.append(remove_trigger)

    def on_bar(self, snapshot: Snapshot):
        self.some_record.append({"custom1": snapshot.market_status[market_key]["netAmount1"]})

    def work(self, snapshot: Snapshot):
        lp_market: UniLpMarket = self.markets[market_key]  # pick our market.
        self.new_position, amount0_used, amount1_used, liquidity = lp_market.add_liquidity(1000, 4000)  # add liquidity
        self.comment_last_action("Add liquidity because ...")  # add comment to last transaction

    def remove_liquidity(self, snapshot: Snapshot):
        lp_market: UniLpMarket = self.markets[market_key]
        lp_market.remove_liquidity(self.new_position)

    def notify(self, action: BaseAction):
        """
        When a new action(add/remove liquidity) is executed, you can be notified by this call back.
        """
        print("\n")
        print(action.timestamp, action.action_type.value)
        # add price to actions, so price will be kept in csv file.
        action.price = "{:.3f}".format(actuator.token_prices.loc[action.timestamp][eth.name])
        pass

    def finalize(self):
        """
        account_status, it's very important as it contains net_value.
        It has other values include net value for each market, and balance history of each asset
        For Uniswap market, it has the following values
        * net_value: total net value
        * usdc: token usdc balance
        * eth: token eth balance
        * market1_net_value: net value of market1
        * market1_base_uncollected: uncollected base token amount.
        * market1_quote_uncollected: uncollected quote token amount
        * market1_base_in_position: how many base token was deposited in get_position. it's calculated by liquidity and price
        * market1_quote_in_position: how many quote token was deposited in get_position.
        * market1_position_count: get_position count
        """
        account_status: List[AccountStatus] = self.account_status

        # if you need a dataframe. you can call account_status_df
        # do not call account_status_df in on_bar because it will slow the backtesting.
        account_status_df: pd.DataFrame = self.account_status_df

        # actions, this record all the actions such as add/remove liquidity, buy, sell,
        # As each action has different parameter, its type is List[BaseAction],
        # and it can't be converted into a dataframe.
        actions: List[BaseAction] = self.actions

        # Add custom column to account status dataframe.
        custom_df = pd.DataFrame(index=self.account_status_df.index, data=self.some_record)
        multi_index = pd.MultiIndex.from_tuples([("custom", "custom1")])
        custom_df.columns = multi_index
        actuator.account_status_df = pd.concat([actuator.account_status_df, custom_df], axis=1)

        pass


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

    actuator = Actuator()
    actuator.broker.add_market(market)  # add market
    actuator.broker.set_balance(usdc, 10000)  # set balance
    actuator.broker.set_balance(eth, 10)  # set balance
    actuator.strategy = DemoStrategy()  # add strategy
    actuator.set_price(market.get_price_from_data())  # set price

    actuator.run()

    # get metrics
    metrics = performance_metrics(
        actuator.account_status_df["net_value"], benchmark=actuator.account_status_df["price"]["ETH"]
    )
    metrics_df = pd.DataFrame(data=metrics.items(), columns=["item", "value"])
    print(metrics_df)
    # save backtest result(include backtest information(.pkl) and account status(.csv) to this folder)
    # default file name has timestamp. If you want a custom file name, you can set file_name
    # if you want to add some custom parameter to pkl file, you can use dict, such as custom_param in this example.
    files = actuator.save_result(path="./result", file_name="custom-file-name", custom_param="custom_value", decimals=3)

    # load equity list
    account_df_loaded = load_account_status(files[1])
    pass
