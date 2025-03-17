from dataclasses import dataclass
from typing import Union

import pandas as pd

from demeter import TokenInfo, MarketStatus
from demeter._typing import MarketDescription


@dataclass
class GmxV2Pool(object):
    long_token: TokenInfo
    short_token: TokenInfo
    index_token: TokenInfo


@dataclass
class GmxV2Description(MarketDescription):
    amount: float

@dataclass
class GmxV2PoolStatus:
     longAmount:float
     shortAmount:float
     virtualSwapInventoryLong:float
     virtualSwapInventoryShort:float
     poolValue:float
     marketTokensSupply:float
     longPrice:float
     shortPrice:float
     indexPrice:float


@dataclass
class GmxV2MarketStatus(MarketStatus):
    data: Union[pd.Series, GmxV2PoolStatus]