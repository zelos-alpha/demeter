from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from .._typing import TokenInfo, ZelosError


class PoolBaseInfo(object):
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
                raise ZelosError("fee should be 0.05 or 0.3 or 1")
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
        return self.name

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

    def sub(self, amount=Decimal(0)):
        """
        subtract amount from balance. if balance is not enough, an error will be raised.

        :param amount: amount to subtract
        :type amount: Decimal
        :return:
        :rtype:
        """
        base = self.balance if self.balance != Decimal(0) else Decimal(amount)

        if base == Decimal(0):  # amount and balance is both 0
            return self
        # if difference between amount and balance is below 0.01%, will deduct all the balance
        # That's because, the amount calculated by v3_core, has some acceptable error.
        if abs((self.balance - amount) / base) < 0.00001:
            self.balance = Decimal(0)
        elif self.balance - amount < Decimal(0):
            raise ZelosError(
                f"insufficient balance, balance is {self.balance}{self.name}, but sub amount is {amount}{self.name}")
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
    current status of a pool, runners can notify current status to broker by filling this entity
    """
    timestamp: datetime
    current_tick: int
    current_liquidity: Decimal
    in_amount0: Decimal
    in_amount1: Decimal
    price: Decimal
