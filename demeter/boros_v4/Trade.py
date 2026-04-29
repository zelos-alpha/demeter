from dataclasses import dataclass
from decimal import Decimal
from ._typing import Side
from .PMath import PMath

@dataclass
class Trade:
    signed_size: Decimal = Decimal('0')
    signed_cost: Decimal = Decimal('0')

    @staticmethod
    def ZERO() -> 'Trade':
        return Trade(Decimal('0'), Decimal('0'))

    @staticmethod
    def from_(signed_size: Decimal, signed_cost: Decimal) -> 'Trade':
        return Trade(signed_size, signed_cost)

    def side(self) -> Side:
        return Side.LONG if self.signed_size > 0 else Side.SHORT

    def abs_size(self) -> Decimal:
        return PMath.abs(self.signed_size)

    def abs_cost(self) -> Decimal:
        return PMath.abs(self.signed_cost)

    def __add__(self, other: 'Trade') -> 'Trade':
        return Trade(self.signed_size + other.signed_size, self.signed_cost + other.signed_cost)

    def opposite(self) -> 'Trade':
        return Trade(-self.signed_size, -self.signed_cost)

    def is_zero(self) -> bool:
        return True if self.signed_size + self.signed_cost == Decimal(0) else False

    def from_size_and_rate(self, signed_size: Decimal, rate: Decimal) -> 'Trade':
        return Trade(signed_size, signed_size * rate)  # todo

    @staticmethod
    def from3(side: Side, size: Decimal, rate: Decimal) -> 'Trade':
        # size uint256
        cost = size * rate  # todo
        if side == Side.LONG:
            return Trade(size, cost)
        else:
            return Trade(-size, -cost)

@dataclass
class Fill:
    signed_size: Decimal = Decimal('0')
    signed_cost: Decimal = Decimal('0')

    @staticmethod
    def from3(side: Side, size: Decimal, rate: Decimal) -> 'Fill':
        trade = Trade.from3(side, size, rate)
        return Fill(trade.signed_size, trade.signed_cost)

    def to_trade(self) -> Trade:
        return Trade(self.signed_size, self.signed_cost)

    def is_zero(self) -> bool:
        return True if self.signed_size + self.signed_cost == Decimal(0) else False

    def abs_size(self) -> Decimal:
        return PMath.abs(self.signed_size)

    def abs_cost(self) -> Decimal:
        return PMath.abs(self.signed_cost)
