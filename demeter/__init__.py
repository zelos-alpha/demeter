"""
A backtest package for uniswap and aave
"""

from ._typing import (
    DemeterError,
    DemeterWarning,
    TokenInfo,
    UnitDecimal,
    DECIMAL_0,
    DECIMAL_1,
    ChainType,
    Formats,
    STABLE_COINS,
)
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
from .result import BackTestDescription