from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple, List, Dict

import pandas as pd
from .. import Strategy, TokenInfo
from ..broker import Market

class BacktestData(NamedTuple):
    data: pd.DataFrame
    prices: pd.DataFrame


@dataclass
class StrategyConfig:
    start: datetime
    end: datetime
    assets:Dict[TokenInfo,Decimal]
    markets:List[Market]
    strategy:Strategy