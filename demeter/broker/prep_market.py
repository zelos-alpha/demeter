import logging
from abc import abstractmethod, ABC
from functools import wraps
from typing import Callable

import pandas as pd

from . import Market
from ._typing import BaseAction, MarketBalance, MarketStatus, MarketInfo, Snapshot
from .._typing import DemeterError, TokenInfo, USD


class PrepMarket(Market):
    """

    | Market is the place to invest your assets.
    | This is an abstract class, you should use subclass instead this one

    :param market_info: Key of this market.
    :type market_info: MarketInfo
    """

    def __init__(self, market_info: MarketInfo, data: pd.DataFrame | None = None, data_path: str = "./data"):
        super().__init__(market_info, data, data_path)
        self.positions = {}
