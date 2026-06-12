"""
Indicator is a group of calculators, can be used in strategy or somewhere else.
"""

__all__ = [
    "simple_moving_average",
    "exponential_moving_average",
    "realized_volatility",
]

from .ma import simple_moving_average, exponential_moving_average
from .volatility import realized_volatility
