from dataclasses import dataclass
from decimal import Decimal
from typing import Union

import pandas as pd

from .. import TokenInfo, MarketStatus
from .._typing import MarketDescription
from ..broker import MarketBalance
from .gmx_v2 import GmxV2PoolStatus


@dataclass
class GmxV2Balance(MarketBalance):
    gm_amount: Decimal
    long_amount: Decimal
    short_amount: Decimal


@dataclass
class GmxV2Pool(object):
    long_token: TokenInfo
    short_token: TokenInfo
    index_token: TokenInfo


@dataclass
class GmxV2Description(MarketDescription):
    amount: float


@dataclass
class GmxV2MarketStatus(MarketStatus):
    data: Union[pd.Series, GmxV2PoolStatus]
