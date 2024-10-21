import logging
import os
import pickle
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Union, Tuple

import pandas as pd
from pandas import Timestamp
from tqdm import tqdm  # process bar

from .. import Broker, Asset, ActionTypeEnum
from .._typing import (
    DemeterError,
    UnitDecimal,
    DemeterWarning,
    TokenInfo,
    USD,
    DemeterLog,
)
from ..broker import BaseAction, AccountStatus, MarketInfo, MarketDict, MarketStatus, RowData
from ..result import BackTestDescription
from ..strategy import Strategy
from ..uniswap import PositionInfo
from ..utils import console_text
from ..utils import get_formatted_predefined, STYLE, to_decimal, to_multi_index_df

BASIC_INTERVAL = pd.Timedelta("1min")


@dataclass
class RunningCount:
    get_account_status_df: int = 0


class Actuator(object):
    """
    Core component of a back test. Manage the resources in a test, including broker/strategy/data/indicator,

    :param allow_negative_balance: Allow cash balance of broker can be negative value or not. Default is False
    :type allow_negative_balance: bool
    """

    def __init__(self, allow_negative_balance=False):
        """
        init Actuator
        """
        # all the actions during the test(buy/sell/add liquidity)
        self._action_list: List[BaseAction] = []
        self._logs: List[DemeterLog] = []
        self._currents = Currents()
        # broker status in every bar, use array for performance
        self._account_status_list: List[AccountStatus] = []
        self._account_status_df: pd.DataFrame | None = None

        # broker
        self._broker: Broker = Broker(allow_negative_balance, self._record_action_list)
        # strategy
        self._strategy: Strategy = Strategy()
        self._token_prices: pd.DataFrame | None = None
        # logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)
        # internal var
        self.__start_time = None
        self.__backtest_duration = None
        self.__backtest_finished = False
        self.__runnning_count: RunningCount = RunningCount()
        self.print_action = False
        self.init_account_status = None
        # set backtest with other freq to make it faster, freq should be larger than 1 minute
        self.interval: str = "1min"

    def _record_action_list(self, action: BaseAction):
        """
        record action list

        :param action: action
        :type action: BaseAction
        """
        action.timestamp = self._currents.timestamp
        action.set_type()
        self._action_list.append(action)
        self._currents.actions.append(action)
        self._log(action.timestamp, f"{action.market}: {action.action_type.name}, {action.comment}")

    # region property
    @property
    def account_status(self) -> List[AccountStatus]:
        """
        | Get account status list.
        | Account status includes balances, net values and positions.
        | Each element in this list stands for one minute.
        | It is good to call it during backtest.
        | After backtest, it's better to use account_status_df.
        """
        return self._account_status_list

    @property
    def token_prices(self) -> pd.DataFrame:
        """
        Price of all tokens. Row(index) is minutely timestamp, column is token. e.g.

        +-------------------+---------+-------+
        |                   |WETH     | USDC  |
        +===================+=========+=======+
        |2023-08-13 00:00:00| 1848.12 | 1     |
        +-------------------+---------+-------+
        |2023-08-13 00:01:00| 1848.12 | 1     |
        +-------------------+---------+-------+

        they should be quoted by quote_token in backtest.

        :return: data from with prices of all token
        :rtype: DataFrame
        """
        return self._token_prices

    @property
    def final_status(self) -> AccountStatus:
        """
        | Get last account status of back test.
        | Note: If back test has not run, an error will be raised.

        :return: Final state of broker
        :rtype: AccountStatus
        """
        if self.__backtest_finished:
            return self._account_status_list[len(self._account_status_list) - 1]
        else:
            raise DemeterError("please run strategy first")

    def reset(self):
        """
        Reset actuator by re-initiate all the status variables
        """

        self._action_list = []
        self._currents = Currents()
        self._account_status_list = []
        self.__backtest_finished = False

        self._account_status_df: pd.DataFrame | None = None

    @property
    def actions(self) -> List[BaseAction]:
        """
        A list of actions(buy/sell/add liquidity) happened during back test

        :return: A list of actions
        :rtype: List[BaseAction]
        """
        return self._action_list

    @property
    def broker(self) -> Broker:
        """
        | Get broker instance.
        | Brokers are managers of assets. It manages cash and markets(the place to invest assets)

        """
        return self._broker

    @property
    def strategy(self) -> Strategy:
        """
        Get strategy instance

        :return: strategy instance
        :rtype: Strategy
        """
        return self._strategy

    @strategy.setter
    def strategy(self, value):
        """
        Set strategy instance to actuator
        :param value: strategy instance
        :type value: Strategy
        """
        if isinstance(value, Strategy):
            self._strategy = value
        else:
            raise ValueError()

    @property
    def account_status_df(self) -> pd.DataFrame:
        """
        | Get account status in dataframe. it contains account balance/position change of every minute.
        | Row(datetimeindex) is per minute.
        | Column is net value/positions.

        :return: account status
        :rtype: DataFrame
        """
        if not self.__backtest_finished:
            if self.__runnning_count.get_account_status_df >= 10:
                raise DemeterWarning(
                    "Frequent calls to account_status_df will generate multiple DataFrame objects, "
                    "consuming a lot of time and memory. Consider using account_status instead."
                )
            self.__runnning_count.get_account_status_df += 1

            self._account_status_df = AccountStatus.to_dataframe(self._account_status_list)
        return self._account_status_df

    @account_status_df.setter
    def account_status_df(self, new_df: pd.DataFrame):
        if not self.__backtest_finished:
            raise DemeterError("Back test has not finish yet, can not write account_status_df")
        else:
            self._account_status_df = new_df
            self._strategy.account_status_df = new_df

    # endregion
    def comment_last_action(self, message: str, action_type: ActionTypeEnum | None = None):
        if len(self._action_list) < 0:
            raise DemeterWarning("No action yet")
        if action_type is None:
            self._action_list[len(self._action_list) - 1].comment = message
        else:
            for action in reversed(self._action_list):
                if action_type == action.action_type:
                    action.comment = message
                    break

    def set_assets(self, assets: List[Asset]):
        """
        Set initial token balance. That's cash held by the broker.

        :param assets: assets to set.
        :type assets: [Asset]
        """
        for asset in assets:
            self._broker.set_balance(asset.token_info, asset.balance)

    def set_price(
        self, prices: Union[pd.DataFrame, pd.Series, Tuple[pd.DataFrame, TokenInfo]], quote_token: TokenInfo = None
    ):
        """
        | Set price to actuator. param price can be dataframe(price of several tokens) or series(price of one token).
        | It's index time range should be larger than or equal to data.
        | And column name should be the same to token.name in upper case. e.g.

        +-------------------+---------+-------+
        |                   |WETH     | USDC  |
        +===================+=========+=======+
        |2023-08-13 00:00:00| 1848.12 | 1     |
        +-------------------+---------+-------+
        |2023-08-13 00:01:00| 1848.12 | 1     |
        +-------------------+---------+-------+

        :param prices: dataframe or series contains prices
        :type prices: Union[pd.DataFrame, pd.Series, Tuple[pd.DataFrame, TokenInfo]]
        :param quote_token: quote token of price
        :type quote_token: TokenInfo
        """
        if isinstance(prices, pd.DataFrame):
            quote_token = quote_token if quote_token is not None else USD
        elif isinstance(prices, Tuple):  # Got from uniswap market
            quote_token = prices[1]
            prices = prices[0]
        else:
            quote_token = quote_token if quote_token is not None else USD
            prices = pd.DataFrame(data=prices, index=prices.index)

        prices = prices.map(lambda y: to_decimal(y))
        prices[USD.name] = 1
        if self._token_prices is None:
            self._token_prices = prices
        else:
            self._token_prices = pd.concat([self._token_prices, prices])

        if self.broker.quote_token is None:
            self.broker.quote_token = quote_token
        elif self.broker.quote_token != quote_token:
            raise DemeterError(
                f"Quote token is different from previous setting, new value is {quote_token}, "
                f"old is {self.broker.quote_token}"
            )

    def notify(self, strategy: Strategy, actions: List[BaseAction]):
        """
        Call strategy.notify() when new action happens.

        :param strategy: Strategy instance
        :type strategy: Strategy
        :param actions: action list
        :type actions: List[BaseAction]
        """
        if len(actions) < 1:
            return
        # last_time = datetime(1970, 1, 1)
        for action in actions:
            strategy.notify(action)
            if self.print_action:
                print(action.get_output_str())

    def _check_backtest(self):
        if not self.interval[0].isdigit():
            self.interval = "1" + self.interval
        interval_delta = pd.Timedelta(self.interval)
        if interval_delta < BASIC_INTERVAL:
            raise DemeterError("interval should be larger than 1 minute")

        self.broker.check_backtest()

        # ensure all token has price list.
        if self._token_prices is None:
            # if price is not set and market is uni_lp_market, get price from market automatically
            for market in self.broker.markets.values():
                if hasattr(market, "get_price_from_data"):
                    self.set_price(market.get_price_from_data())
            if self._token_prices is None:
                raise DemeterError("token prices is not set")

        default_market_data = self.broker.markets.default.data
        if (
            self._token_prices.index[0] > default_market_data.head(1).index.get_level_values(0).unique()[0]
            or self._token_prices.index[-1] < default_market_data.tail(1).index.get_level_values(0).unique()[0]
        ):
            raise DemeterError("Time range of price doesn't cover market data")

        # check match quote token is in price
        for market in self.broker.markets.values():
            if market.quote_token.name not in self._token_prices.columns:
                raise DemeterError(
                    f"Price dataframe doesn't have {market.quote_token}, it's the quote token of {market.market_info.name}"
                )

    def _log(self, timestamp: datetime, message: str, level: int = logging.INFO):
        self._logs.append(DemeterLog(timestamp, message, level))

    def __get_row_data(self, timestamp, row_id, current_price) -> RowData:
        row_data = RowData(timestamp.to_pydatetime(), row_id, current_price)
        for market_info, market in self.broker.markets.items():
            row_data.market_status[market_info] = market.market_status.data
        row_data.market_status.set_default_key(self.broker.markets.get_default_key())
        return row_data

    def __set_market_timestamp(self, timestamp: Timestamp, update: bool = False):
        """
        set markets row data
        :param timestamp:
        :param update: enable or disable has_update flag in markets, if set to false, will always update, if set to true, just update when necessary
        :return:
        """

        for market_key in self.broker.markets.keys():
            if (not update) or (update and self._broker.markets[market_key].has_update):
                ms = MarketStatus(timestamp, None)
                self._broker.markets[market_key].set_market_status(ms, self._token_prices.loc[timestamp])

    def get_test_range(self):
        longest_data = max(map(lambda m: len(m.data.index.get_level_values(0).unique()), self._broker.markets.values()))
        largest_market = list(
            filter(
                lambda m: len(m.data.index.get_level_values(0).unique()) == longest_data, self._broker.markets.values()
            )
        )[0]
        # start = largest_market.data.head(1).index.get_level_values(0).unique()
        # end = largest_market.data.tail(1).index.get_level_values(0).unique()

        return largest_market.data.index.get_level_values(0).unique()

    def switch_interval(self, index_array: pd.DatetimeIndex) -> pd.DatetimeIndex:
        for mk, market in self.broker.markets.items():
            market._resample(self.interval)
        return pd.Series(0, index=index_array).resample(self.interval).first().index

    def run(self, print_result: bool = True):
        """
        Start back test, the whole process including:

        * reset actuator
        * initialize strategy (set object to strategy, then run strategy.initialize())
        * process each row in data
            * prepare data in this iteration
            * run trigger
            * run strategy.on_bar()
            * update market, e.g. calculate fee earned
            * run strategy.after_bar()
            * get latest account status
            * notify actions
        * run evaluator indicator
        * run strategy.finalize()
        * output result if required

        :param print_result: If true, print backtest result to console.
        :type print_result: bool
        """
        self.__start_time = time.time()  # 1681718968.267463
        self.reset()

        self._check_backtest()
        index_array: pd.DatetimeIndex = (
            self.get_test_range()
        )  # list(self._broker.markets.values())[0].data.index.get_level_values(0).unique()
        if self.interval != "1min":
            self.logger.info(f"Interval is {self.interval}, resampling data...")
            index_array = self.switch_interval(index_array)
        self.logger.info(f"Quote token is {self.broker.quote_token}")
        self.logger.info("init strategy...")

        # set initial status for strategy, so user can run some calculation in initial function.
        self.__set_market_timestamp(index_array[0], False)
        self._currents.timestamp = index_array[0].to_pydatetime()
        # keep initial balance for evaluating
        self.init_account_status = self._broker.get_account_status(
            self._token_prices.head(1).iloc[0], index_array[0].to_pydatetime()
        )
        self.init_strategy()
        row_id = 0
        data_length = len(index_array)
        self.logger.info("start main loop...")
        with tqdm(total=data_length, ncols=150) as pbar:
            try:
                for timestamp_index in index_array:
                    current_price = self._token_prices.loc[timestamp_index]
                    # prepare data of a row

                    self.__set_market_timestamp(timestamp_index, False)
                    # execute strategy, and some calculate
                    self._currents.timestamp = timestamp_index.to_pydatetime()
                    row_data = self.__get_row_data(timestamp_index, row_id, current_price)
                    if self._strategy.triggers:
                        for trigger in self._strategy.triggers:
                            if trigger.when(row_data):
                                trigger.do(row_data)
                    # remove outdate triggers
                    self._strategy.triggers = [
                        x for x in self._strategy.triggers if not x.is_out_date(self._currents.timestamp)
                    ]
                    for market in self.broker.markets.values():
                        if market.is_open and market.open is not None:
                            market.open(row_data)

                    self._strategy.on_bar(row_data)

                    # important, take uniswap market for example,
                    # if liquidity has changed in the head of this minute,
                    # this will add the new liquidity to total_liquidity in current minute.
                    self.__set_market_timestamp(timestamp_index, True)

                    # update broker status, e.g. re-calculate fee
                    # and read the latest status from broker
                    for market in self._broker.markets.values():
                        market.update()

                    row_data = self.__get_row_data(timestamp_index, row_id, current_price)
                    self._strategy.after_bar(row_data)

                    self._account_status_list.append(
                        self._broker.get_account_status(current_price, timestamp_index.to_pydatetime())
                    )
                    # notify actions in current loop
                    self.notify(self.strategy, self._currents.actions)
                    self._currents.actions = []
                    # move forward for process bar and index
                    pbar.update()
                    row_id += 1
            except RuntimeError as e:
                print(f"timestamp on error: " + str(row_data.timestamp))
                self._generate_account_status_df()
                self.save_result("./", "backtest-with-error")
                raise e

        self.logger.info("main loop finished")
        self.__backtest_finished = True
        # generate dataframe first so finalize can use it
        self._generate_account_status_df()
        self._strategy.finalize()
        if print_result:
            self.print_result()

        self.__backtest_duration = time.time() - self.__start_time
        self.logger.info(f"Backtesting finished, execute time {time.time() - self.__start_time}s")

    def _generate_account_status_df(self):
        self._account_status_df: pd.DataFrame = AccountStatus.to_dataframe(self._account_status_list)

        tmp_price_df = (
            self._token_prices.drop(columns=[USD.name])
            .loc[self._account_status_df.index[0] : self._account_status_df.index[-1]]
            .reindex(self._account_status_df.index)
        )
        to_multi_index_df(tmp_price_df, "price")
        self._account_status_df = pd.concat([self._account_status_df, tmp_price_df], axis=1)
        self._strategy.account_status_df = self._account_status_df

    def print_result(self):
        """
        Print backtest result to console, and it will print the following content

        1. Account status (including balances and positions) at the end of the back test.
        2. Balance change during back test.
        3. If evaluating indicator is enabled, will print evaluating of strategy.
        """
        if not self.__backtest_finished:
            raise DemeterError("Please run strategy first")
        self.logger.info(f"Print actuator summary")
        print(get_formatted_predefined("Final account status", STYLE["header1"]))
        print(self.broker.formatted_str())
        print(get_formatted_predefined(f"Quote by: {self.broker.quote_token}", STYLE["key"]))
        print(get_formatted_predefined("Account balance history", STYLE["header1"]))
        console_text.print_dataframe_with_precision(self._account_status_df)

    def save_result(self, path: str, file_name: str = None, decimals: int | None = None, **custom_attr) -> List[str]:
        """
        Save backtesting result

        :param path: path to save
        :type path: str
        :param file_name: file name, default is timestamp
        :type file_name: str
        :param decimals: decimals in csv
        :type decimals: int
        :return: A list of saved file path
        :rtype: List[str]
        """
        # if not self.__backtest_finished:
        #     raise DemeterError("Please run strategy first")
        file_name_head = file_name if file_name is not None else "backtest-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        if not os.path.exists(path):
            os.mkdir(path)
        file_list = []

        # save account file
        file_name = os.path.join(path, file_name_head + ".account.csv")
        df_2_save: pd.DataFrame = self._account_status_df
        if decimals is not None:
            df_2_save = df_2_save.astype(float).round(decimals)

            # df_2_save = df_2_save.map(lambda x: round(x, decimals) if pd.api.types.is_numeric_dtype(type(x)) else x)
        df_2_save.to_csv(file_name)
        file_list.append(file_name)

        # save backtest file
        backtest_result = BackTestDescription(
            strategy_name=type(self._strategy).__name__,
            quote_token=self.broker.quote_token,
            init_status=self.init_account_status.asset_balances,
            assets=list(self.broker.assets.keys()),
            markets=[m.description for m in self.broker.markets.values()],
            actions=self._action_list,
            backtest_start=datetime.fromtimestamp(self.__start_time),
            backtest_duration=self.__backtest_duration,
            backtest_end=datetime.now(),
            logs=self._logs,
        )
        for k, v in custom_attr.items():
            setattr(backtest_result, k, v)
        pkl_name = os.path.join(path, file_name_head + ".pkl")
        with open(pkl_name, "wb") as outfile1:
            pickle.dump(backtest_result, outfile1)

        file_list.append(pkl_name)

        self.logger.info(f"files have saved to {','.join(file_list)}")
        return file_list

    def init_strategy(self):
        """
        initialize strategy, set property to strategy. and run strategy.initialize()
        """
        if not isinstance(self._strategy, Strategy):
            raise DemeterError("strategy must be inherit from Strategy")
        self._strategy.broker = self._broker
        self._strategy.markets = self._broker.markets
        market_datas = MarketDict()
        for k, v in self.broker.markets.items():
            market_datas[k] = v.data
        market_datas.set_default_key(self.broker.markets.get_default_key())
        self._strategy.data = market_datas
        self._strategy.prices = self._token_prices
        self._strategy.account_status = self._account_status_list
        self._strategy.actions = self._action_list
        self._strategy.assets = self.broker.assets
        self._strategy.account_status_df = self.account_status_df
        self._strategy.comment_last_action = self.comment_last_action
        self._strategy.log = self._log
        for k, v in self.broker.markets.items():
            setattr(self._strategy, k.name, v)
        for k, v in self.broker.assets.items():
            setattr(self._strategy, k.name, v)
        self._strategy.initialize()

    def __str__(self):
        return (
            '{{"Account status":{}, "action_count":{}, "timestamp":"{}", "strategy":"{}", '
            '"price_df_rows":{}, "price_assets":{} }}'
        ).format(
            str(self.broker),
            len(self._action_list),
            self._currents.timestamp,
            type(self._strategy).__name__,
            len(self._token_prices.index) if self._token_prices is not None else 0,
            (
                "[" + ",".join(f'"{x}"' for x in self._token_prices.columns) + "]"
                if self._token_prices is not None
                else str([])
            ),
        )


@dataclass
class Currents:
    """
    Values in current timestamp.

    """

    actions: List[BaseAction] = field(default_factory=list)
    """Actions in this iteration"""
    timestamp: datetime = None
    """Current timestamp"""


def _json_default(obj):
    """
    format json data

    :param obj:
    :return:
    """
    if isinstance(obj, UnitDecimal):
        return obj.to_str()
    elif isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, MarketInfo):
        return f"{obj.name}({obj.type.name})"
    elif isinstance(obj, PositionInfo):
        return {"lower_tick": obj.lower_tick, "upper_tick": obj.upper_tick}
    else:
        raise TypeError
