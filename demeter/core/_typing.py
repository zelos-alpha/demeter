from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import NamedTuple, List, Dict, Tuple, Callable

import pandas as pd

from .actuator import Actuator
from .. import TokenInfo, MarketInfo
from ..broker import Market


class BacktestData(NamedTuple):
    """
    Data will be used in backtest

    :param data: backtest data
    :type data: Dict[MarketInfo, pd.DataFrame]
    :param prices: price during backtest, the first Dataframe is price of all involved tokens, the second TokenInfo is base token.
    :type prices: Tuple[pd.DataFrame, TokenInfo]

    """
    data: Dict[MarketInfo, pd.DataFrame]
    prices: Tuple[pd.DataFrame, TokenInfo]


@dataclass
class StrategyConfig:
    """
    Configuration for your strategy.

    :param assets: Initial asset amount.
    :type assets: Dict[TokenInfo, Decimal | float]
    :param markets: Market instances
    :type markets: List[Market]
    """
    assets: Dict[TokenInfo, Decimal | float]
    markets: List[Market]


@dataclass
class BacktestConfig:
    """
    Configuration for Backtesting.

    :param print_actions: Print trades during backtesting
    :type print_actions: bool
    :param print_result: Print backtest result when finished
    :type print_result: bool
    :param interval: Backtest interval, default is 1 minute,
    :type interval: str
    :param callback: A function will be called after backtest.
    :type callback:  Callable[[Actuator], None] | None = None
    """
    print_actions:bool = False
    print_result: bool = False
    interval: str = "1min"
    quote_token:TokenInfo = None
