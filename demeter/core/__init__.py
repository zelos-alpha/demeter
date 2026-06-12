"""
Core module of demeter, includes actuator and evaluating indicator
"""

__all__ = [
    "Actuator",
    "BacktestManager",
    "BacktestConfig",
    "BacktestData",
    "StrategyConfig",
]

from .actuator import Actuator
from .backtest import BacktestManager
from ._typing import BacktestConfig, BacktestData, StrategyConfig



