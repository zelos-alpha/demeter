from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from . import RowData
from .._typing import TokenInfo, DemeterError, UnitDecimal
from ..utils.application import get_formatted_str


@dataclass
class UniLPData(RowData):
    netAmount0: int = None
    netAmount1: int = None
    closeTick: int = None
    openTick: int = None
    lowestTick: int = None
    highestTick: int = None
    inAmount0: int = None
    inAmount1: int = None
    currentLiquidity: Decimal = None
    open: Decimal = None
    price: Decimal = None
    low: Decimal = None
    high: Decimal = None
    volume0: Decimal = None
    volume1: Decimal = None


class PoolInfo(object):
    """
    pool information, corresponding with definition in pool contract.

    :param token0: First token in  pool contract.
    :type token0:  TokenInfo
    :param token1: Second token in  pool contract.
    :type token1: TokenInfo
    :param fee: fee rate of this pool, should be among [0.05, 0.3, 1]
    :type fee: float
    :param base_token: which token will be considered as base token. eg: to a token pair of USDT/BTC, if you want price unit to be like 10000 usdt/btc, you should set usdt as base token, otherwise if price unit is 0.00001 btc/usdt, you should set btc as base token
    :type base_token: TokenInfo
    """

    def __init__(self, token0: TokenInfo, token1: TokenInfo, fee: float, base_token):
        self.token0 = token0
        self.token1 = token1
        self.is_token0_base = (base_token == token0)
        self.base_token = base_token
        fee = str(fee)  # keep precision
        match fee:
            case "0.05":
                self.tickSpacing = 10
            case "0.3":
                self.tickSpacing = 60
            case "1":
                self.tickSpacing = 200
            case _:
                raise DemeterError("fee should be 0.05 or 0.3 or 1")
        self.fee = Decimal(fee) * Decimal(10000)
        self.fee_rate = Decimal(fee) / Decimal(100)

    def __str__(self):
        """
        get string
        :return:
        :rtype:
        """
        return "PoolBaseInfo(Token0: {},".format(self.token0) + \
            "Token1: {},".format(self.token1) + \
            "fee: {},".format(self.fee_rate * Decimal(100)) + \
            "base token: {})".format(self.token0.name if self.is_token0_base else self.token1.name)


@dataclass
class DepositBalance:
    """
    current status of broker

    :param timestamp: timestamp
    :type timestamp: datetime
    :param base_uncollected: base token uncollect fee in all the positions.
    :type base_uncollected: UnitDecimal
    :param quote_uncollected: quote token uncollect fee in all the positions.
    :type quote_uncollected: UnitDecimal
    :param base_in_position: base token amount deposited in positions, calculated according to current price
    :type base_in_position: UnitDecimal
    :param quote_in_position: quote token amount deposited in positions, calculated according to current price
    :type quote_in_position: UnitDecimal
    :param pool_net_value: 按照池子base/quote关系的净值. 不是broker层面的(which 通常是对u的).
    :type pool_net_value: UnitDecimal
    :param price: current price
    :type price: UnitDecimal

    """
    timestamp: datetime
    base_uncollected: UnitDecimal
    quote_uncollected: UnitDecimal
    base_in_position: UnitDecimal
    quote_in_position: UnitDecimal
    pool_net_value: UnitDecimal
    price: UnitDecimal

    def get_output_str(self) -> str:
        """
        get colored and formatted string to output in console
        :return: formatted string
        :rtype: str
        """
        return get_formatted_str({
            "total capital": f"{self.pool_net_value.to_str()}",
            "uncollect fee": f"{self.base_uncollected.to_str()},{self.quote_uncollected.to_str()}",
            "in position amount": f"{self.base_in_position.to_str()},{self.quote_in_position.to_str()}"
        })

    def to_array(self):
        return [
            self.base_uncollected,
            self.quote_uncollected,
            self.base_in_position,
            self.quote_in_position,
            self.pool_net_value,
            self.price
        ]


@DeprecationWarning
class BrokerAsset(object):
    """
    Wallet of broker, manage balance of an asset.
    It will prevent excess usage on asset.
    """

    def __init__(self, token: TokenInfo, init_amount=Decimal(0)):
        self.token_info = token
        self.name = token.name
        self.decimal = token.decimal
        self.balance = init_amount

    def __str__(self):
        return f"{self.balance} {self.name}"

    def add(self, amount=Decimal(0)):
        """
        add amount to balance
        :param amount: amount to add
        :type amount: Decimal
        :return: entity itself
        :rtype: BrokerAsset
        """
        self.balance += amount
        return self

    def sub(self, amount=Decimal(0), allow_negative_balance=False):
        """
        subtract amount from balance. if balance is not enough, an error will be raised.

        :param amount: amount to subtract
        :type amount: Decimal
        :param allow_negative_balance: allow balance is negative
        :type allow_negative_balance: bool
        :return:
        :rtype:
        """
        base = self.balance if self.balance != Decimal(0) else Decimal(amount)

        if base == Decimal(0):  # amount and balance is both 0
            return self
        if allow_negative_balance:
            self.balance -= amount
        else:
            # if difference between amount and balance is below 0.01%, will deduct all the balance
            # That's because, the amount calculated by v3_core, has some acceptable error.
            if abs((self.balance - amount) / base) < 0.00001:
                self.balance = Decimal(0)
            elif self.balance - amount < Decimal(0):
                raise DemeterError(f"Insufficient balance, balance is {self.balance}{self.name}, "
                                   f"but sub amount is {amount}{self.name}")
            else:
                self.balance -= amount

        return self

    def amount_in_wei(self):
        return self.balance * Decimal(10 ** self.decimal)


@dataclass
class Position(object):
    """
    variables for position
    """

    pending_amount0: Decimal
    pending_amount1: Decimal
    liquidity: int


class PoolStatus(NamedTuple):
    """
    current status of a pool, actuators can notify current status to broker by filling this entity
    """
    timestamp: datetime
    current_tick: int
    current_liquidity: Decimal
    in_amount0: Decimal
    in_amount1: Decimal
    price: Decimal
