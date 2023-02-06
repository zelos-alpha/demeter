from decimal import Decimal
from typing import Union

import pandas as pd

from .trigger import Trigger
from .._typing import PositionInfo, BaseAction, AddLiquidityAction, SellAction, BuyAction, CollectFeeAction, \
    RemoveLiquidityAction, RowData
from ..broker import UniLpMarket
from ..data_line import Lines, Line


class Strategy(object):
    """
    strategy parent class, all user strategy should inherit this class
    """

    def __init__(self):
        self.broker: UniLpMarket = None
        self.data: Lines = None
        self.number_format = ".8g"
        self.triggers: [Trigger] = []

    def initialize(self):
        """
        initialize your strategy, this will be called before self.on_bar()

        """
        pass

    def before_bar(self, row_data: Union[RowData, pd.Series]):
        """
        called before triggers on each row, at this time, fees are not updated yet. you can add some indicator or add some actions

        :param row_data: row data, include columns load from data, converted data( price, volumn, and timestamp, index), indicators(such as ma)
        :type row_data: Union[RowData, pd.Series]
        """
        pass

    def on_bar(self, row_data: Union[RowData, pd.Series]):
        """
        called after triggers on each row, at this time, fees and account status are not updated yet. you can add some actions here

        :param row_data: row data, include columns load from data, converted data( price, volumn, and timestamp, index), indicators(such as ma)
        :type row_data: Union[RowData, pd.Series]
        """
        pass

    def after_bar(self, row_data: Union[RowData, pd.Series]):
        """
        called after fees and account status are updated on each row. you can add some statistic logic here

        :param row_data: row data, include columns load from data, converted data( price, volumn, and timestamp, index), indicators(such as ma)
        :type row_data: Union[RowData, pd.Series]
        """
        pass

    def finalize(self):
        """
        this will run after all the data processed.

        """
        pass

    def notify(self, action: BaseAction):
        """
        notify if non-basic action happens

        :param action:  action
        :type action: BaseAction
        """
        print(action.get_output_str())

    def notify_add_liquidity(self, action: AddLiquidityAction):
        """
        notify if add liquidity action happens

        :param action:  action
        :type action: AddLiquidityAction
        """
        print(action.get_output_str())

    def notify_remove_liquidity(self, action: RemoveLiquidityAction):
        """
        notify if remove liquidity action happens

        :param action:  action
        :type action: RemoveLiquidityAction
        """
        print(action.get_output_str())

    def notify_collect_fee(self, action: CollectFeeAction):
        """
        notify if collect fee action happens

        :param action:  action
        :type action: CollectFeeAction
        """
        print(action.get_output_str())

    def notify_buy(self, action: BuyAction):
        """
        notify if buy action happens

        :param action:  action
        :type action: BuyAction
        """
        print(action.get_output_str())

    def notify_sell(self, action: SellAction):
        """
        notify if sell action happens

        :param action:  action
        :type action: SellAction
        """
        print(action.get_output_str())

    def _add_column(self, name: str, line: Line):
        """
        add a column to data

        :param name: column name
        :type name: str
        :param line: data
        :type line: Line
        """
        self.data[name] = line

    def add_liquidity(self,
                      lower_quote_price: Decimal | float,
                      upper_quote_price: Decimal | float,
                      base_max_amount: Decimal | float = None,
                      quote_max_amount: Decimal | float = None,
                      ) -> (PositionInfo, Decimal, Decimal):
        """

        add liquidity, then get a new position

        :param lower_quote_price: lower price base on quote token.
        :type lower_quote_price: Decimal | float
        :param upper_quote_price: upper price base on quote token.
        :type upper_quote_price: Decimal | float
        :param base_max_amount:  inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type base_max_amount: Decimal | float
        :param quote_max_amount: inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type quote_max_amount: Decimal | float
        :return: added position, base token used, quote token used
        :rtype: (PositionInfo, Decimal, Decimal)
        """

        return self.broker.add_liquidity(lower_quote_price, upper_quote_price, base_max_amount, quote_max_amount)

    def add_liquidity_by_tick(self,
                              lower_tick: int,
                              upper_tick: int,
                              base_max_amount: Decimal | float = None,
                              quote_max_amount: Decimal | float = None,
                              sqrt_price_x96: int = -1,
                              tick: int = -1):
        """

        add liquidity, you need to set tick instead of price.

        :param lower_tick: lower tick
        :type lower_tick: int
        :param upper_tick: upper tick
        :type upper_tick: int
        :param base_max_amount:  inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type base_max_amount: Decimal | float
        :param quote_max_amount: inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type quote_max_amount: Decimal | float
        :param tick: tick price.  if set to none, it will be calculated from current price.
        :type tick: int
        :param sqrt_price_x96: precise price.  if set to none, it will be calculated from current price. this param will override tick
        :type sqrt_price_x96: int
        :return: added position, base token used, quote token used
        :rtype: (PositionInfo, Decimal, Decimal)
        """
        return self.broker.add_liquidity_by_tick(lower_tick,
                                                 upper_tick,
                                                 base_max_amount,
                                                 quote_max_amount,
                                                 sqrt_price_x96,
                                                 tick)

    def remove_liquidity(self, positions: PositionInfo | list, remove_dry_pool: bool = True) -> {
        PositionInfo: (Decimal, Decimal)}:
        """
        remove liquidity from pool, position will be deleted

        :param positions: position info, as an object or an array
        :type positions: [PositionInfo]
        :return: a dict, key is position info, value is (base_got,quote_get), base_got is base token amount collected from position
        :rtype: {PositionInfo: (Decimal,Decimal)}
        """
        return self.broker.remove_liquidity(positions, remove_dry_pool)

    def collect_fee(self, positions: [PositionInfo]) -> {PositionInfo: tuple}:
        """
        collect fee from positions

        :param positions: position info, as an object or an array
        :type positions: [PositionInfo]
        :return: a dict, key is position info, value is (base_got,quote_get), base_got is base token fee collected from position
        :rtype: {Position: tuple(base_got,quote_get)}
        """
        return self.broker.collect_fee(positions)

    def buy(self, amount: Decimal | float, price: Decimal | float = None) -> (Decimal, Decimal, Decimal):
        """
        buy token, swap from base token to quote token.

        :param amount: amount to buy(in quote token)
        :type amount:  Decimal | float
        :param price: price
        :type price: Decimal | float
        :return: fee, base token amount spend, quote token amount got
        :rtype: (Decimal, Decimal, Decimal)
        """
        return self.broker.buy(amount, price)

    def sell(self, amount: Decimal | float, price: Decimal | float = None) -> (Decimal, Decimal, Decimal):
        """
        sell token, swap from quote token to base token.

        :param amount: amount to sell(in quote token)
        :type amount:  Decimal | float
        :param price: price
        :type price: Decimal | float
        :return: fee, base token amount got, quote token amount spend
        :rtype: (Decimal, Decimal, Decimal)
        """
        return self.broker.sell(amount, price)
