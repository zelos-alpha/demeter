import math
from datetime import timedelta, date

import pandas as pd

from demeter import TokenInfo, Actuator, Strategy, RowData, simple_moving_average, ChainType, MarketInfo, PeriodTrigger, BaseAction
from demeter.uniswap import UniV3Pool, UniLpMarket

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)

"""
This demo will show how to work with strategy, including how to trigger actions and get notified.
"""


class DemoStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.net_value_before_bar = 0
        self.net_value_diff_list = []

    """
    Strategy has may functions to override, They provide flexibility for writing strategy.
    During backtest process, those functions will be called in the following sequence:
    
    some_prepare_work()
    strategy.initialize()
    for row in all_data:
        strategy.triggers(row)
        strategy.on_bar(row)
        markets.update()
        strategy.after_bar(row)
    strategy.finalize()
    output_test_result()
    
    
    """

    def initialize(self):
        """
        This function is called before main loop is executed.
        you can prepare data, or register trigger here
        """

        # Add a simple moving average line for backtesting data. In backtesting,
        # we will add/remove liquidity according to this line.
        self._add_column(market_key, "sma", simple_moving_average(self.data[market_key].price, window=timedelta(hours=1)))

        # Register a trigger, every day, we split both assets into two shares of equal value
        self.triggers.append(PeriodTrigger(time_delta=timedelta(days=1), trigger_immediately=True, do=self.rebalance))

    def rebalance(self, row_data: RowData):
        self.markets[market_key].even_rebalance(row_data.market_status[market_key].price)

    """
    After a test is executed, actuator will loop the data, and bar series functions will be called on every time. 
    Here you can set conditions and execute liquidity operations 
    """

    def on_bar(self, row_data: RowData):
        """
        This function is called after trigger, but before market is updated(Fees will be distributed in this step).
        """
        lp_market: UniLpMarket = self.markets[market_key]
        current_price = row_data.market_status[market_key].price
        # get moving average price, if value is nan, fill it with current price
        ma_price = self.data[market_key].loc[row_data.timestamp]["sma"]
        ma_price = row_data.market_status[market_key].price if math.isnan(ma_price) else ma_price

        # this is a nonsense strategy, just to show how to trigger actions
        if row_data.market_status[market_key].price > ma_price + 25 and len(self.markets[market_key].positions) < 1:
            lp_market.remove_all_liquidity()
            lp_market.add_liquidity(current_price, current_price + 100)
        elif row_data.market_status[market_key].price < ma_price - 25 and len(self.markets[market_key].positions) < 1:
            lp_market.remove_all_liquidity()
            lp_market.add_liquidity(current_price - 100, current_price)

    def after_bar(self, row_data: RowData):
        """
        this function is called after market has updated.
        """
        timestamp = row_data.timestamp
        net_value_after_bar = self.broker.get_account_status(self.prices.loc[timestamp]).net_value
        net_value_diff = net_value_after_bar - self.net_value_before_bar
        self.net_value_diff_list.append(net_value_diff)

    def finalize(self):
        """
        Call when main loop finished. some statistic work can be executed here
        """
        self.data[market_key]["diff"] = self.net_value_diff_list
        pass

    def notify(self, action: BaseAction):
        """
        When a new action(add/remove liquidity) is executed, you can be notified by this call back.
        """
        print("\n")
        print(action.timestamp, action.action_type.value)


if __name__ == "__main__":
    usdc = TokenInfo(name="usdc", decimal=6)  # TokenInfo(name='usdc', decimal=6)
    eth = TokenInfo(name="eth", decimal=18)  # TokenInfo(name='eth', decimal=18)
    pool = UniV3Pool(
        usdc, eth, 0.05, usdc
    )  # PoolBaseInfo(Token0: TokenInfo(name='usdc', decimal=6),Token1: TokenInfo(name='eth', decimal=18),fee: 0.0500,base token: usdc)

    market_key = MarketInfo("market1")  # market1
    market = UniLpMarket(market_key, pool)
    market.data_path = "../data"
    market.load_data(ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", date(2023, 8, 15), date(2023, 8, 15))

    actuator = Actuator()  # init actuator
    actuator.broker.add_market(market)  # add market to actuator
    actuator.broker.set_balance(usdc, 10000)  # set balance
    actuator.broker.set_balance(eth, 10)  # set balance
    actuator.strategy = DemoStrategy()  # set strategy
    actuator.set_price(market.get_price_from_data())  # set actuator price

    actuator.run()  # run actuator
