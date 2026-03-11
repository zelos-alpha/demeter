from dataclasses import dataclass
from decimal import Decimal

from .PMath import PMath


@dataclass(frozen=True)
class FIndex:
    floating_index: int = 0
    fee_index: int = 0


@dataclass(frozen=True)
class PayFee:
    payment: int = 0
    fees: int = 0

    @property
    def total(self) -> int:
        return self.payment - self.fees

    def __add__(self, other: "PayFee") -> "PayFee":
        return PayFee(payment=self.payment + other.payment, fees=self.fees + other.fees)


@dataclass(frozen=True)
class SettlementBreakdown:
    settlement: PayFee = PayFee()
    mark_to_maturity_value: int = 0
    entry_fixed_cost: int = 0
    entry_opening_fee_cost: int = 0

    @property
    def total(self) -> int:
        return self.settlement.total + self.mark_to_maturity_value - self.entry_fixed_cost - self.entry_opening_fee_cost


class PaymentLib:
    @staticmethod
    def wad_to_decimal(value: int) -> Decimal:
        return Decimal(value) / Decimal(PMath.ONE)

    @staticmethod
    def decimal_to_wad(value: Decimal | int | float | str) -> int:
        return int((Decimal(value) * Decimal(PMath.ONE)).to_integral_value())

    @staticmethod
    def calc_floating_fee(abs_size: int, fee_rate: int, time_to_mat: int) -> int:
        numerator = abs_size * fee_rate * time_to_mat
        return PMath.raw_div_up(numerator, PMath.ONE_MUL_YEAR)

    @staticmethod
    def calc_settlement(signed_size: int, last_findex: FIndex, current_findex: FIndex) -> PayFee:
        if last_findex == current_findex:
            return PayFee()

        delta_floating = current_findex.floating_index - last_findex.floating_index
        delta_fee = current_findex.fee_index - last_findex.fee_index
        payment = PMath.mul_floor(signed_size, delta_floating)
        if delta_fee >= 0:
            fees = PMath.mul_up(abs(signed_size), delta_fee)
        else:
            fees = -PMath.mul_floor(abs(signed_size), -delta_fee)
        return PayFee(payment=payment, fees=fees)

    @staticmethod
    def calc_upfront_fixed_cost(cost: int, time_to_mat: int) -> int:
        numerator = cost * time_to_mat
        return PMath.raw_div_up(numerator, PMath.IONE_YEAR)

    @staticmethod
    def to_upfront_fixed_cost(trade_signed_cost: int, time_to_mat: int) -> int:
        return PaymentLib.calc_upfront_fixed_cost(trade_signed_cost, time_to_mat)

    @staticmethod
    def calc_position_value(signed_size: int, mark_rate: int, time_to_mat: int) -> int:
        numerator = signed_size * mark_rate * time_to_mat
        return PMath.raw_div_floor(numerator, PMath.IONE_MUL_YEAR)

    @staticmethod
    def calc_entry_fixed_cost(signed_size: int, fixed_rate: int, entry_time_to_mat: int) -> int:
        signed_cost = PMath.mul_floor(signed_size, fixed_rate)
        return PaymentLib.calc_upfront_fixed_cost(signed_cost, entry_time_to_mat)

    @staticmethod
    def calc_present_value(
        signed_size: int,
        entry_fixed_rate: int,
        entry_findex: FIndex,
        current_findex: FIndex,
        current_mark_rate: int,
        entry_time_to_mat: int,
        current_time_to_mat: int,
        entry_opening_fee_cost: int = 0,
    ) -> SettlementBreakdown:
        settlement = PaymentLib.calc_settlement(signed_size, entry_findex, current_findex)
        mark_to_maturity_value = PaymentLib.calc_position_value(signed_size, current_mark_rate, current_time_to_mat)
        entry_fixed_cost = PaymentLib.calc_entry_fixed_cost(signed_size, entry_fixed_rate, entry_time_to_mat)
        return SettlementBreakdown(
            settlement=settlement,
            mark_to_maturity_value=mark_to_maturity_value,
            entry_fixed_cost=entry_fixed_cost,
            entry_opening_fee_cost=entry_opening_fee_cost,
        )

    @staticmethod
    def calc_new_fee_index(old_fee_index: int, fee_rate: int, time_passed: int) -> int:
        additional_fee = PaymentLib.calc_floating_fee(PMath.ONE, fee_rate, time_passed)
        return old_fee_index + additional_fee
