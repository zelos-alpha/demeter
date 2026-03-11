import logging
import os
import platform
import time
import traceback
from multiprocessing import Pool, cpu_count, set_start_method
from multiprocessing.pool import ApplyResult
from typing import List

from ._typing import StrategyConfig, BacktestData, BacktestConfig
from .actuator import Actuator
from ..strategy import Strategy
from ..utils import config_log

global_data: BacktestData | None = None

config_log()

logger = logging.getLogger("BacktestManager")


def _start_with_global_data(config: StrategyConfig, strategy: Strategy, bk_config: BacktestConfig):
    return _start(config, global_data, strategy, bk_config)


def _start_with_param_data(config: StrategyConfig, data: BacktestData, strategy: Strategy, bk_config: BacktestConfig):
    return _start(config, data, strategy, bk_config)


def _start(config: StrategyConfig, data: BacktestData, strategy: Strategy, bk_config: BacktestConfig):
    logger.info(f"Start with process id: {os.getpid()}, id of data object {id(data)}")
    actuator = Actuator()
    for market in config.markets:
        # add market to broker
        actuator.broker.add_market(market)
        market.data = data.data[market.market_info]
    for asset, amount in config.assets.items():
        # Initial some fund to broker.
        actuator.broker.set_balance(asset, amount)
    # Set strategy to actuator
    actuator.strategy = strategy
    actuator.set_price(data.prices, quote_token=bk_config.quote_token)
    actuator.print_action = bk_config.print_actions
    actuator.interval = bk_config.interval
    actuator.run(bk_config.print_result)


def e_callback(e):
    traceback.print_exception(e)


class BacktestManager:
    def __init__(
        self,
        config: StrategyConfig | None = None,
        data: BacktestData | None = None,
        strategies: List[Strategy] = None,
        backtest_config: BacktestConfig | None = None,
        threads=1,
    ):
        self.config: StrategyConfig | None = config
        self.data: BacktestData | None = data
        self.backtest_config: BacktestConfig | None = backtest_config

        if strategies is None:
            self.strategies: List[Strategy] = []
        else:
            self.strategies = strategies
        self.threads = threads

    def add_strategy(self, stg: Strategy):
        self.strategies.append(stg)

    def run(self):
        if self.config is None:
            raise RuntimeError("Config has not set")
        if self.data is None:
            raise RuntimeError("Data has not set")
        start_time = time.time()  # 1681718968.267463
        if len(self.strategies) < 1:
            return
        elif len(self.strategies) == 1 or self.threads == 1:
            # start in single thread by default
            for strategy in self.strategies:
                actuator = _start_with_param_data(self.config, self.data, strategy, self.backtest_config)
                e_callback(actuator)
        else:
            if self.threads > cpu_count():
                raise RuntimeError("Threads should lower than " + cpu_count())

            if "Windows" in platform.system():
                logger.warning(
                    "In windows data will be copied to every subprocess, which will cause a waste of memory, please consider use WSL"
                )
                with Pool(processes=self.threads) as pool:
                    tasks = []
                    for strategy in self.strategies:
                        result1 = pool.apply_async(
                            _start_with_param_data,
                            args=(self.config, self.data, strategy, self.backtest_config),
                            error_callback=e_callback,
                        )
                        tasks.append(result1)
                    [x.wait() for x in tasks]
            else:
                set_start_method("fork")  # ensure linux and macos have the same behavior
                global global_data
                global_data = self.data  # to keep there only one instance among processes
                with Pool(processes=self.threads) as pool:
                    tasks: List[ApplyResult] = []
                    for strategy in self.strategies:
                        result1 = pool.apply_async(
                            _start_with_global_data,
                            args=(
                                self.config,
                                strategy,
                                self.backtest_config,
                            ),  # do not pass data here as it will generate a new copy in subprocess
                            error_callback=e_callback,
                        )
                        tasks.append(result1)
                    [x.wait() for x in tasks]
                pass
        logger.info(f"All backtest finished, total execute time {(time.time() - start_time):.3f}s")
