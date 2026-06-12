"""
A backtest package for uniswap and aave
"""

__all__ = [
    # from ._typing
    "DemeterError",
    "DemeterAssertionError",
    "DemeterWarning",
    "TokenInfo",
    "UnitDecimal",
    "DECIMAL_0",
    "DECIMAL_1",
    "ChainType",
    "Formats",
    "STABLE_COINS",
    "USD",
    # from .broker
    "Broker",
    "MarketStatus",
    "MarketInfo",
    "Asset",
    "MarketDict",
    "AssetDict",
    "AccountStatus",
    "MarketTypeEnum",
    "BaseAction",
    "Snapshot",
    "ActionTypeEnum",
    # from .core
    "Actuator",
    "BacktestManager",
    "BacktestConfig",
    "BacktestData",
    "StrategyConfig",
    # from .indicator
    "simple_moving_average",
    "exponential_moving_average",
    "realized_volatility",
    # from .strategy
    "Strategy",
    "Trigger",
    "TimeRangesTrigger",
    "TimeRangeTrigger",
    "TimeRange",
    "PeriodTrigger",
    "PeriodsTrigger",
    "AtTimesTrigger",
    "AtTimeTrigger",
    "PriceTrigger",
    # from .result
    "BackTestDescription",
]

from ._typing import (
    DemeterError,
    DemeterAssertionError,
    DemeterWarning,
    TokenInfo,
    UnitDecimal,
    DECIMAL_0,
    DECIMAL_1,
    ChainType,
    Formats,
    STABLE_COINS,
    USD
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
    Snapshot,
    ActionTypeEnum,
)

from .core import Actuator, BacktestManager, BacktestConfig, BacktestData, StrategyConfig


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
