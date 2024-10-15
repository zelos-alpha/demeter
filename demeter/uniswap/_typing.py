import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, NamedTuple, Union

from .._typing import TokenInfo, UnitDecimal, MarketDescription
from ..broker import BaseAction, ActionTypeEnum, MarketBalance, MarketStatus
from ..utils import console_text
from ..utils import get_formatted_from_dict
from ..utils.console_text import get_action_str, ForColorEnum


class PositionInfo(NamedTuple):
    """
    get_position information, including tick range and liquidity. It contains immutable properties of a get_position, and used as a key for get_position dict

    :param lower_tick: lower tick
    :type lower_tick: int
    :param upper_tick: upper tick
    :type upper_tick: int

    """

    lower_tick: int
    """lower tick"""
    upper_tick: int
    """upper tick"""

    def __str__(self):
        return f"""tick:{self.lower_tick},{self.upper_tick}"""

@dataclass
class UniDescription(MarketDescription):
    """
    A brief description for uniswap market status.
    """

    token0: TokenInfo
    """token0"""
    token1: TokenInfo
    """token1"""
    quote_token: TokenInfo
    """quote token"""
    base_token: TokenInfo
    """base token"""
    fee_rate: Decimal
    """fee rate"""


class UniV3Pool(object):
    """
    pool information, corresponding with definition in pool contract.

    :param token0: First token in  pool contract.
    :type token0:  TokenInfo
    :param token1: Second token in  pool contract.
    :type token1: TokenInfo
    :param fee: fee rate of this pool, should be among [0.05%, 0.3%, 1%]
    :type fee: float, 0.05
    :param quote_token: which token will be considered as base token. e.g. to a token pair of USDT/BTC, if you want price unit to be like 10000 usdt/btc, you should set usdt as base token, otherwise if price unit is 0.00001 btc/usdt, you should set btc as base token
    :type quote_token: TokenInfo
    """

    def __init__(self, token0: TokenInfo, token1: TokenInfo, fee: float, quote_token: TokenInfo):
        fee = Decimal(str(fee))
        self.token0 = token0
        self.token1 = token1
        self.is_token0_quote = quote_token == token0
        self.quote_token = quote_token
        self.base_token = token1 if self.is_token0_quote else token0
        self.tick_spacing = int(fee * 200)
        self.fee: Decimal = fee * Decimal(10000)
        self.fee_rate: Decimal = Decimal(fee) / Decimal(100)

    def __str__(self):
        return (
            "PoolBaseInfo(Token0: {},".format(self.token0)
            + "Token1: {},".format(self.token1)
            + "fee: {}%,".format(self.fee_rate * Decimal(100))
            + "base token: {})".format(self.token0.name if self.is_token0_quote else self.token1.name)
        )

    def __repr__(self):
        return self.__str__()


@dataclass
class UniLpBalance(MarketBalance):
    """
    current balances of quote and base token in uniswap market

    :param base_uncollected: base token uncollect fee in all the positions.
    :type base_uncollected: UnitDecimal
    :param quote_uncollected: quote token uncollect fee in all the positions.
    :type quote_uncollected: UnitDecimal
    :param base_in_position: base token amount deposited in positions, calculated according to current price
    :type base_in_position: UnitDecimal
    :param quote_in_position: quote token amount deposited in positions, calculated according to current price
    :type quote_in_position: UnitDecimal
    :param position_count: count of positions
    :type position_count: int

    """

    base_uncollected: UnitDecimal
    """base token uncollect fee in all the positions."""
    quote_uncollected: UnitDecimal
    """quote token uncollect fee in all the positions."""
    base_in_position: UnitDecimal
    """base token amount deposited in positions, calculated according to current price"""
    quote_in_position: UnitDecimal
    """quote token amount deposited in positions, calculated according to current price"""
    position_count: int
    """count of positions"""

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """
        return get_formatted_from_dict(
            {
                "total capital": self.net_value.to_str(),
                "uncollect fee": f"{self.base_uncollected.to_str()},{self.quote_uncollected.to_str()}",
                "in get_position amount": f"{self.base_in_position.to_str()},{self.quote_in_position.to_str()}",
                "get_position count": self.position_count,
            }
        )

    def to_array(self):
        """
        Join attributes to an array
        """
        return [
            self.net_value,
            self.base_uncollected,
            self.quote_uncollected,
            self.base_in_position,
            self.quote_in_position,
            self.position_count,
        ]


# @DeprecationWarning
# class BrokerAsset(object):
#     """
#     Wallet of broker, manage balance of an asset.
#     It will prevent excess usage on asset.
#     """
#
#     def __init__(self, token: TokenInfo, init_amount=Decimal(0)):
#         self.token_info = token
#         self.name = token.name
#         self.decimal = token.decimal
#         self.balance = init_amount
#
#     def __str__(self):
#         return f"{self.balance} {self.name}"
#
#     def add(self, amount=Decimal(0)):
#         """
#         add amount to balance
#         :param amount: amount to add
#         :type amount: Decimal
#         :return: entity itself
#         :rtype: BrokerAsset
#         """
#         self.balance += amount
#         return self
#
#     def sub(self, amount=Decimal(0), allow_negative_balance=False):
#         """
#         subtract amount from balance. if balance is not enough, an error will be raised.
#
#         :param amount: amount to subtract
#         :type amount: Decimal
#         :param allow_negative_balance: allow balance is negative
#         :type allow_negative_balance: bool
#         :return:
#         :rtype:
#         """
#         base = self.balance if self.balance != Decimal(0) else Decimal(amount)
#
#         if base == Decimal(0):  # amount and balance is both 0
#             return self
#         if allow_negative_balance:
#             self.balance -= amount
#         else:
#             # if difference between amount and balance is below 0.01%, will deduct all the balance
#             # That's because, the amount calculated by v3_core, has some acceptable error.
#             if abs((self.balance - amount) / base) < 0.00001:
#                 self.balance = Decimal(0)
#             elif self.balance - amount < Decimal(0):
#                 raise DemeterError(f"Insufficient balance, balance is {self.balance}{self.name}, " f"but sub amount is {amount}{self.name}")
#             else:
#                 self.balance -= amount
#
#         return self
#
#     def amount_in_wei(self):
#         return self.balance * Decimal(10**self.decimal)


@dataclass
class Position(object):
    """
    keeps variables for get_position
    """

    pending_amount0: Decimal
    pending_amount1: Decimal
    liquidity: int
    lower_price: Decimal
    upper_price: Decimal
    transferred: bool = False  # this position(nft) has been transferred, so owner is not current user.


def position_dict_to_dataframe(positions: Dict[PositionInfo, Position]) -> pd.DataFrame:
    pos_dict = {
        "lower_tick": [],
        "upper_tick": [],
        "pending0": [],
        "pending1": [],
        "liquidity": [],
    }
    for k, v in positions.items():
        pos_dict["lower_tick"].append(k.lower_tick)
        pos_dict["upper_tick"].append(k.upper_tick)
        pos_dict["pending0"].append(console_text.format_value(v.pending_amount0))
        pos_dict["pending1"].append(console_text.format_value(v.pending_amount1))
        pos_dict["liquidity"].append(v.liquidity)
    return pd.DataFrame(pos_dict)


@dataclass
class UniV3PoolStatus:
    """
    current status of a pool, actuators can notify current status to broker by filling this entity
    """

    # required by market class
    price: Decimal
    """token price(price of quote token)"""
    currentLiquidity: int = None
    """total liquidity of this pool"""
    inAmount0: int = None
    """in amount of token 0 in this minute"""
    inAmount1: int = None
    """in amount of token 1 in this minute"""
    closeTick: int = None
    """last price tick of this minute"""

    # useless. just pass poperity to
    netAmount0: int = None
    """total amount of token 0"""
    netAmount1: int = None
    """total amount of token 1"""
    openTick: int = None
    """start tick in this minute"""
    lowestTick: int = None
    """lowest tick in this minute"""
    highestTick: int = None
    """highest tick in this minute"""
    open: Decimal = None
    """start price in this minute"""
    low: Decimal = None
    """lowest price in this minute"""
    high: Decimal = None
    """highest price in this minute"""
    volume0: Decimal = None
    """swap volumn of token 0"""
    volume1: Decimal = None
    """swap volumn of token 1"""


@dataclass
class UniswapMarketStatus(MarketStatus):
    """
    MarketStatus properties

    :param data: current pool status
    :type data: Union[pd.Series, UniV3PoolStatus]
    """

    data: Union[pd.Series, UniV3PoolStatus] = None


@dataclass
class UniLpBaseAction(BaseAction):
    """
    Parent class of broker actions,

    :param base_balance_after: after action balance of base token
    :type base_balance_after: UnitDecimal
    :param quote_balance_after: after action balance of quote token
    :type quote_balance_after: UnitDecimal
    """

    base_balance_after: UnitDecimal
    quote_balance_after: UnitDecimal

    def get_output_str(self):
        return str(self)


@dataclass
class AddLiquidityAction(UniLpBaseAction):
    """
    Add Liquidity

    :param base_amount_max: inputted base token amount, also the max amount to deposit
    :type base_amount_max: ActionTypeEnum
    :param quote_amount_max: inputted base token amount, also the max amount to deposit
    :type quote_amount_max: datetime
    :param lower_quote_price: lower price base on quote token.
    :type lower_quote_price: UnitDecimal
    :param upper_quote_price: upper price base on quote token.
    :type upper_quote_price: UnitDecimal
    :param base_amount_actual: actual used base token
    :type base_amount_actual: UnitDecimal
    :param quote_amount_actual: actual used quote token
    :type quote_amount_actual: UnitDecimal
    :param position: generated get_position
    :type position: PositionInfo
    :param liquidity: liquidity added
    :type liquidity: int
    """

    base_amount_max: UnitDecimal
    quote_amount_max: UnitDecimal
    lower_quote_price: UnitDecimal
    upper_quote_price: UnitDecimal
    base_amount_actual: UnitDecimal
    quote_amount_actual: UnitDecimal
    position: PositionInfo
    liquidity: int

    def set_type(self):
        self.action_type = ActionTypeEnum.uni_lp_add_liquidity

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """
        return get_action_str(
            self,
            ForColorEnum.red,
            {
                "max amount": f"{self.base_amount_max.to_str()},{self.quote_amount_max.to_str()}",
                "price": f"{self.lower_quote_price.to_str()},{self.upper_quote_price.to_str()}",
                "get_position": str(self.position),
                "liquidity": self.liquidity,
                "balance": f"{self.base_balance_after.to_str()}(-{self.base_amount_actual.to_str()}), {self.quote_balance_after.to_str()}(-{self.quote_amount_actual.to_str()})",
            },
        )


@dataclass
class CollectFeeAction(UniLpBaseAction):
    """
    collect fee

    :param position: get_position to operate
    :type position: PositionInfo
    :param base_amount: fee collected in base token
    :type base_amount: UnitDecimal
    :param quote_amount: fee collected in quote token
    :type quote_amount: UnitDecimal

    """

    position: PositionInfo
    base_amount: UnitDecimal
    quote_amount: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.uni_lp_collect

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """
        return get_action_str(
            self,
            ForColorEnum.yellow,
            {
                "get_position": str(self.position),
                "balance": f"{self.base_balance_after.to_str()}(+{self.base_amount.to_str()}), {self.quote_balance_after.to_str()}(+{self.quote_amount.to_str()})",
            },
        )


@dataclass
class RemoveLiquidityAction(UniLpBaseAction):
    """
    remove get_position

    :param position: get_position to operate
    :type position: PositionInfo
    :param base_amount: base token amount collected
    :type base_amount: UnitDecimal
    :param quote_amount: quote token amount collected
    :type quote_amount: UnitDecimal
    :param removed_liquidity: liquidity number has removed
    :type removed_liquidity: int
    :param remain_liquidity: liquidity number left in get_position
    :type remain_liquidity: int

    """

    position: PositionInfo
    base_amount: UnitDecimal
    quote_amount: UnitDecimal
    removed_liquidity: int
    remain_liquidity: int

    def set_type(self):
        self.action_type = ActionTypeEnum.uni_lp_remove_liquidity

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.green,
            {
                "get_position": str(self.position),
                "balance": f"{self.base_balance_after.to_str()}(+0), {self.quote_balance_after.to_str()}(+0)",
                "token_got": f"{self.base_amount.to_str()},{self.quote_amount.to_str()}",
                "removed liquidity": self.removed_liquidity,
                "remain liquidity": self.remain_liquidity,
            },
        )


@dataclass
class SwapAction(BaseAction):
    """
    buy token, swap from base token to quote token.

    :param amount: amount to buy(in quote token)
    :type amount: UnitDecimal
    :param price: price,
    :type price: UnitDecimal
    :param fee: fee paid (in base token)
    :type fee: UnitDecimal
    :param base_change: base token amount changed
    :type base_change: PositionInfo
    :param quote_change: quote token amount changed
    :type quote_change: UnitDecimal

    """

    amount: UnitDecimal
    price: UnitDecimal
    fee: UnitDecimal
    to_amount: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.uni_lp_swap

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """
        return get_action_str(
            self,
            ForColorEnum.cyan,
            {
                "price": self.price.to_str(),
                "fee": self.fee.to_str(),
                "amount": f"{self.amount.to_str()}->{self.to_amount.to_str()}",
            },
        )


@dataclass
class BuyAction(UniLpBaseAction):
    """
    buy token, swap from base token to quote token.

    :param amount: amount to buy(in quote token)
    :type amount: UnitDecimal
    :param price: price,
    :type price: UnitDecimal
    :param fee: fee paid (in base token)
    :type fee: UnitDecimal
    :param base_change: base token amount changed
    :type base_change: PositionInfo
    :param quote_change: quote token amount changed
    :type quote_change: UnitDecimal

    """

    amount: UnitDecimal
    price: UnitDecimal
    fee: UnitDecimal
    base_change: UnitDecimal
    quote_change: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.uni_lp_buy

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """
        return get_action_str(
            self,
            ForColorEnum.cyan,
            {
                "price": self.price.to_str(),
                "fee": self.fee.to_str(),
                "balance": f"{self.base_balance_after.to_str()}(-{self.base_change.to_str()}), {self.quote_balance_after.to_str()}(+{self.quote_change.to_str()})",
            },
        )


@dataclass
class SellAction(UniLpBaseAction):
    """
    sell token, swap from quote token to base token.

    :param amount: amount to sell(in quote token)
    :type amount: UnitDecimal
    :param price: price,
    :type price: UnitDecimal
    :param fee: fee paid (in quote token)
    :type fee: UnitDecimal
    :param base_change: base token amount changed
    :type base_change: PositionInfo
    :param quote_change: quote token amount changed
    :type quote_change: UnitDecimal

    """

    amount: UnitDecimal
    price: UnitDecimal
    fee: UnitDecimal
    base_change: UnitDecimal
    quote_change: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.uni_lp_sell

    def get_output_str(self):
        """
        get colored and formatted string to output in console

        :return: formatted string
        :rtype: str
        """

        return get_action_str(
            self,
            ForColorEnum.light_red,
            {
                "price": self.price.to_str(),
                "fee": self.fee.to_str(),
                "balance": f"{self.base_balance_after.to_str()}(+{self.base_change.to_str()}), {self.quote_balance_after.to_str()}(-{self.quote_change.to_str()})",
            },
        )
