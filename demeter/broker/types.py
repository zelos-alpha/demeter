from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple
from datetime import datetime
from .._typing import TokenInfo, ZelosError


class PoolBaseInfo(object):
    def __init__(self, token0: TokenInfo, token1: TokenInfo, fee: float, base_token):
        self.token0 = token0
        self.token1 = token1
        self.is_token0_base = (base_token == token0)
        self.base_token = base_token
        fee = str(fee)  # 防止精度问题
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
        return "PoolBaseInfo(Token0: {},".format(self.token0) + \
               "Token1: {},".format(self.token1) + \
               "fee: {},".format(self.fee_rate * Decimal(100)) + \
               "base token: {})".format(self.token0.name if self.is_token0_base else self.token1.name)


class BrokerAsset(object):  # 类型使用decimal.Decimal防止出现python float精度问题
    def __init__(self, token: TokenInfo, init_amount=Decimal(0)):
        self.token_info = token
        self.name = token.name
        self.decimal = token.decimal
        self.balance = init_amount

    def __str__(self):
        return self.name

    def add(self, amount=Decimal(0)):
        self.balance += amount
        return self

    def sub(self, amount=Decimal(0)):
        base = self.balance if self.balance != Decimal(0) else amount

        if base == Decimal(0):  # amount and balance is both 0
            return self
        # 如果扣减金额和余额相差, 小于0.01%, 扣减所有余额
        # 这是因为, core所计算出的扣减金额. 实际上有一些误差. 在一定范围内可以接受这个误差
        # 具体来说, 在"花光余额"的场景下. 会造成余额不足的问题
        if abs((self.balance - amount) / base) < 0.00001:
            self.balance = Decimal(0)
        elif self.balance - amount < Decimal(0):
            raise ZelosError("insufficient balance")
        else:
            self.balance -= amount
        return self

    def amount_in_wei(self):
        return self.balance * Decimal(10 ** self.decimal)


@dataclass
class Position(object):
    def __init__(self):
        self.uncollected_fee_token0: Decimal = Decimal(0)
        self.uncollected_fee_token1: Decimal = Decimal(0)


class BarData(NamedTuple):
    timestamp: datetime
    current_tick: int
    current_liquidity: Decimal
    in_amount0: Decimal
    in_amount1: Decimal
    price: Decimal
