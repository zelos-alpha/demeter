from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import List

from demeter import TokenInfo, AccountStatus, BaseAction, MarketInfo
from demeter._typing import MarketDescription, DemeterLog


@dataclass
class BackTestDescription:
    strategy_name: str
    quote_token: TokenInfo
    init_status: AccountStatus
    assets: List[TokenInfo]
    markets: List[MarketDescription]
    actions: List[BaseAction]
    backtest_start: datetime
    backtest_end: datetime
    backtest_duration: float
    logs: List[DemeterLog] = field(default_factory=list)


@dataclass
class Position:
    key: any
    market: MarketInfo
    start: datetime
    end: datetime | None
    amount: Decimal


@dataclass
class OptionPosition(Position):
    token: str
    strike_price: int
    expiry_time: datetime
    type: str  # call put


@dataclass
class LpPosition(Position):
    base_token: str
    quote_token: str
    lower_price: Decimal
    upper_price: Decimal
