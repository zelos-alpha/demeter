import tempfile
from typing import List

from joblib import Memory, Parallel, delayed

from ._typing import StrategyConfig, BacktestData
from .actuator import Actuator
from .. import Strategy, DemeterError

with tempfile.TemporaryDirectory() as tempdir:
    memory = Memory(tempdir, verbose=0)


@memory.cache
def multi_processes_start(config: StrategyConfig, data: BacktestData, strategy: Strategy):
    start(config, data, strategy)


def single_process_start(config: StrategyConfig, data: BacktestData, strategy: Strategy):
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
            single_process_start(self.config, self.data, self.strategies[0])
        else:
            Parallel(n_jobs=self.threads)(
                delayed(multi_processes_start)(self.config, self.data, stg) for stg in self.strategies
            )
