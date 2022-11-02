from datetime import date, datetime
from typing import Union
import demeter.indicator
from demeter import TokenInfo, PoolBaseInfo, Actuator, Strategy, Asset, AccountStatus, BuyAction, SellAction, RowData, \
    ChainType
import pandas as pd
from strategy_ploter import plotter, plot_position_return_decomposition


class AddLpByMa(Strategy):
    price_width = None

    def __init__(self, price_width=100):
        super().__init__()
        self.price_width = price_width

    def initialize(self):
        prices = self.data.closeTick.map(lambda x: self.broker.tick_to_price(x))
        self._add_column("ma5", demeter.indicator.simple_moving_average(prices, 5))

    def rebalance(self, price):
        status: AccountStatus = self.broker.get_account_status(price)
        base_amount = status.net_value / 2
        quote_amount_diff = base_amount / price - status.quote_balance
        if quote_amount_diff > 0:
            self.buy(quote_amount_diff)
        elif quote_amount_diff < 0:
            self.sell(0 - quote_amount_diff)

    def next(self, row_data: Union[RowData, pd.Series]):
        if row_data.timestamp.minute != 0:
            return
        if len(self.broker.positions) > 0:
            keys = list(self.broker.positions.keys())
            for k in keys:
                self.remove_liquidity(k)
            self.rebalance(row_data.price)
        ma_price = row_data.ma5 if row_data.ma5 > 0 else row_data.price
        self.add_liquidity(ma_price - self.price_width,
                           ma_price + self.price_width)

    def notify_buy(self, action: BuyAction):
        print(action.get_output_str(), action.base_balance_after / action.quote_balance_after)

    def notify_sell(self, action: SellAction):
        print(action.get_output_str(), action.base_balance_after / action.quote_balance_after)


if __name__ == "__main__":
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = PoolBaseInfo(usdc, eth, 0.05, usdc)

    actuator_instance = Actuator(pool)
    actuator_instance.strategy = AddLpByMa(200)
    actuator_instance.set_assets([Asset(usdc, 2000)])
    actuator_instance.data_path = "../data"
    actuator_instance.load_data(ChainType.Polygon.name,
                              "0x45dda9cb7c25131df268515131f647d726f50608",
                                date(2022, 8, 5),
                                date(2022, 8, 20))
    actuator_instance.run(enable_notify=False)
    print(actuator_instance.final_status.net_value)

    actuator_instance.broker.get_account_status(actuator_instance.final_status.price)

    plot_position_return_decomposition(actuator_instance.account_status_list)
