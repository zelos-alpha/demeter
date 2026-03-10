from PMath import PMath


class PaymentLib:
    @staticmethod
    def calc_floating_fee(abs_size: int, fee_rate: int, time_to_mat: int) -> int:
        """
        Calculate floating fee.
        Formula: (absSize * feeRate * timeToMat) / ONE_MUL_YEAR (rounded up)
        """
        # Using raw_div_up for ceiling division
        numerator = abs_size * fee_rate * time_to_mat
        return PaymentLib._raw_div_up(numerator, PMath.ONE_MUL_YEAR)

    @staticmethod
    def calc_settlement(signed_size: int, last_findex: FIndex, current_findex: FIndex) -> PayFee:  # todo
        """
        Calculate settlement based on size and FIndex changes.
        """
        if last_findex == current_findex:
            return PayFeeLib.ZERO

        # Calculate payment and fees
        delta_floating = FIndexLib.floating_index(current_findex) - FIndexLib.floating_index(last_findex)
        delta_fee = FIndexLib.fee_index(current_findex) - FIndexLib.fee_index(last_findex)

        # Payment: signedSize * deltaFloating (mulFloor)
        payment = PMath.mul_floor(signed_size, delta_floating)

        # Fees: abs(signedSize) * deltaFee (mulUp)
        fees = PMath.mul_up(abs(signed_size), delta_fee)

        return PayFeeLib.from_values(payment, fees)

    @staticmethod
    def calc_upfront_fixed_cost(cost: int, time_to_mat: int) -> int:
        """
        Calculate upfront fixed cost.
        Formula: (cost * timeToMat) / ONE_YEAR (rounded up)
        """
        numerator = cost * time_to_mat
        return PaymentLib._raw_div_up(numerator, PMath.IONE_YEAR)

    @staticmethod
    def to_upfront_fixed_cost(trade_signed_cost: int, time_to_mat: int) -> int:
        """Calculate upfront fixed cost from trade's signed cost."""
        return PaymentLib.calc_upfront_fixed_cost(trade_signed_cost, time_to_mat)

    @staticmethod
    def calc_position_value(signed_size: int, mark_rate: int, time_to_mat: int) -> int:
        """
        Calculate position value.
        Formula: (signedSize * markRate * timeToMat) / ONE_MUL_YEAR (rounded down)
        """
        numerator = signed_size * mark_rate * time_to_mat
        return PaymentLib._raw_div_floor(numerator, PMath.IONE_MUL_YEAR)

    @staticmethod
    def calc_new_fee_index(old_fee_index: int, fee_rate: int, time_passed: int) -> int:
        """
        Calculate new fee index.
        Formula: oldFeeIndex + calcFloatingFee(ONE, feeRate, timePassed)
        """
        additional_fee = PaymentLib.calc_floating_fee(PMath.ONE, fee_rate, time_passed)
        return old_fee_index + additional_fee

    @staticmethod
    def _raw_div_up(x: int, d: int) -> int:
        """Raw division with ceiling (for positive numbers)."""
        if d == 0:
            raise ValueError("Division by zero")
        return x // d + (1 if x % d != 0 else 0)

    @staticmethod
    def _raw_div_floor(x: int, d: int) -> int:
        """Raw division with floor."""
        if d == 0:
            raise ValueError("Division by zero")
        return x // d