from _decimal import Decimal
from datetime import date, datetime
from typing import List, Dict

import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, RowData, ChainType, MarketInfo, MarketDict, AtTimeTrigger, AccountStatus, EvaluatorEnum, BaseAction
from demeter.uniswap import UniLpMarket, UniV3Pool

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class DemoStrategy(Strategy):
    """
    this demo shows how to access markets and assets
    """

    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime(2023, 8, 15, 12, 0, 0), do=self.work)
        self.triggers.append(new_trigger)

    def work(self, row_data: RowData):
        lp_market: UniLpMarket = self.markets[market_key]  # pick our market.
        new_position, amount0_used, amount1_used, liquidity = lp_market.add_liquidity(1000, 4000)  # add liquidity

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
        * market1_base_in_position: how many base token was deposited in position. it's calculated by liquidity and price
        * market1_quote_in_position: how many quote token was deposited in position.
        * market1_position_count: position count
        """
        account_status: List[AccountStatus] = self.account_status

        # if you need a dataframe. you can call get_account_status_dataframe()
        # do not call get_account_status_dataframe in on_bar because it will slow the backtesting.
        account_status_df: pd.DataFrame = self.get_account_status_dataframe()

        # actions, this record all the actions such as add/remove liquidity, buy, sell,
        # As each action has different parameter, its type is List[BaseAction],
        # and it can't be converted into a dataframe.
        actions: List[BaseAction] = self.actions
        pass


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)  # TokenInfo(name='usdc', decimal=6)
    eth = TokenInfo(name="eth", decimal=18)  # TokenInfo(name='eth', decimal=18)
    pool = UniV3Pool(usdc, eth, 0.05, usdc)

    market_key = MarketInfo("market1")  # market1
    market = UniLpMarket(market_key, pool)
    market.data_path = "../data"
    market.load_data(ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", date(2023, 8, 15), date(2023, 8, 15))

    actuator = Actuator()
    actuator.broker.add_market(market)  # add market
    actuator.broker.set_balance(usdc, 10000)  # set balance
    actuator.broker.set_balance(eth, 10)  # set balance
    actuator.strategy = DemoStrategy()  # add strategy
    actuator.set_price(market.get_price_from_data())  # set price

    # if evaluator is set, evaluating indicator will run after backtest.
    # those evaluating indicator will calculate indicator of net value.
    actuator.run(evaluator=[EvaluatorEnum.MAX_DRAW_DOWN, EvaluatorEnum.ANNUALIZED_RETURNS])
    # get result
    evaluating_result: Dict[EvaluatorEnum, Decimal] = actuator.evaluating_indicator

    actuator.save_result(
        path="./result",  # save path
        account=True,  # save account status list as a csv file
        actions=True,  # save actions as a json file and a pickle file
    )
    pass
