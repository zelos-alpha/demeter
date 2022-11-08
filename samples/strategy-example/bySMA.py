from datetime import date, timedelta

import demeter.indicator
from demeter import TokenInfo, PoolBaseInfo, Actuator, Strategy, Asset, BuyAction, SellAction, ChainType, PeriodTrigger
from strategy_ploter import plot_position_return_decomposition


class AddLpByMa(Strategy):
    """
    We will provide liquidity according simple moving average,
    The liquidity position will be [pa − price_width, pa + price_width].

    * pa is simple moving average
    * price_width is a constant value, default value is 100

    we will adjust liquidity every hours, by remove all the liquidity, then even split all the capital into two assets,
    and provide liquidity by the rules above.

    """
    price_width = None

    def __init__(self, price_width=100):
        super().__init__()
        self.price_width = price_width

    def initialize(self):
        self._add_column("ma5", demeter.indicator.simple_moving_average(self.data.price, timedelta(hours=5)))
        self.triggers.append(PeriodTrigger(time_delta=timedelta(hours=1),
                                           trigger_immediately=True,
                                           do=self.work))

    def work(self, row_data):
        if len(self.broker.positions) > 0:
            self.broker.remove_all_liquidity()
            self.broker.even_rebalance(row_data.price)
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
