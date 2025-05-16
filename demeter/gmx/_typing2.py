from dataclasses import dataclass
from decimal import Decimal
from typing import Union

import pandas as pd

from .. import TokenInfo, MarketStatus, BaseAction, ActionTypeEnum
from .._typing import MarketDescription, UnitDecimal
from ..broker import MarketBalance
from .gmx_v2 import GmxV2PoolStatus
from ..utils.console_text import get_action_str, ForColorEnum


@dataclass
class GmxV2Balance(MarketBalance):
    gm_amount: Decimal
    long_amount: Decimal
    short_amount: Decimal
    realized_profit: Decimal
    pending_pnl: Decimal


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


@dataclass
class Gmx2WithdrawAction(BaseAction):
    gm_amount: UnitDecimal
    gm_usd: UnitDecimal
    long_amount: UnitDecimal
    short_amount: UnitDecimal
    withdraw_usd: UnitDecimal
    long_fee: UnitDecimal
    short_fee: UnitDecimal
    fee_usd: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.gmx2_withdraw

    def get_output_str(self):
        return get_action_str(
            self,
            ForColorEnum.light_red,
            {
                "gm_amount": self.gm_amount.to_str(),
                "gm_usd": self.gm_usd.to_str(),
                "long_amount": self.long_amount.to_str(),
                "short_amount": self.short_amount.to_str(),
                "withdraw_usd": self.withdraw_usd.to_str(),
                "fee_usd": self.fee_usd.to_str(),
            },
        )


@dataclass
class Gmx2DepositAction(BaseAction):
    long_amount: UnitDecimal
    short_amount: UnitDecimal
    deposit_usd: UnitDecimal
    gm_amount: UnitDecimal
    gm_usd: UnitDecimal
    long_fee: UnitDecimal
    short_fee: UnitDecimal
    fee_usd: UnitDecimal
    price_impact_usd: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.gmx2_deposit

    def get_output_str(self):

        return get_action_str(
            self,
            ForColorEnum.light_green,
            {
                "long_amount": self.long_amount.to_str(),
                "short_amount": self.short_amount.to_str(),
                "deposit_usd": self.deposit_usd.to_str(),
                "gm_amount": self.gm_amount.to_str(),
                "gm_usd": self.gm_usd.to_str(),
                "fee_usd": self.fee_usd.to_str(),
                "price_impact_usd": self.price_impact_usd.to_str(),
            },
        )
