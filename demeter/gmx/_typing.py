from dataclasses import dataclass
from .._typing import MarketDescription
from ..broker import MarketBalance, BaseAction, ActionTypeEnum
from decimal import Decimal

PRICE_PRECISION = 10**30


@dataclass
class GmxDescription(MarketDescription):
    pass


@dataclass
class GmxBalance(MarketBalance):
    glp: Decimal
    # esGmx: Decimal  # not consider
    reward: Decimal  # price must with platform coin, arbitrum->weth, avalanche->avax


@dataclass
class BuyGlpAction(BaseAction):
    token: str
    token_amount: Decimal
    mint_amount: Decimal

    def set_type(self):
        self.action_type = ActionTypeEnum.gmx_buy_glp


@dataclass
class SellGlpAction(BaseAction):
    token: str
    glp_amount: Decimal
    token_out: Decimal

    def set_type(self):
        self.action_type = ActionTypeEnum.gmx_sell_glp
