import logging
import os
import pickle
import time
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass, field
import orjson
import pandas as pd
from tqdm import tqdm  # process bar

from .evaluating_indicator import Evaluator
from .. import Broker, RowData, Asset
from .._typing import DemeterError, EvaluatorEnum, UnitDecimal
from ..broker import BaseAction, AccountStatus, MarketInfo, MarketDict
from ..uniswap import UniLpMarket, PositionInfo
from ..strategy import Strategy
from ..utils import get_formatted_predefined, STYLE


class Actuator(object):
    """
    Core component of a back test. Manage the resources in a test, including broker/strategy/data/indicator,



    """

    def __init__(self, allow_negative_balance=False):
        """
        init Actuator
        :param allow_negative_balance: balance can less than 0
        """
        # all the actions during the test(buy/sell/add liquidity)
        self._action_list: List[BaseAction] = []
        self._currents = Currents()
        # broker status in every bar, use array for performance
        self._account_status_list: List[AccountStatus] = []
        self._account_status_df: pd.DataFrame | None = None

        # broker
        self._broker: Broker = Broker(allow_negative_balance, self._record_action_list)
        # strategy
        self._strategy: Strategy = Strategy()
        self._token_prices: pd.DataFrame | None = None
        # path of source data, which is saved by downloader
        # evaluating indicator calculator
        self._evaluator: Evaluator | None = None
        self._enabled_evaluator: [] = []
        # logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)

        # internal var
        self.__backtest_finished = False

    def _record_action_list(self, action: BaseAction):
        """
        record action list
        :param action: action
        :return: None
        """
        action.timestamp = self._currents.timestamp
        action.set_type()
        self._action_list.append(action)
        self._currents.actions.append(action)

    # region property
    @property
    def account_status(self) -> List[AccountStatus]:
        """
        account status of all market,
        """
        return self._account_status_list

    @property
    def token_prices(self):
        """
        price of all token
        :return: None
        """
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
        self._evaluator: Evaluator | None = None
        self._enabled_evaluator: [] = []

        self._action_list = []
        self._currents = Currents()
        self._account_status_list = []
        self.__backtest_finished = False

        self._account_status_df: pd.DataFrame | None = None

    @property
    def actions(self) -> List[BaseAction]:
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

    def get_account_status_dataframe(self) -> pd.DataFrame:
        """
        get account status dataframe
        :return: dataframe
        """
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
        """
        set price
        :param prices: dataframe or series
                                                       eth  usdc
        2022-08-20 00:00:00  1610.553895752868641174609110     1
        2022-08-20 00:01:00  1612.487623747744872677867817     1
        2022-08-20 00:02:00  1615.715664560742874527210287     1
        2022-08-20 00:03:00  1615.715664560742874527210287     1
        2022-08-20 00:04:00  1615.554109149827891738036484     1
        ...                                            ...   ...
        2022-08-20 23:55:00  1577.086574012079067849553855     1
        2022-08-20 23:56:00  1576.928881123966671182435611     1
        2022-08-20 23:57:00  1576.928881123966671182435611     1
        2022-08-20 23:58:00  1576.613542649301384412539259     1
        2022-08-20 23:59:00  1576.613542649301384412539259     1
        [1440 rows x 2 columns]
        :return: None
        """
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
        """
        check backtest result
        :return:
        """
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
        for token in self._broker.assets.keys():  # dict_keys([TokenInfo(name='usdc', decimal=6), TokenInfo(name='eth', decimal=18)])
            if token.name not in self._token_prices:
                raise DemeterError(f"Price of {token.name} has not set yet")

        data_length = []  # [1440]
        for market in self._broker.markets.values():
            data_length.append(len(market.data.index))
            market.check_market()  # check each market, including assets
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

    def __get_market_row_dict(self, index, row_id) -> MarketDict:
        """
        get market row dict info
        :param index:
        :param row_id:
        :return: Market dict
        """
        market_dict = MarketDict()
        for market_key, market in self._broker.markets.items():
            market_row = RowData(index.to_pydatetime(), row_id)
            df_row = market.data.loc[index]
            for column_name in df_row.index:
                setattr(market_row, column_name, df_row[column_name])
            market_dict[market_key] = market_row
        market_dict.set_default_key(self.broker.markets.get_default_key())
        return market_dict

    def __set_row_to_markets(self, timestamp, market_row_dict: dict, update: bool = False):
        """
        set markets row data
        :param timestamp:
        :param market_row_dict:
        :param update: enable or disable has_update flag in markets, if set to false, will always update, if set to true, just update when necessary
        :return:
        """

        # 过时的设计, 可以优化.
        # 数据是从market中获取的. 没必要再给set回去. 直接传入一个index就可以了
        for market_key, market_row_data in market_row_dict.items():
            if (not update) or (update and self._broker.markets[market_key].has_update):
                self._broker.markets[market_key].set_market_status(timestamp, market_row_data, self._token_prices.loc[timestamp])

    def run(self, evaluator: List[EvaluatorEnum] | None = None, output: bool = True):
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

        :param evaluator: enable evaluating indicator.
        :type evaluator: List[EvaluatorEnum]
        :param output: enable output.
        :type output: bool
        """
        evaluator = evaluator if evaluator is not None else []
        run_begin_time = time.time()  # 1681718968.267463
        self.reset()

        self._enabled_evaluator = evaluator
        self._check_backtest()
        index_array: pd.DatetimeIndex = list(self._broker.markets.values())[0].data.index
        self.logger.info("init strategy...")

        # set initial status for strategy, so user can run some calculation in initial function.
        init_row_data = self.__get_market_row_dict(index_array[0], 0)
        self.__set_row_to_markets(index_array[0], init_row_data, False)
        # keep initial balance for evaluating
        init_account_status = self._broker.get_account_status(self._token_prices.head(1).iloc[0])
        self.init_strategy()
        row_id = 0
        data_length = len(index_array)
        self.logger.info("start main loop...")
        with tqdm(total=data_length, ncols=150) as pbar:
            for timestamp_index in index_array:
                current_price = self._token_prices.loc[timestamp_index]
                # prepare data of a row
                market_row_dict = self.__get_market_row_dict(timestamp_index, row_id)
                row_id += 1
                self.__set_row_to_markets(timestamp_index, market_row_dict, False)
                # execute strategy, and some calculate
                self._currents.timestamp = timestamp_index.to_pydatetime()

                if self._strategy.triggers:
                    for trigger in self._strategy.triggers:
                        if trigger.when(market_row_dict, current_price):
                            trigger.do(market_row_dict, current_price)
                self._strategy.on_bar(market_row_dict, current_price)

                # important, take uniswap market for example,
                # if liquidity has changed in the head of this minute, this will add the new liquidity to total_liquidity in current minute.
                self.__set_row_to_markets(timestamp_index, market_row_dict, True)

                # update broker status, eg: re-calculate fee
                # and read the latest status from broker
                for market in self._broker.markets.values():
                    market.update()

                self._strategy.after_bar(market_row_dict, current_price)

                self._account_status_list.append(self._broker.get_account_status(current_price, timestamp_index))
                # notify actions in current loop
                self.notify(self.strategy, self._currents.actions)
                self._currents.actions = []
                # move forward for process bar and index
                pbar.update()

        self.logger.info("main loop finished")
        self._account_status_df: pd.DataFrame = self.get_account_status_dataframe()

        if len(self._enabled_evaluator) > 0:
            self.logger.info("Start calculate evaluating indicator...")
            self._evaluator = Evaluator(init_account_status, self._account_status_df, self._token_prices)
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
        self.logger.info(f"Print actuator summary")
        print(self.broker.formatted_str())
        print(get_formatted_predefined("Account Status", STYLE["header1"]))
        print(self._account_status_df)
        if len(self._enabled_evaluator) > 0:
            print("Evaluating indicator")
            print(self._evaluator)

    def save_result(self, path: str, account=True, actions=True) -> List[str]:
        """
        save back test result
        :param path: path to save
        :type path: str
        :param account: Save account status or not
        :type account: bool
        :param actions: Save actions or not
        :type actions: bool
        :return:
        :rtype:
        """
        if not self.__backtest_finished:
            raise DemeterError("Please run strategy first")
        file_name_head = "backtest-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        if not os.path.exists(path):
            os.mkdir(path)
        file_list = []
        if account:
            file_name = os.path.join(path, file_name_head + ".account.csv")
            self._account_status_df.to_csv(file_name)
            file_list.append(file_name)
        if actions:
            # save pkl file to load again
            pkl_name = os.path.join(path, file_name_head + ".action.pkl")
            with open(pkl_name, "wb") as outfile1:
                pickle.dump(self._action_list, outfile1)
            # save json to read
            actions_json_str = orjson.dumps(self._action_list, option=orjson.OPT_INDENT_2, default=json_default)
            json_name = os.path.join(path, file_name_head + ".action.json")
            with open(json_name, "wb") as outfile:
                outfile.write(actions_json_str)

            file_list.append(json_name)
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
        self._strategy.get_account_status_dataframe = self.get_account_status_dataframe
        for k, v in self.broker.markets.items():
            setattr(self._strategy, k.name, v)
        for k, v in self.broker.assets.items():
            setattr(self._strategy, k.name, v)
        self._strategy.initialize()

    def __str__(self):
        return '{{"broker":{}, "action_count":{}, "timestamp":"{}", "strategy":"{}", "price_df_rows":{}, "price_assets":{} }}'.format(
            str(self.broker),
            len(self._action_list),
            self._currents.timestamp,
            type(self._strategy).__name__,
            len(self._token_prices.index) if self._token_prices is not None else 0,
            "[" + ",".join(f'"{x}"' for x in self._token_prices.columns) + "]" if self._token_prices is not None else str([]),
        )


@dataclass
class Currents:
    actions: List[BaseAction] = field(default_factory=list)
    timestamp: datetime = None


def json_default(obj):
    """
    format json data
    :param obj:
    :return:
    """
    if isinstance(obj, UnitDecimal):
        return obj.to_str()
    elif isinstance(obj, MarketInfo):
        return {"name": obj.name}
    elif isinstance(obj, PositionInfo):
        return {"lower_tick": obj.lower_tick, "upper_tick": obj.upper_tick}
    else:
        raise TypeError
