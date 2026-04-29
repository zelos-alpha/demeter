"""
Test cases for PMath module in boros_v4.
Tests for all functions in PMath.py
"""

import unittest
from decimal import Decimal
from demeter.boros_v4.PMath import PMath, PMathOverflowError


class TestPMathConstants(unittest.TestCase):
    """Test PMath constants."""
    
    def test_one_constant(self):
        """Test ONE constant equals 10^18."""
        self.assertEqual(PMath.ONE, 10**18)
    
    def test_ione_constant(self):
        """Test IONE constant equals 10^18."""
        self.assertEqual(PMath.IONE, 10**18)
    
    def test_one_year_constant(self):
        """Test ONE_YEAR constant equals 365 days in seconds."""
        self.assertEqual(PMath.ONE_YEAR, 365 * 24 * 60 * 60)
    
    def test_ione_year_constant(self):
        """Test IONE_YEAR constant equals 365 days in seconds."""
        self.assertEqual(PMath.IONE_YEAR, 365 * 24 * 60 * 60)
    
    def test_one_mul_year_constant(self):
        """Test ONE_MUL_YEAR constant."""
        self.assertEqual(PMath.ONE_MUL_YEAR, 10**18 * 365 * 24 * 60 * 60)
    
    def test_ione_mul_year_constant(self):
        """Test IONE_MUL_YEAR constant."""
        self.assertEqual(PMath.IONE_MUL_YEAR, 10**18 * 365 * 24 * 60 * 60)


class TestPMathIncDec(unittest.TestCase):
    """Test inc and dec functions."""
    
    def test_inc_positive(self):
        """Test inc with positive number."""
        self.assertEqual(PMath.inc(5), 6)
    
    def test_inc_zero(self):
        """Test inc with zero."""
        self.assertEqual(PMath.inc(0), 1)
    
    def test_inc_large_number(self):
        """Test inc with large number."""
        self.assertEqual(PMath.inc(10**18), 10**18 + 1)
    
    def test_dec_positive(self):
        """Test dec with positive number."""
        self.assertEqual(PMath.dec(5), 4)
    
    def test_dec_one(self):
        """Test dec with one."""
        self.assertEqual(PMath.dec(1), 0)
    
    def test_dec_zero(self):
        """Test dec with zero."""
        self.assertEqual(PMath.dec(0), -1)


class TestPMathMul(unittest.TestCase):
    """Test multiplication functions."""
    
    def test_mul_up_basic(self):
        """Test mul_up with basic values."""
        # 2 * 3 = 6, with WAD scaling: 6 * 10^18 / 10^18 = 6
        result = PMath.mul_up(2 * PMath.ONE, 3 * PMath.ONE)
        self.assertEqual(result, 6 * PMath.ONE)
    
    def test_mul_up_rounds_up(self):
        """Test mul_up rounds up correctly."""
        # (1 * ONE) * (1 * ONE) / ONE = ONE, exact division
        result = PMath.mul_up(1 * PMath.ONE, 1 * PMath.ONE)
        self.assertEqual(result, 1 * PMath.ONE)
    
    def test_mul_up_with_remainder(self):
        """Test mul_up with remainder."""
        # (10^18 + 1) * 10^18 / 10^18 = 10^18 + 1, but with extra it rounds up to next integer
        result = PMath.mul_up(10**18 + 1, 10**18)
        self.assertEqual(result, 10**18 + 1)
    
    def test_mul_up_zero_y(self):
        """Test mul_up when y is zero."""
        result = PMath.mul_up(5 * PMath.ONE, 0)
        self.assertEqual(result, 0)
    
    def test_mul_up_overflow(self):
        """Test mul_up raises overflow error."""
        with self.assertRaises(PMathOverflowError):
            PMath.mul_up(2**255, 2)
    
    def test_mul_down_basic(self):
        """Test mul_down with basic values."""
        result = PMath.mul_down(2 * PMath.ONE, 3 * PMath.ONE)
        self.assertEqual(result, 6 * PMath.ONE)
    
    def test_mul_down_zero_x(self):
        """Test mul_down when x is zero."""
        result = PMath.mul_down(0, 5 * PMath.ONE)
        self.assertEqual(result, 0)
    
    def test_mul_down_zero_y(self):
        """Test mul_down when y is zero."""
        result = PMath.mul_down(5 * PMath.ONE, 0)
        self.assertEqual(result, 0)
    
    def test_mul_down_rounds_down(self):
        """Test mul_down rounds down correctly."""
        # mul_down(x, y) = (x * y) / ONE
        # (10^18 * 3 * 10^18) / 10^18 = 3 * 10^18
        result = PMath.mul_down(10**18, 3 * 10**18)
        self.assertEqual(result, 3 * PMath.ONE)
    
    def test_mul_down_int_basic(self):
        """Test mul_down_int with basic values."""
        result = PMath.mul_down_int(2 * PMath.IONE, 3 * PMath.IONE)
        self.assertEqual(result, 6 * PMath.IONE)
    
    def test_mul_down_int_negative(self):
        """Test mul_down_int with negative values."""
        result = PMath.mul_down_int(-2 * PMath.IONE, 3 * PMath.IONE)
        self.assertEqual(result, -6 * PMath.IONE)
    
    def test_mul_down_int_zero(self):
        """Test mul_down_int with zero."""
        result = PMath.mul_down_int(0, 5 * PMath.IONE)
        self.assertEqual(result, 0)
    
    def test_mul_down_int_overflow(self):
        """Test mul_down_int raises overflow error."""
        with self.assertRaises(PMathOverflowError):
            PMath.mul_down_int(-1, -2**255)


class TestPMathDiv(unittest.TestCase):
    """Test division functions."""
    
    def test_div_down_basic(self):
        """Test div_down with basic values."""
        # div_down(x, y) = (x * ONE) / y
        # 6 * ONE / 3 = 2 * ONE * ONE
        result = PMath.div_down(6 * PMath.ONE, 3)
        self.assertEqual(result, 2 * PMath.ONE * PMath.ONE)
    
    def test_div_down_zero_y(self):
        """Test div_down raises error when y is zero."""
        with self.assertRaises(PMathOverflowError):
            PMath.div_down(5 * PMath.ONE, 0)
    
    def test_div_down_int_basic(self):
        """Test div_down_int with basic values."""
        # div_down_int(x, y) = (x * IONE) / y
        # 6 * IONE / 3 = 2 * IONE * IONE
        result = PMath.div_down_int(6 * PMath.IONE, 3)
        self.assertEqual(result, 2 * PMath.IONE * PMath.IONE)
    
    def test_div_down_int_negative(self):
        """Test div_down_int with negative numerator."""
        # div_down_int(x, y) = (x * IONE) / y
        # -6 * IONE / 3 = -2 * IONE * IONE
        result = PMath.div_down_int(-6 * PMath.IONE, 3)
        self.assertEqual(result, -2 * PMath.IONE * PMath.IONE)
    
    def test_div_down_int_zero_y(self):
        """Test div_down_int raises error when y is zero."""
        with self.assertRaises(PMathOverflowError):
            PMath.div_down_int(5 * PMath.IONE, 0)
    
    def test_raw_div_up_basic(self):
        """Test raw_div_up with basic values."""
        result = PMath.raw_div_up(10, 3)
        self.assertEqual(result, 4)  # ceil(10/3) = 4
    
    def test_raw_div_up_exact(self):
        """Test raw_div_up with exact division."""
        result = PMath.raw_div_up(9, 3)
        self.assertEqual(result, 3)
    
    def test_raw_div_up_zero_d(self):
        """Test raw_div_up raises error when d is zero."""
        with self.assertRaises(PMathOverflowError):
            PMath.raw_div_up(10, 0)
    
    def test_raw_div_ceil_basic(self):
        """Test raw_div_ceil with positive values."""
        result = PMath.raw_div_ceil(10, 3)
        self.assertEqual(result, 4)
    
    def test_raw_div_ceil_negative(self):
        """Test raw_div_ceil with negative numerator."""
        # raw_div_ceil: Only adjusts when x and d have same sign
        # For -10 / 3: different signs, so no adjustment, result = -10 // 3 = -4
        result = PMath.raw_div_ceil(-10, 3)
        self.assertEqual(result, -4)
    
    def test_raw_div_ceil_zero_d(self):
        """Test raw_div_ceil raises error when d is zero."""
        with self.assertRaises(PMathOverflowError):
            PMath.raw_div_ceil(10, 0)
    
    def test_raw_div_floor_basic(self):
        """Test raw_div_floor with positive values."""
        result = PMath.raw_div_floor(10, 3)
        self.assertEqual(result, 3)
    
    def test_raw_div_floor_negative(self):
        """Test raw_div_floor with negative numerator."""
        # raw_div_floor: Only adjusts when x and d have opposite signs
        # For -10 / 3: -10 < 0 and 3 > 0, opposite signs, so subtract 1
        # result = -10 // 3 - 1 = -4 - 1 = -5
        result = PMath.raw_div_floor(-10, 3)
        self.assertEqual(result, -5)
    
    def test_raw_div_floor_zero_d(self):
        """Test raw_div_floor raises error when d is zero."""
        with self.assertRaises(PMathOverflowError):
            PMath.raw_div_floor(10, 0)
    
    def test_mul_ceil_basic(self):
        """Test mul_ceil with basic values."""
        result = PMath.mul_ceil(2 * PMath.IONE, 3 * PMath.IONE)
        self.assertEqual(result, 6 * PMath.IONE)
    
    def test_mul_floor_basic(self):
        """Test mul_floor with basic values."""
        result = PMath.mul_floor(2 * PMath.IONE, 3 * PMath.IONE)
        self.assertEqual(result, 6 * PMath.IONE)


class TestPMathTweak(unittest.TestCase):
    """Test tweak functions."""
    
    def test_tweak_up_basic(self):
        """Test tweak_up with basic values."""
        # a * (1 + factor), with factor = 0.1 * ONE
        factor = PMath.ONE // 10
        result = PMath.tweak_up(PMath.ONE, factor)
        self.assertEqual(result, PMath.ONE + PMath.ONE // 10)
    
    def test_tweak_down_basic(self):
        """Test tweak_down with basic values."""
        # a * (1 - factor), with factor = 0.1 * ONE
        factor = PMath.ONE // 10
        result = PMath.tweak_down(PMath.ONE, factor)
        self.assertEqual(result, PMath.ONE - PMath.ONE // 10)


class TestPMathAbsNeg(unittest.TestCase):
    """Test abs and neg functions."""
    
    def test_abs_positive(self):
        """Test abs with positive value."""
        result = PMath.abs(Decimal(5))
        self.assertEqual(result, Decimal(5))
    
    def test_abs_negative(self):
        """Test abs with negative value."""
        result = PMath.abs(Decimal(-5))
        self.assertEqual(result, Decimal(5))
    
    def test_abs_zero(self):
        """Test abs with zero."""
        result = PMath.abs(Decimal(0))
        self.assertEqual(result, Decimal(0))
    
    def test_neg_basic(self):
        """Test neg with basic value."""
        result = PMath.neg(5)
        self.assertEqual(result, -5)
    
    def test_neg_zero(self):
        """Test neg with zero."""
        result = PMath.neg(0)
        self.assertEqual(result, 0)


class TestPMathMaxMin(unittest.TestCase):
    """Test max and min functions."""
    
    def test_max_first_larger(self):
        """Test max when first value is larger."""
        result = PMath.max(10, 5)
        self.assertEqual(result, 10)
    
    def test_max_second_larger(self):
        """Test max when second value is larger."""
        result = PMath.max(5, 10)
        self.assertEqual(result, 10)
    
    def test_max_equal(self):
        """Test max with equal values."""
        result = PMath.max(5, 5)
        self.assertEqual(result, 5)
    
    def test_max_int_first_larger(self):
        """Test max_int when first value is larger."""
        result = PMath.max_int(10, 5)
        self.assertEqual(result, 10)
    
    def test_max_int_negative(self):
        """Test max_int with negative values."""
        result = PMath.max_int(-5, -10)
        self.assertEqual(result, -5)
    
    def test_max_32_basic(self):
        """Test max_32 basic."""
        result = PMath.max_32(10, 5)
        self.assertEqual(result, 10)
    
    def test_max_40_basic(self):
        """Test max_40 basic."""
        result = PMath.max_40(10, 5)
        self.assertEqual(result, 10)
    
    def test_min_first_smaller(self):
        """Test min when first value is smaller."""
        result = PMath.min(5, 10)
        self.assertEqual(result, 5)
    
    def test_min_second_smaller(self):
        """Test min when second value is smaller."""
        result = PMath.min(10, 5)
        self.assertEqual(result, 5)
    
    def test_min_equal(self):
        """Test min with equal values."""
        result = PMath.min(5, 5)
        self.assertEqual(result, 5)
    
    def test_min_int_first_smaller(self):
        """Test min_int when first value is smaller."""
        result = PMath.min_int(5, 10)
        self.assertEqual(result, 5)
    
    def test_min_int_negative(self):
        """Test min_int with negative values."""
        result = PMath.min_int(-5, -10)
        self.assertEqual(result, -10)


class TestPMathSign(unittest.TestCase):
    """Test sign function."""
    
    def test_sign_positive(self):
        """Test sign with positive value."""
        result = PMath.sign(5)
        self.assertEqual(result, 1)
    
    def test_sign_negative(self):
        """Test sign with negative value."""
        result = PMath.sign(-5)
        self.assertEqual(result, -1)
    
    def test_sign_zero(self):
        """Test sign with zero."""
        result = PMath.sign(0)
        self.assertEqual(result, 0)


class TestPMathAvg(unittest.TestCase):
    """Test average functions."""
    
    def test_avg_basic(self):
        """Test avg with basic values."""
        result = PMath.avg(10, 20)
        self.assertEqual(result, 15)
    
    def test_avg_equal(self):
        """Test avg with equal values."""
        result = PMath.avg(5, 5)
        self.assertEqual(result, 5)
    
    def test_avg_odd_difference(self):
        """Test avg with odd difference."""
        result = PMath.avg(1, 2)
        self.assertEqual(result, 1)  # (1 & 2) + ((1 ^ 2) >> 1) = 0 + 1 = 1
    
    def test_avg_int_basic(self):
        """Test avg_int with basic values."""
        result = PMath.avg_int(10, 20)
        self.assertEqual(result, 15)
    
    def test_avg_int_negative(self):
        """Test avg_int with negative values."""
        result = PMath.avg_int(-10, 10)
        self.assertEqual(result, 0)


class TestPMathCast(unittest.TestCase):
    """Test type casting functions."""
    
    def test_to_int_basic(self):
        """Test to_int with basic value."""
        result = PMath.to_int(100)
        self.assertEqual(result, 100)
    
    def test_to_int_overflow(self):
        """Test to_int raises error when value exceeds int256 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_int(2**255)
    
    def test_to_int128_basic(self):
        """Test to_int128 with basic value."""
        result = PMath.to_int128(100)
        self.assertEqual(result, 100)
    
    def test_to_int128_overflow(self):
        """Test to_int128 raises error when value exceeds int128 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_int128(2**127)
    
    def test_to_int112_basic(self):
        """Test to_int112 with basic value."""
        result = PMath.to_int112(100)
        self.assertEqual(result, 100)
    
    def test_to_int112_overflow_positive(self):
        """Test to_int112 raises error when value exceeds int112 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_int112(2**111)
    
    def test_to_int112_overflow_negative(self):
        """Test to_int112 raises error when value exceeds int112 negative range."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_int112(-(2**111) - 1)
    
    def test_to_int128_int_basic(self):
        """Test to_int128_int with basic value."""
        result = PMath.to_int128_int(100)
        self.assertEqual(result, 100)
    
    def test_to_int128_int_overflow_positive(self):
        """Test to_int128_int raises error when value exceeds int128 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_int128_int(2**127)
    
    def test_to_int128_int_overflow_negative(self):
        """Test to_int128_int raises error when value exceeds int128 negative range."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_int128_int(-(2**127) - 1)
    
    def test_to_uint_basic(self):
        """Test to_uint with basic value."""
        result = PMath.to_uint(100)
        self.assertEqual(result, 100)
    
    def test_to_uint_negative(self):
        """Test to_uint raises error for negative value."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_uint(-1)
    
    def test_to_uint128_basic(self):
        """Test to_uint128 with basic value."""
        result = PMath.to_uint128(100)
        self.assertEqual(result, 100)
    
    def test_to_uint128_negative(self):
        """Test to_uint128 raises error for negative value."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_uint128(-1)
    
    def test_to_uint128_overflow(self):
        """Test to_uint128 raises error when value exceeds uint128 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_uint128(2**128)
    
    def test_to_uint8_bool_true(self):
        """Test to_uint8_bool with True."""
        result = PMath.to_uint8_bool(True)
        self.assertEqual(result, 1)
    
    def test_to_uint8_bool_false(self):
        """Test to_uint8_bool with False."""
        result = PMath.to_uint8_bool(False)
        self.assertEqual(result, 0)
    
    def test_to_uint8_basic(self):
        """Test to_uint8 with basic value."""
        result = PMath.to_uint8(100)
        self.assertEqual(result, 100)
    
    def test_to_uint8_overflow(self):
        """Test to_uint8 raises error when value exceeds uint8 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_uint8(256)
    
    def test_to_uint16_basic(self):
        """Test to_uint16 with basic value."""
        result = PMath.to_uint16(100)
        self.assertEqual(result, 100)
    
    def test_to_uint16_overflow(self):
        """Test to_uint16 raises error when value exceeds uint16 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_uint16(2**16)
    
    def test_to_uint32_basic(self):
        """Test to_uint32 with basic value."""
        result = PMath.to_uint32(100)
        self.assertEqual(result, 100)
    
    def test_to_uint32_overflow(self):
        """Test to_uint32 raises error when value exceeds uint32 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_uint32(2**32)
    
    def test_to_uint40_basic(self):
        """Test to_uint40 with basic value."""
        result = PMath.to_uint40(100)
        self.assertEqual(result, 100)
    
    def test_to_uint40_overflow(self):
        """Test to_uint40 raises error when value exceeds uint40 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_uint40(2**40)
    
    def test_to_uint64_basic(self):
        """Test to_uint64 with basic value."""
        result = PMath.to_uint64(100)
        self.assertEqual(result, 100)
    
    def test_to_uint64_overflow(self):
        """Test to_uint64 raises error when value exceeds uint64 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_uint64(2**64)
    
    def test_to_uint128_uint_basic(self):
        """Test to_uint128_uint with basic value."""
        result = PMath.to_uint128_uint(100)
        self.assertEqual(result, 100)
    
    def test_to_uint128_uint_overflow(self):
        """Test to_uint128_uint raises error when value exceeds uint128 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_uint128_uint(2**128)
    
    def test_to_uint224_basic(self):
        """Test to_uint224 with basic value."""
        result = PMath.to_uint224(100)
        self.assertEqual(result, 100)
    
    def test_to_uint224_overflow(self):
        """Test to_uint224 raises error when value exceeds uint224 max."""
        with self.assertRaises(PMathOverflowError):
            PMath.to_uint224(2**224)


class TestPMathSqrt(unittest.TestCase):
    """Test sqrt function."""
    
    def test_sqrt_zero(self):
        """Test sqrt with zero."""
        result = PMath.sqrt(0)
        self.assertEqual(result, 0)
    
    def test_sqrt_one(self):
        """Test sqrt with one."""
        result = PMath.sqrt(1)
        self.assertEqual(result, 1)
    
    def test_sqrt_four(self):
        """Test sqrt with four."""
        result = PMath.sqrt(4)
        self.assertEqual(result, 2)
    
    def test_sqrt_nine(self):
        """Test sqrt with nine."""
        result = PMath.sqrt(9)
        self.assertEqual(result, 3)
    
    def test_sqrt_perfect_square(self):
        """Test sqrt with medium perfect square."""
        # sqrt(10^12) = 10^6
        result = PMath.sqrt(10**12)
        self.assertEqual(result, 10**6)
    
    def test_sqrt_non_perfect_square(self):
        """Test sqrt with non-perfect square."""
        result = PMath.sqrt(10)
        self.assertEqual(result, 3)  # floor(sqrt(10)) = 3


class TestPMathApprox(unittest.TestCase):
    """Test approximation functions."""
    
    def test_is_a_approx_b_exact(self):
        """Test is_a_approx_b with exact match."""
        result = PMath.is_a_approx_b(PMath.ONE, PMath.ONE, PMath.ONE // 100)
        self.assertTrue(result)
    
    def test_is_a_approx_b_within_epsilon(self):
        """Test is_a_approx_b within epsilon tolerance."""
        # a = 1.01 * ONE, b = ONE, eps = 0.02 * ONE
        a = PMath.ONE + PMath.ONE // 100
        b = PMath.ONE
        eps = PMath.ONE // 50
        result = PMath.is_a_approx_b(a, b, eps)
        self.assertTrue(result)
    
    def test_is_a_approx_b_outside_epsilon(self):
        """Test is_a_approx_b outside epsilon tolerance."""
        # a = 1.1 * ONE, b = ONE, eps = 0.02 * ONE
        a = PMath.ONE + PMath.ONE // 10
        b = PMath.ONE
        eps = PMath.ONE // 50
        result = PMath.is_a_approx_b(a, b, eps)
        self.assertFalse(result)
    
    def test_is_a_greater_approx_b_true(self):
        """Test is_a_greater_approx_b returns True."""
        result = PMath.is_a_greater_approx_b(PMath.ONE, PMath.ONE, PMath.ONE // 100)
        self.assertTrue(result)
    
    def test_is_a_greater_approx_b_false(self):
        """Test is_a_greater_approx_b returns False when a < b."""
        result = PMath.is_a_greater_approx_b(PMath.ONE // 2, PMath.ONE, PMath.ONE // 100)
        self.assertFalse(result)
    
    def test_is_a_smaller_approx_b_true(self):
        """Test is_a_smaller_approx_b returns True."""
        result = PMath.is_a_smaller_approx_b(PMath.ONE, PMath.ONE, PMath.ONE // 100)
        self.assertTrue(result)
    
    def test_is_a_smaller_approx_b_false(self):
        """Test is_a_smaller_approx_b returns False when a > b."""
        result = PMath.is_a_smaller_approx_b(PMath.ONE * 2, PMath.ONE, PMath.ONE // 100)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
