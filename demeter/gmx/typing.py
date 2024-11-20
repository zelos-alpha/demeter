from dataclasses import dataclass
from .._typing import MarketDescription, UnitDecimal
from ..broker import MarketBalance, BaseAction, ActionTypeEnum
from decimal import Decimal


@dataclass
class GmxDescription(MarketDescription):
    pass


@dataclass
class TokenInfo:
    """
    Identity for a token, will be used as key for token dict.

    :param name: token symbol, will be set as unit of a token value, e.g. usdc
    :type name: str
    :param decimal: decimal of this token, e.g. 6
    :type decimal: int
    :param address: Address of token, for aave market, this attribute has to be filled to load data.
    :type decimal: str
    """

    name: str
    decimal: int
    address: str

    def __init__(self, name: str, decimal: int, address: str = ""):
        self.name = name.upper()
        self.decimal = decimal
        self.address = address.lower()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, TokenInfo):
            return self.name == other.name
        else:
            return False

    def __hash__(self):
        return self.name.__hash__()


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
