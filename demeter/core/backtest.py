import logging
import platform
import traceback
from multiprocessing import Pool, cpu_count
from typing import List

from ._typing import StrategyConfig, BacktestData
from .actuator import Actuator
from .. import Strategy, DemeterError

global_data: BacktestData | None = None


def start_with_global_data(config: StrategyConfig, strategy: Strategy):
    start(config, global_data, strategy)


def start_with_param_data(config: StrategyConfig, data: BacktestData, strategy: Strategy):
    start(config, data, strategy)


def start(config: StrategyConfig, data: BacktestData, strategy: Strategy):
    actuator = Actuator()
    for market in config.markets:
        # add market to broker
        actuator.broker.add_market(market)
    for asset, amount in config.assets.items():
        # Initial some fund to broker.
        actuator.broker.set_balance(asset, amount)
    # Set strategy to actuator
    actuator.strategy = strategy
    actuator.set_price(data.prices)
    # run test, If you use default parameter, final fund status will be printed in console.
    actuator.run()
    if True:
        actuator.save_result("xxx.csv")


def callback(result):
    print(f"Result: {result}")


def e_callback(e):
    traceback.print_exception(e)


class Backtest:
    def __init__(
        self,
        config: StrategyConfig | None = None,
        data: BacktestData | None = None,
        strategies: List[Strategy] = None,
        threads=4,
    ):
        self.config: StrategyConfig | None = config
        self.data: BacktestData | None = data
        if strategies is None:
            self.strategies: List[Strategy] = []
        else:
            self.strategies = strategies
        self.threads = threads

    def add_strategy(self, stg: Strategy):
        self.strategies.append(stg)

    def run(self):
        if self.config is None:
            raise DemeterError("Config has not set")
        if self.data is None:
            raise DemeterError("Data has not set")

        if len(self.strategies) < 1:
            return
        elif len(self.strategies) == 1:
            # start in single thread by default
            start_with_param_data(self.config, self.data, self.strategies[0])
        else:
            if self.threads > cpu_count():
                raise DemeterError("Threads should lower than " + cpu_count())

            if "Windows" in platform.system():
                logging.warning(
                    "In windows data will be copied to every subprocess, which will lead to a waste of memory, please consider use wsl"
                )
                with Pool(processes=self.threads) as pool:
                    tasks = []
                    for strategy in self.strategies:
                        result1 = pool.apply_async(
                            start_with_param_data,
                            args=(self.config, self.data, strategy),
                            callback=callback,
                            error_callback=e_callback,
                        )
                        tasks.append(result1)
                    [x.get() for x in tasks]
            else:
                global global_data
                global_data = self.data  # to keep there only one instance among processes
                with Pool(processes=self.threads) as pool:
                    tasks = []
                    for strategy in self.strategies:
                        result1 = pool.apply_async(
                            start_with_global_data,
                            args=(
                                self.config,
                                strategy,
                            ),  # do not pass data here as it will generate a new copy in subprocess
                            callback=callback,
                            error_callback=e_callback,
                        )
                        tasks.append(result1)
                    [x.get() for x in tasks]
                pass
