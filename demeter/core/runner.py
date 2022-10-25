import logging
from datetime import date, timedelta, datetime
from decimal import Decimal

import pandas as pd
from tqdm import tqdm  # process bar

from .evaluating_indicator import Evaluator
from .. import PoolStatus
from .._typing import AccountStatus, BarStatusNames, BaseAction, Asset, ZelosError, ActionTypeEnum, \
    EvaluatingIndicator, RowData
from ..broker import Broker, PoolBaseInfo
from ..data_line import Lines
from ..strategy import Strategy

DEFAULT_DATA_PATH = "./data"


def decimal_from_value(value):
    return Decimal(value)


class Runner(object):
    """
    Core component of a back test. Manage the resources in a test, including broker/strategy/data/indicator,

    :param pool_info: pool information
    :type pool_info: PoolBaseInfo

    """

    def __init__(self, pool_info: PoolBaseInfo):
        self._broker: Broker = Broker(pool_info)
        # data
        self._data: Lines = None
        # strategy
        self._strategy: Strategy = Strategy()
        # all the actions during the test(buy/sell/add liquidity)
        self._actions: [BaseAction] = []
        # actions in current bar
        self.bar_actions: [BaseAction] = []
        self._broker.action_buffer = self.bar_actions
        # broker status in every bar
        self.account_status_list: [AccountStatus] = []
        # path of source data, which is saved by downloader
        self._data_path: str = DEFAULT_DATA_PATH
        # evaluating indicator calculator
        self._evaluator: Evaluator = None

        # logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # internal var
        self.__backtest_finished = False

    @property
    def final_status(self) -> AccountStatus:
        """
        Get status after back test finish.

        If test has not run, an error will be raised.

        :return: Final state of broker
        :rtype: AccountStatus
        """
        if self.__backtest_finished:
            return self.account_status_list[len(self.account_status_list) - 1]
        else:
            raise ZelosError("please run strategy first")

    def reset(self):
        """

        reset all the status variables

        """
        self._actions = []
        self._evaluator = None
        self.account_status_list = []
        self.__backtest_finished = False
        self.data.reset_cursor()

    @property
    def data_path(self) -> str:
        """
        path of source data, which is saved by downloader
        """
        return self._data_path

    @data_path.setter
    def data_path(self, value: str):
        """
        path of source data, which is saved by downloader

        :param value: path
        :type value: str

        """
        self._data_path = value

    @property
    def actions(self) -> [BaseAction]:
        """
        all the actions during the test(buy/sell/add liquidity)

        :return: action list
        :rtype: [BaseAction]
        """
        return self._actions

    @property
    def evaluating_indicator(self) -> EvaluatingIndicator:
        """
        evaluating indicator result

        :return:  evaluating indicator
        :rtype: EvaluatingIndicator
        """
        return self._evaluator.evaluating_indicator if self._evaluator is not None else None

    @property
    def broker(self) -> Broker:
        """
        Broker manage assets in back testing. Including asset, positions. it also provides operations for positions,

        :return: Broker
        :rtype: Broker
        """
        return self._broker

    @property
    def data(self) -> Lines:
        """
        data

        :return:
        :rtype: Lines
        """
        return self._data

    @data.setter
    def data(self, value: Lines):
        """
        set data which saved by downloader. data source should contain the following column, and indexed with timestamp

        * netAmount0,
        * netAmount1,
        * closeTick,
        * openTick,
        * lowestTick,
        * highestTick,
        * inAmount0,
        * inAmount1,
        * currentLiquidity

        :param value: data
        :type value: Lines
        """
        self._data = value

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
        self._strategy = value

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
        number format for console output, eg: ".8g", ".5f", follow the document here: https://python-reference.readthedocs.io/en/latest/docs/functions/format.html

        :param value: number format,
        :type value:str
        """
        self._number_format = value

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
        if len(actions) < 1:
            return
        last_time = datetime(1970, 1, 1)
        for action in actions:
            if last_time != action.timestamp:
                print(f"\033[7;34m{action.timestamp} \033[0m")
                last_time = action.timestamp
            match action.action_type:
                case ActionTypeEnum.add_liquidity:
                    strategy.notify_add_liquidity(action)
                case ActionTypeEnum.remove_liquidity:
                    strategy.notify_remove_liquidity(action)
                case ActionTypeEnum.collect_fee:
                    strategy.notify_collect_fee(action)
                case ActionTypeEnum.buy:
                    strategy.notify_buy(action)
                case ActionTypeEnum.sell:
                    strategy.notify_sell(action)
                case _:
                    strategy.notify(action)

    def load_data(self, chain: str, contract_addr: str, start_date: date, end_date: date):
        """

        load data, and preprocess. preprocess actions including:

        * fill empty data
        * calculate statistic column
        * set timestamp as index

        :param chain: chain name
        :type chain: str
        :param contract_addr: pool contract address
        :type contract_addr: str
        :param start_date: start test date
        :type start_date: date
        :param end_date: end test date
        :type end_date: date
        """
        self.logger.info(f"start load files from {start_date} to {end_date}...")
        df = pd.DataFrame()
        day = start_date
        while day <= end_date:
            path = f"{self.data_path}/{chain}-{contract_addr}-{day.strftime('%Y-%m-%d')}.csv"
            day_df = pd.read_csv(path, converters={'inAmount0': decimal_from_value,
                                                   'inAmount1': decimal_from_value,
                                                   'netAmount0': decimal_from_value,
                                                   'netAmount1': decimal_from_value,
                                                   "currentLiquidity": decimal_from_value})
            df = pd.concat([df, day_df])
            day = day + timedelta(days=1)
        self.logger.info("load file complete, preparing...")

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)

        # fill empty row (first minutes in a day, might be blank)
        full_indexes = pd.date_range(start=df.index[0], end=df.index[df.index.size - 1], freq="1min")
        df = df.reindex(full_indexes)
        df = Lines.from_dataframe(df)
        df = df.fillna()
        self.add_statistic_column(df)
        self.data = df
        self.logger.info("data has benn prepared")

    def add_statistic_column(self, df: Lines):
        """
        add statistic column to data, new columns including:

        * open: open price
        * price: close price (current price)
        * low: lowest price
        * high: height price
        * volume0: swap volume for token 0
        * volume1: swap volume for token 1

        :param df: original data
        :type df: Lines

        """
        # add statistic column
        df["open"] = df["openTick"].map(lambda x: self.broker.tick_to_price(x))
        df["price"] = df["closeTick"].map(lambda x: self.broker.tick_to_price(x))
        high_name, low_name = ("lowestTick", "highestTick") if self.broker.pool_info.is_token0_base \
            else ("highestTick", "lowestTick")
        df["low"] = df[high_name].map(lambda x: self.broker.tick_to_price(x))
        df["high"] = df[low_name].map(lambda x: self.broker.tick_to_price(x))
        df["volume0"] = df["inAmount0"].map(lambda x: Decimal(x) / 10 ** self.broker.pool_info.token0.decimal)
        df["volume1"] = df["inAmount1"].map(lambda x: Decimal(x) / 10 ** self.broker.pool_info.token1.decimal)

    def run(self, enable_notify=True):
        """
        start back test, the whole process including:

        * reset runner
        * initialize strategy (set object to strategy, then run strategy.initialize())
        * process each bar in data
            * prepare data in each row
            * run strategy.next()
            * calculate fee earned
            * get latest account status
            * notify actions
        * run evaluator indicator
        * run strategy.finalize()

        :param enable_notify: notify when new action happens
        :type enable_notify: bool
        """
        self.reset()
        if self._data is None:
            return
        self.logger.info("init strategy...")
        first_data = self._data.iloc[0]
        self._broker.pool_status = PoolStatus(self._data.index[0].to_pydatetime(),
                                              first_data.closeTick,
                                              first_data.currentLiquidity,
                                              first_data.inAmount0,
                                              first_data.inAmount1,
                                              first_data.price)
        self.init_strategy()
        if not isinstance(self._data, Lines):
            raise ZelosError("Data must be instance of Lines")
        row_id = 0
        first = True
        self.logger.info("start main loop...")
        with tqdm(total=len(self._data.index), ncols=150) as pbar:
            for index, row in self._data.iterrows():
                row_data = RowData()
                setattr(row_data, "timestamp", index.to_pydatetime())
                setattr(row_data, "row_id", row_id)
                row_id += 1
                for column_name in row.index:
                    setattr(row_data, column_name, row[column_name])
                # execute strategy, and some calculate
                # update price tick
                self._broker.pool_status = PoolStatus(index.to_pydatetime(),
                                                      row_data.closeTick,
                                                      row_data.currentLiquidity,
                                                      row_data.inAmount0,
                                                      row_data.inAmount1,
                                                      row_data.price)
                self._strategy.next(row_data)
                if self._strategy.triggers:
                    for trigger in self._strategy.triggers:
                        if trigger.when(row_data):
                            trigger.do(row_data)
                # update broker status, eg: re-calculate fee
                # and read the latest status from broker
                self._broker.update()
                if first:
                    init_price = row_data.price
                    first = False
                self.account_status_list.append(self._broker.get_account_status(row_data.price, index.to_pydatetime()))

                # collect actions in this loop
                current_event_list = self.bar_actions.copy()
                for event in current_event_list:
                    event.timestamp = index
                self.bar_actions.clear()
                if current_event_list and len(current_event_list) > 0:
                    self._actions.extend(current_event_list)

                # process next
                self._data.move_cursor_to_next()
                pbar.update()
        # notify
        if enable_notify and len(self._actions) > 0:
            self.logger.info("start notify all the actions")
            self.notify(self.strategy, self._actions)
        self.logger.info("main loop finished, start calculate evaluating indicator...")
        bar_status_df = pd.DataFrame(columns=BarStatusNames,
                                     index=self.data.index,
                                     data=map(lambda d: d.to_array(), self.account_status_list))
        self.logger.info("run evaluating indicator")
        self._evaluator = Evaluator(
            self._broker.get_init_account_status(init_price, self.data.index[0].to_pydatetime()),
            bar_status_df)
        self._evaluator.run()
        self._strategy.finalize()
        self.logger.info("back testing finish")
        self.__backtest_finished = True

    def output(self):
        """
        output back test result to console
        """
        if self.__backtest_finished:
            print("Final status")
            print(self.broker.get_account_status(self.data.tail(1).price[0]).get_output_str())
            print("Evaluating indicator")
            print(self._evaluator.evaluating_indicator.get_output_str())
        else:
            raise ZelosError("please run strategy first")

    def init_strategy(self):
        """
        initialize strategy, set property to strategy. and run strategy.initialize()
        """
        if not isinstance(self._strategy, Strategy):
            raise ZelosError("strategy must be inherit from Strategy")
        self._strategy.broker = self._broker
        self._strategy.data = self._data

        self._strategy.initialize()

    def __str__(self):
        return f"Demeter(broker:{self._broker})\n" \
               f"data(data length: {0 if self._data is None else len(self._data)})"
