import logging
import time
from typing import List, Dict

import pandas as pd
from tqdm import tqdm  # process bar

from .evaluating_indicator import Evaluator
from .. import Broker, RowData, Asset
from .._typing import DemeterError, EvaluatorEnum, UnitDecimal
from ..broker import UniLpMarket, BaseAction, AccountStatus, MarketInfo
from ..strategy import Strategy
from ..utils import get_formatted_from_dict, get_formatted_predefined, ForColorEnum, BackColorEnum, ModeEnum, STYLE


class Actuator(object):
    """
    Core component of a back test. Manage the resources in a test, including broker/strategy/data/indicator,



    """

    def __init__(self, allow_negative_balance=False):
        # all the actions during the test(buy/sell/add liquidity)
        self._action_list: List[BaseAction] = []
        self._current_actions: List[BaseAction] = []
        # broker status in every bar, use array for performance
        self._account_status_list: List[AccountStatus] = []
        # broker
        self._broker: Broker = Broker(allow_negative_balance, self._record_action_list)
        # strategy
        self._strategy: Strategy = Strategy()
        self._token_prices: pd.DataFrame = None
        # path of source data, which is saved by downloader
        # evaluating indicator calculator
        self._evaluator: Evaluator = None
        self._enabled_evaluator: [] = []
        # logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # internal var
        self.__backtest_finished = False

    def _record_action_list(self, actions):
        self._action_list.append(actions)
        self._current_actions.append(actions)

    # region property
    @property
    def account_status(self) -> List[AccountStatus]:
        return self._account_status_list

    @property
    def token_prices(self):
        return self._token_prices

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

    def reset(self):
        """

        reset all the status variables

        """
        self._evaluator: Evaluator = None
        self._enabled_evaluator: [] = []

        self._action_list = []
        self._current_actions = []
        self._account_status_list = []
        self.__backtest_finished = False

    @property
    def actions(self) -> [BaseAction]:
        """
        all the actions during the test(buy/sell/add liquidity)

        :return: action list
        :rtype: [BaseAction]
        """
        return self._action_list

    @property
    def evaluating_indicator(self) -> Dict[EvaluatorEnum, UnitDecimal]:
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

    def account_status_dataframe(self) -> pd.DataFrame:
        return AccountStatus.to_dataframe(self._account_status_list)

    def set_assets(self, assets: List[Asset]):
        """
        set initial balance for token

        :param assets: assets to set.
        :type assets: [Asset]
        """
        for asset in assets:
            self._broker.set_balance(asset.token_info, asset.balance)

    def set_price(self, prices: pd.DataFrame | pd.Series):
        if isinstance(prices, pd.DataFrame):
            if self._token_prices is None:
                self._token_prices = prices
            else:
                self._token_prices = pd.concat([self._token_prices, prices])
        else:
            if self._token_prices is None:
                self._token_prices = pd.DataFrame(data=prices, index=prices.index)
            else:
                self._token_prices[prices.name] = prices

    def notify(self, strategy: Strategy, actions: List[BaseAction]):
        """

        notify user when new action happens.

        :param strategy: Strategy
        :type strategy: Strategy
        :param actions:  action list
        :type actions: [BaseAction]
        """
        if len(actions) < 1:
            return
        # last_time = datetime(1970, 1, 1)
        for action in actions:
            # if last_time != action.timestamp:
            #     print(f"\033[7;34m{action.timestamp} \033[0m")
            #     last_time = action.timestamp
            strategy.notify(action)

    def _check_backtest(self):
        # ensure a market exist
        if len(self._broker.markets) < 1:
            raise DemeterError("No market assigned")
        # ensure all token has price list.
        if self._token_prices is None:
            # if price is not set and market is uni_lp_market, get price from market automatically
            for market in self.broker.markets.values():
                if isinstance(market, UniLpMarket):
                    self.set_price(market.get_price_from_data())
            if self._token_prices is None:
                raise DemeterError("token prices is not set")
        for token in self._broker.assets.keys():
            if token.name not in self._token_prices:
                raise DemeterError(f"Price of {token.name} has not set yet")
        [market.check_before_test() for market in self._broker.markets.values()]

        data_length = []
        for market in self._broker.markets.values():
            data_length.append(len(market.data.index))
            market.check_asset()  # check each market, including assets
        # ensure data length same
        if List.count(data_length, data_length[0]) != len(data_length):
            raise DemeterError("data length among markets are not same")
        if len(self._token_prices.index) != data_length[0]:
            raise DemeterError("price length and data length are not same")
        length = data_length[0]
        # ensure data interval same
        data_interval = []
        if length > 1:
            for market in self._broker.markets.values():
                data_interval.append(market.data.index[1] - market.data.index[0])
            if List.count(data_interval, data_interval[0]) != len(data_interval):
                raise DemeterError("data interval among markets are not same")
            price_interval = self._token_prices.index[1] - self._token_prices.index[0]
            if price_interval != data_interval[0]:
                raise DemeterError("price list interval and data interval are not same")

    def __get_market_row_dict(self, index, row_id) -> Dict[MarketInfo, RowData]:
        markets_row = {}
        for market_key, market in self._broker.markets.items():
            market_row = RowData(index.to_pydatetime(), row_id)
            df_row = market.data.loc[index]
            for column_name in df_row.index:
                setattr(market_row, column_name, df_row[column_name])
            markets_row[market_key] = market_row
        return markets_row

    def __set_row_to_markets(self, timestamp, market_row_dict: dict):
        for market_key, market_row_data in market_row_dict.items():
            self._broker.markets[market_key].set_market_status(timestamp, market_row_data)

    def run(self,
            evaluator: List[EvaluatorEnum] = [],
            output: bool = True,
            save_results: bool = False,
            save_results_path: str = "."):
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
        index_array: pd.DatetimeIndex = list(self._broker.markets.values())[0].data.index
        self.logger.info("init strategy...")

        # set initial status for strategy, so user can run some calculation in initial function.
        init_row_data = self.__get_market_row_dict(index_array[0], 0)
        self.__set_row_to_markets(index_array[0], init_row_data)
        # keep initial balance for evaluating
        init_account_status = self._broker.get_account_status(self._token_prices.iloc[0])
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
                self.__set_row_to_markets(timestamp_index, market_row_dict)
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
                self._account_status_list.append(
                    self._broker.get_account_status(self._token_prices.loc[timestamp_index], timestamp_index))
                # notify actions in current loop
                self.notify(self.strategy, self._current_actions)
                self._current_actions = []
                # move forward for process bar and index
                pbar.update()

        self.logger.info("main loop finished")

        if len(self._enabled_evaluator) > 0:
            self.logger.info("Start calculate evaluating indicator...")
            account_status_df: pd.DataFrame = self.account_status_dataframe()
            self._evaluator = Evaluator(init_account_status, account_status_df, self._token_prices)
            self._evaluator.run(self._enabled_evaluator)
            self.logger.info("Evaluating indicator has finished it's job.")
        self._strategy.finalize()
        self.__backtest_finished = True
        if output:
            self.output()
        self.logger.info(f"Backtesting finished, execute time {time.time() - run_begin_time}s")

    def output(self):
        """
        output back test result to console
        """
        if not self.__backtest_finished:
            raise DemeterError("Please run strategy first")
        print(self.broker.formatted_str())
        print(get_formatted_predefined("Account Status", STYLE["header1"]))
        print(self.account_status_dataframe())
        if len(self._enabled_evaluator) > 0:
            print("Evaluating indicator")
            print(self._evaluator.result)

    def init_strategy(self):
        """
        initialize strategy, set property to strategy. and run strategy.initialize()
        """
        if not isinstance(self._strategy, Strategy):
            raise DemeterError("strategy must be inherit from Strategy")
        self._strategy.broker = self._broker
        self._strategy.data = {k: v.data for k, v in self.broker.markets.items()}
        self._strategy.account_status = self._account_status_list
        self._strategy.account_status_dataframe = self.account_status_dataframe
        for k, v in self.broker.markets.items():
            setattr(self._strategy, k.name, v)
        for k, v in self.broker.assets.items():
            setattr(self._strategy, k.name, v)
        self._strategy.initialize()

    def __str__(self):
        return f"Demeter Actuator (broker:{self._broker})\n"
