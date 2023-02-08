import logging
import time
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import List

import pandas as pd
from tqdm import tqdm  # process bar

from .evaluating_indicator import Evaluator
from .. import PoolStatus, Broker, RowData
from .._typing import BarStatusNames, Asset, DemeterError, \
    EvaluatorEnum, UnitDecimal
from ..broker import UniLpMarket, PoolInfo, BaseAction, AccountStatus
from ..broker._typing import MarketInfo
from ..data_line import Lines
from ..strategy import Strategy


class Actuator(object):
    """
    Core component of a back test. Manage the resources in a test, including broker/strategy/data/indicator,

    :param pool_info: pool information
    :type pool_info: PoolInfo

    """

    def __init__(self, allow_negative_balance=False):
        # all the actions during the test(buy/sell/add liquidity)
        self._action_list: [BaseAction] = []
        # broker status in every bar, use array for performance
        self._account_status_list: [AccountStatus] = []
        # broker
        self._broker: Broker = Broker(allow_negative_balance, lambda action: self._action_list.append(action))
        # strategy
        self._strategy: Strategy = Strategy()

        # path of source data, which is saved by downloader
        # evaluating indicator calculator
        self._evaluator: Evaluator = None
        self._enabled_evaluator: [] = []
        # logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # internal var
        self.__backtest_finished = False

    # region property
    @property
    def account_status(self) -> pd.DataFrame:
        index = self.data.index[0:len(self._account_status_list)]
        return pd.DataFrame(columns=BarStatusNames,
                            index=index,
                            data=map(lambda d: d.to_array(), self._account_status_list))

    @property
    def final_status(self) -> AccountStatus:
        """
        Get status after back test finish.

        If test has not run, an error will be raised.

        :return: Final state of broker
        :rtype: AccountStatus
        """
        if self.__backtest_finished:
            return self._account_status_list[len(self._account_status_list) - 1]
        else:
            raise DemeterError("please run strategy first")

    def reset(self):  # TODO Finish this
        """

        reset all the status variables

        """
        self._action_list = []
        self._evaluator = None
        self._account_status_list = []
        self.__backtest_finished = False
        self.data.reset_cursor()

    @property
    def actions(self) -> [BaseAction]:
        """
        all the actions during the test(buy/sell/add liquidity)

        :return: action list
        :rtype: [BaseAction]
        """
        return self._action_list

    @property
    def evaluating_indicator(self) -> dict[EvaluatorEnum:UnitDecimal]:
        """
        evaluating indicator result

        :return:  evaluating indicator
        :rtype: EvaluatingIndicator
        """
        return self._evaluator.result if self._evaluator is not None else None

    @property
    def broker(self) -> Broker:
        """
        Broker manage assets in back testing. Including asset, positions. it also provides operations for positions,

        :return: Broker
        :rtype: UniLpMarket
        """
        return self._broker

    @property
    def strategy(self) -> Strategy:
        """
        strategy,

        :return: strategy
        :rtype: Strategy
        """
        return self._strategy

    @strategy.setter
    def strategy(self, value):
        """
        set strategy
        :param value: strategy
        :type value: Strategy
        """
        if isinstance(value, Strategy):
            self._strategy = value
        else:
            raise ValueError()

    @property
    def number_format(self) -> str:
        """
        number format for console output, eg: ".8g", ".5f"

        :return: number format
        :rtype: str
        """
        return self._number_format

    @number_format.setter
    def number_format(self, value: str):
        """
        number format for console output, eg: ".8g", ".5f",
        follow the document here: https://python-reference.readthedocs.io/en/latest/docs/functions/format.html

        :param value: number format,
        :type value:str
        """
        self._number_format = value

    # endregion

    def set_assets(self, assets=[Asset]):
        """
        set initial balance for token

        :param assets: assets to set.
        :type assets: [Asset]
        """
        for asset in assets:
            self._broker.set_asset(asset.token, asset.amount)

    def notify(self, strategy: Strategy, actions: [BaseAction]):
        """

        notify user when new action happens.

        :param strategy: Strategy
        :type strategy: Strategy
        :param actions:  action list
        :type actions: [BaseAction]
        """
        # if len(actions) < 1:
        #     return
        # last_time = datetime(1970, 1, 1)
        # for action in actions:
        #     if last_time != action.timestamp:
        #         print(f"\033[7;34m{action.timestamp} \033[0m")
        #         last_time = action.timestamp
        #     match action.action_type:
        #         case ActionTypeEnum.add_liquidity:
        #             strategy.notify_add_liquidity(action)
        #         case ActionTypeEnum.remove_liquidity:
        #             strategy.notify_remove_liquidity(action)
        #         case ActionTypeEnum.collect_fee:
        #             strategy.notify_collect_fee(action)
        #         case ActionTypeEnum.buy:
        #             strategy.notify_buy(action)
        #         case ActionTypeEnum.sell:
        #             strategy.notify_sell(action)
        #         case _:
        #             strategy.notify(action)
        pass

    def _check_backtest(self):

        if len(self._broker.markets) < 1:
            raise DemeterError("No market assigned")
        data_length = []
        # ensure data length same
        for marketInfo, market in self._broker.markets:
            if not isinstance(market.data, Lines):
                raise DemeterError(f"data in {marketInfo.name} must be type of Lines")
            data_length.append(len(market.data.index))
            market.check_asset()  # check each market, including assets

        if List.count(data_length[0]) != len(data_length):
            raise DemeterError("data length among markets are not same")
        length = data_length[0]
        # ensure data interval same
        data_interval = []
        if length > 1:
            for marketInfo, market in self._broker.markets:
                data_interval.append(market.data.iloc[1] - market.data.iloc[0])
            if List.count(data_interval[0]) != len(data_interval):
                raise DemeterError("data interval among markets are not same")

    def __get_market_row_dict(self, index, row_id)->{MarketInfo:RowData}:
        markets_row = {}
        for market_key, market in self._broker.markets.items():
            market_row = RowData(index.to_pydatetime(), row_id)
            df_row = market.data.loc[index]
            for column_name in df_row.index:
                setattr(market_row, column_name, df_row[column_name])
            markets_row[market_key] = market_row
        return markets_row

    def __set_row_to_markets(self, market_row_dict: dict):
        for market_key, market_row_data in market_row_dict.items():
            self._broker.markets[market_key].set_market_status(market_row_data)

    def run(self,
            enable_notify=True,
            evaluator=[EvaluatorEnum.ALL],
            print_final_status=False):
        """
        start back test, the whole process including:

        * reset actuator
        * initialize strategy (set object to strategy, then run strategy.initialize())
        * process each bar in data
            * prepare data in each row
            * run strategy.on_bar()
            * calculate fee earned
            * get latest account status
            * notify actions
        * run evaluator indicator
        * run strategy.finalize()

        :param enable_notify: notify when new action happens
        :type enable_notify: bool
        :param enable_evaluating: enable evaluating indicator. if not enabled, no evaluating will be calculated
        :type enable_evaluating: bool
        :param print_final_status: enable output.
        :type print_final_status: bool
        """
        run_begin_time = time.time()
        self._enabled_evaluator = evaluator
        self.reset()
        self._check_backtest()
        index_array: pd.DatetimeIndex = list(self._broker.markets.keys())[0].data.index
        self.logger.info("init strategy...")

        # set initial status for strategy, so user can run some calculation in initial function.
        first_data = self.__get_market_row_dict(index_array.iloc[0], 0)
        self.__set_row_to_markets(first_data)

        self.init_strategy()
        row_id = 0
        data_length = len(index_array)
        first = True
        self.logger.info("start main loop...")
        with tqdm(total=data_length, ncols=150) as pbar:
            for timestamp_index in index_array:
                # prepare data of a row
                market_row_dict = self.__get_market_row_dict(timestamp_index, row_id)
                row_id += 1
                self.__set_row_to_markets(market_row_dict)
                # execute strategy, and some calculate

                self._strategy.before_bar(market_row_dict)

                if self._strategy.triggers:
                    for trigger in self._strategy.triggers:
                        if trigger.when(market_row_dict):
                            trigger.do(market_row_dict)
                self._strategy.on_bar(market_row_dict)

                # update broker status, eg: re-calculate fee
                # and read the latest status from broker
                for market in self._broker.markets.values():
                    market.update()

                self._strategy.after_bar(market_row_dict)

                if first:
                    first = False
                self._account_status_list.append(self._broker.get_account_status(timestamp_index))

                # process on_bar
                [market.data.move_cursor_to_next() for market in self._broker.markets]
                pbar.update()
        # notify
        # if enable_notify and len(self._action_list) > 0:
        #     self.logger.info("start notify all the actions")
        #     self.notify(self.strategy, self._action_list)
        self.logger.info("main loop finished, start calculate evaluating indicator...")
        # bar_status_df = pd.DataFrame(columns=BarStatusNames,
        #                              index=self.data.index,
        #                              data=map(lambda d: d.to_array(), self._account_status_list))
        # self.logger.info("run evaluating indicator")
        # if len(self._enabled_evaluator) > 0:
        #     self._evaluator = Evaluator(
        #         self._broker.get_init_account_status(init_price, self.data.index[0].to_pydatetime()),
        #         bar_status_df)
        #     self._evaluator.run(self._enabled_evaluator)
        # self._strategy.finalize()
        # self.__backtest_finished = True
        # if print_final_status:
        #     self.output()
        self.logger.info(f"back testing finish, execute time {time.time() - run_begin_time}s")

    def output(self):
        """
        output back test result to console
        """
        if self.__backtest_finished:
            print("Final status")
            print(self.broker.get_account_status(self.data.tail(1).price[0]).get_output_str())
            if len(self._enabled_evaluator) > 0:
                print("Evaluating indicator")
                print(self._evaluator.result)
        else:
            raise DemeterError("please run strategy first")

    def init_strategy(self):
        """
        initialize strategy, set property to strategy. and run strategy.initialize()
        """
        if not isinstance(self._strategy, Strategy):
            raise DemeterError("strategy must be inherit from Strategy")
        self._strategy.broker = self._broker
        self._strategy.data = self._data
        self._strategy.account_status = self.account_status
        self._strategy.initialize()

    def __str__(self):
        return f"Demeter(broker:{self._broker})\n" \
               f"data(data length: {0 if self._data is None else len(self._data)})"
