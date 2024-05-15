"""
A backtest package for uniswap and aave
"""

from ._typing import DemeterError, TokenInfo, UnitDecimal, DECIMAL_0, DECIMAL_1, EvaluatorEnum, ChainType
from .broker import (
    Broker,
    MarketStatus,
    MarketInfo,
    Asset,
    MarketDict,
    AssetDict,
    AccountStatus,
    MarketTypeEnum,
    BaseAction,
    RowData,
    ActionTypeEnum,
)

from .core import Actuator
from .indicator import simple_moving_average, exponential_moving_average, realized_volatility
from .strategy import (
    Strategy,
    Trigger,
    TimeRangesTrigger,
    TimeRangeTrigger,
    TimeRange,
    PeriodTrigger,
    PeriodsTrigger,
    AtTimesTrigger,
    AtTimeTrigger,
    PriceTrigger,
)
