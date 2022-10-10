import logging
from .. import PoolStatus
from ..data_line import Lines
from ..broker import Broker, PoolBaseInfo
from .._typing import BrokerStatus, BarStatusNames, BaseAction, Asset, ZelosError, TokenInfo, ActionTypeEnum, \
    EvaluatingIndicator, RowData
from ..strategy import Strategy
from datetime import date, timedelta
from .evaluating_indicator import Evaluator
import pandas as pd
from decimal import Decimal
"""
11111111111111111111111111111111111111111
"""
DEFAULT_DATA_PATH = "./data"


def decimal_from_value(value):
    return Decimal(value)


class Runner(object):
    """
    Core component of a back test
    """

    def __init__(self, pool_info: PoolBaseInfo):
        """
        Create a new Runner

        :param pool_info: pool information

        :type pool_info: PoolBaseInfo

        """
        self._broker: Broker = Broker(pool_info)
        self._data: Lines = None  # 数据
        self._strategy: Strategy = Strategy()  # 策略
        self._actions: [BaseAction] = []  # 所有操作(买, 卖, 添加流动性等)
        self.bar_actions: [BaseAction] = []  # 当前bar的所有操作
        self._broker.action_buffer: [BaseAction] = self.bar_actions
        self.bar_status: [BrokerStatus] = []  # 迭代的每个bar中, broker的状态(包括余额等)
        self._data_path: str = DEFAULT_DATA_PATH  # 存放数据的路径
        self._evaluator: Evaluator = None  # 评价策略

        # configs
        self._enable_notify: bool = True
        # logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # internal var
        self.__backtest_finished = False

    @property
    def final_status(self) -> BrokerStatus:
        """
        Get status after back test finish.

        If test has not run, an error will be raised.

        :return: Final state of broker

        :rtype: BrokerStatus
        """
        if self.__backtest_finished:
            return self.bar_status[len(self.bar_status) - 1]
        else:
            raise ZelosError("please run strategy first")

    def reset(self):
        self._actions = []
        self._evaluator = None
        self.bar_status = []
        self.__backtest_finished = False
        self.data.reset_cursor()

    @property
    def data_path(self):
        return self._data_path

    @data_path.setter
    def data_path(self, value):
        self._data_path = value

    @property
    def enable_notify(self):
        return self._enable_notify

    @enable_notify.setter
    def enable_notify(self, value):
        self._enable_notify = value

    @property
    def actions(self):
        return self._actions

    @property
    def evaluating_indicator(self) -> EvaluatingIndicator:
        return self._evaluator.evaluating_indicator if self._evaluator is not None else None

    @property
    def broker(self):
        return self._broker

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def strategy(self):
        return self._strategy

    @strategy.setter
    def strategy(self, value):
        self._strategy = value

    @property
    def number_format(self):
        return self._number_format

    @number_format.setter
    def number_format(self, value):
        self._number_format = value

    def set_assets(self, assets=[Asset]):
        for asset in assets:
            self._broker.set_asset(asset.token, asset.amount)

    def process_volumne(self, amount0, asset: TokenInfo):
        return Decimal(amount0) / 10 ** asset.decimal

    def notify(self, strategy: Strategy, actions: list[BaseAction]):  # 默认参数, 使用不可变对象
        if not self.enable_notify:
            return
        if len(actions) < 1:
            return
        strategy.notify_on_next(actions)
        for event in actions:
            match event.action_type:
                case ActionTypeEnum.add_liquidity:
                    strategy.notify_add_liquidity(event)
                case ActionTypeEnum.remove_liquidity:
                    strategy.notify_remove_liquidity(event)
                case ActionTypeEnum.collect_fee:
                    strategy.notify_collect_fee(event)
                case ActionTypeEnum.buy:
                    strategy.notify_buy(event)
                case ActionTypeEnum.sell:
                    strategy.notify_sell(event)
                case _:
                    strategy.notify(event)

    def load_data(self, chain: str, contract_addr: str, start_date: date, end_date: date):
        self.logger.info("start load files...")
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

        # 填充空白数据(每天的头几分钟可能空白)
        full_indexes = pd.date_range(start=df.index[0], end=df.index[df.index.size - 1], freq="1min")
        df = df.reindex(full_indexes)
        df = Lines.from_dataframe(df)
        df = df.fillna()
        self.add_statistic_column(df)
        self.data = df
        self.logger.info("data has benn prepared")

    def add_statistic_column(self, df):
        # 增加统计列
        df["open"] = df["openTick"].map(lambda x: self.broker.tick_to_price(x))
        df["price"] = df["closeTick"].map(lambda x: self.broker.tick_to_price(x))
        high_name, low_name = ("lowestTick", "highestTick") if self.broker.pool_info.is_token0_base \
            else ("highestTick", "lowestTick")
        df["low"] = df[high_name].map(lambda x: self.broker.tick_to_price(x))
        df["high"] = df[low_name].map(lambda x: self.broker.tick_to_price(x))
        df["volume0"] = df["inAmount0"].map(lambda x: Decimal(x) / 10 ** self.broker.pool_info.token0.decimal)
        df["volume1"] = df["inAmount1"].map(lambda x: Decimal(x) / 10 ** self.broker.pool_info.token1.decimal)

    def run(self):
        self.reset()
        self.logger.info("init strategy...")
        self.init_strategy()
        if self._data is None:
            return
        if not isinstance(self._data, Lines):
            raise ZelosError("Data must be instance of Lines")
        row_id = 0
        first = True
        self.logger.info("start main loop...")
        for index, row in self._data.iterrows():
            row_data = RowData()
            setattr(row_data, "timestamp", index.to_pydatetime())
            setattr(row_data, "row_id", row_id)
            row_id += 1
            for column_name in row.index:
                setattr(row_data, column_name, row[column_name])
            # 执行策略, 以及一些计算
            # 更新price tick
            self.broker.current_data = PoolStatus(index.to_pydatetime(),
                                                  row_data.closeTick,
                                                  row_data.currentLiquidity,
                                                  row_data.inAmount0,
                                                  row_data.inAmount1,
                                                  row_data.price)
            self._strategy.next(index.to_pydatetime(), row_data)
            # 更新broker中的统计信息, 比如价格, 手续费
            # 顺便从broker中读取新添加的event
            self._broker.update_on_bar(row_data)
            if first:
                init_price = row_data.price
                first = False
            self.bar_status.append(self._broker.get_status(row_data.price))

            # 通知
            # 汇报在这次迭代发生了哪些操作
            current_event_list = self.bar_actions.copy()
            for event in current_event_list:
                event.timestamp = index
            self.bar_actions.clear()

            if current_event_list and len(current_event_list) > 0:
                self._actions.extend(current_event_list)
                self.notify(self.strategy, current_event_list)

            # 准备处理下一条
            self._data.move_cursor_to_next()
        self.logger.info("main loop finished, start calculate evaluating indicator...")
        bar_status_df = pd.DataFrame(columns=BarStatusNames,
                                     index=self.data.index,
                                     data=map(lambda d: d.to_array(), self.bar_status))
        # 评价指标计算
        self.logger.info("run evaluating indicator")
        self._evaluator = Evaluator(self._broker.get_init_status(init_price), bar_status_df)
        self._evaluator.run()
        self.logger.info("back testing finish")
        self.__backtest_finished = True

    def output(self):
        if self.__backtest_finished:
            # 最终状态
            print("Final status")
            print(self.broker.get_status(self.data.tail(1).price[0]).get_output_str())
            # 评价指标
            print("Evaluating indicator")
            print(self._evaluator.evaluating_indicator.get_output_str())
        else:
            raise ZelosError("please run strategy first")

    def init_strategy(self):
        if not isinstance(self._strategy, Strategy):
            raise ZelosError("strategy must be inherit from Strategy")
        # 策略可以直接调用相关的对象
        self._strategy.broker = self._broker
        self._strategy.data = self._data

        # 执行策略的初始化
        self._strategy.initialize()

    def __str__(self):
        return f"Demeter(broker:{self._broker})\n" \
               f"data(data length: {0 if self._data is None else len(self._data)})"
