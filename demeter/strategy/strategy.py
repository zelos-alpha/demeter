from decimal import Decimal
from datetime import datetime
from typing import Union

from demeter import PositionInfo, BaseAction, AddLiquidityAction, SellAction, BuyAction, CollectFeeAction, \
    RemoveLiquidityAction, RowData
import pandas as pd


class Strategy(object):
    def __init__(self):
        self.broker = None
        self.data = None
        self.number_format = ".8g"

    def initialize(self):
        pass

    def next(self, time: datetime, row_data: Union[RowData, pd.Series]):
        """

        :param time:
        :type time: datetime
        :param row_data:
        :type row_data:
        :return:
        :rtype:
        """
        pass

    def notify_on_next(self, actions: [BaseAction]):
        print(f"\033[7;34m{actions[0].timestamp} \033[0m {len(actions)} actions")

    def notify(self, action: BaseAction):
        print(action.get_output_str())

    def notify_add_liquidity(self, action: AddLiquidityAction):
        print(action.get_output_str())

    def notify_remove_liquidity(self, action: RemoveLiquidityAction):
        print(action.get_output_str())

    def notify_collect_fee(self, action: CollectFeeAction):
        print(action.get_output_str())

    def notify_buy(self, action: BuyAction):
        print(action.get_output_str())

    def notify_sell(self, action: SellAction):
        print(action.get_output_str())

    def _add_column(self, name: str, line):
        self.data[name] = line

    def add_liquidity(self, base_max_amount, quote_max_amount, lower_quote_price, upper_quote_price):
        return self.broker.add_liquidity(base_max_amount, quote_max_amount, lower_quote_price, upper_quote_price)

    def remove_liquidity(self, positions: [PositionInfo]):
        return self.broker.remove_liquidity(positions)

    def collect_fee(self, positions: [PositionInfo]):
        return self.broker.collect_fee(positions)

    def buy(self, amount: Decimal | float, price: Decimal | float = None):
        return self.broker.buy(amount, price)

    def sell(self, amount: Decimal | float, price: Decimal | float = None):
        return self.broker.sell(amount, price)
