from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from .._typing import TokenInfo, DemeterError, PoolBaseInfo, Position


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
        return "{} {}".format(self.balance, self.name)

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
            raise DemeterError(
                f"insufficient balance, balance is {self.balance}{self.name}, but sub amount is {amount}{self.name}")
        else:
            self.balance -= amount
        return self

    def amount_in_wei(self):
        return self.balance * Decimal(10 ** self.decimal)


@dataclass
class PositionVariable(object):
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


class PositionContainer:
    def __init__(self, pools: [PoolBaseInfo]):
        self.__positions: {PoolBaseInfo, dict[Position:PositionVariable]} = {}
        for pool in pools:
            self.__positions[pool] = {}

    def get(self, pool: PoolBaseInfo, position: Position):
        return self.__positions[pool][position]

    def set(self, pool: PoolBaseInfo, position: Position, value: PositionVariable):
        self.__positions[pool][position] = value

    def get_by_pool(self, pool: PoolBaseInfo):
        return self.__positions[pool]

    def remove(self, pool: PoolBaseInfo, position: Position):
        del self.__positions[pool][position]

    def is_empty(self):
        pos_sum = 0
        for pool_pos, item in self.__positions:
            pos_sum += len(item)
        return pos_sum == 0

    def __str__(self):
        value = "PositionContainer: \n"
        for index, pool in enumerate(self.__positions):
            value += "pool {}, {}: (".format(index, pool)
            for pos_index, position in enumerate(self.__positions[pool]):
                value += "{}: {}".format(position, self.__positions[pool][position])
            value += ")\n"
