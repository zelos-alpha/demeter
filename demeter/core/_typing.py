from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import NamedTuple, List, Dict, Tuple, Callable

import pandas as pd

from .actuator import Actuator
from .. import TokenInfo, MarketInfo
from ..broker import Market


class BacktestData(NamedTuple):
    data: Dict[MarketInfo, pd.DataFrame]
    prices: Tuple[pd.DataFrame, TokenInfo]


@dataclass
class StrategyConfig:
    assets: Dict[TokenInfo, Decimal | float]
    markets: List[Market]


@dataclass
class BacktestConfig:
    print_actions = False
    print_result = False
    interval: str = "1min"
    callback: Callable[[Actuator], None] | None = None
    # save_result = False
