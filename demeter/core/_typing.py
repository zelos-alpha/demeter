from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import NamedTuple, List, Dict, Tuple

import pandas as pd

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

    # save_result = False
