"""
Test cases for TickMath module.
"""
import unittest
import math
from demeter.boros_v4.TickMath import TickMath


class TestTickMathConstants(unittest.TestCase):
    """Test TickMath constants."""

    def test_base_rate(self):
        """Test BASE_RATE constant equals 1.00005."""
        self.assertEqual(TickMath.BASE_RATE, 1.00005)

    def test_rate_constants_exist(self):
        """Test RATE_CONSTANTS dictionary exists and has expected entries."""
        self.assertIn(0, TickMath.RATE_CONSTANTS)
        self.assertIn(1, TickMath.RATE_CONSTANTS)
        self.assertIn(10, TickMath.RATE_CONSTANTS)
        self.assertIn(15, TickMath.RATE_CONSTANTS)

    def test_high_rate_constants_exist(self):
        """Test HIGH_RATE_CONSTANTS dictionary exists and has expected entries."""
        self.assertIn(16, TickMath.HIGH_RATE_CONSTANTS)
        self.assertIn(17, TickMath.HIGH_RATE_CONSTANTS)
        self.assertIn(18, TickMath.HIGH_RATE_CONSTANTS)


class TestGetRateAtTick(unittest.TestCase):
    """Test cases for get_rate_at_tick method."""

    def test_rate_at_tick_zero(self):
        """Test rate at tick 0 is 0."""
        rate = TickMath.get_rate_at_tick(0)
        self.assertEqual(rate, 0.0)

    def test_rate_at_tick_positive_small(self):
        """Test rate at small positive tick."""
        # tick = 1, rate = 1.00005^1 - 1 = 0.00005
        rate = TickMath.get_rate_at_tick(1)
        self.assertAlmostEqual(rate, 0.00005, places=6)

    def test_rate_at_tick_positive_100(self):
        """Test rate at tick 100."""
        # rate = 1.00005^100 - 1 ≈ 0.005001
        rate = TickMath.get_rate_at_tick(100)
        expected = (1.00005 ** 100) - 1
        self.assertAlmostEqual(rate, expected, places=6)

    def test_rate_at_tick_positive_1000(self):
        """Test rate at tick 1000."""
        # rate = 1.00005^1000 - 1 ≈ 0.051267
        rate = TickMath.get_rate_at_tick(1000)
        expected = (1.00005 ** 1000) - 1
        self.assertAlmostEqual(rate, expected, places=6)

    def test_rate_at_tick_negative_small(self):
        """Test rate at small negative tick."""
        # tick = -1, rate = -(1.00005^1 - 1) = -0.00005
        rate = TickMath.get_rate_at_tick(-1)
        self.assertAlmostEqual(rate, -0.00005, places=6)

    def test_rate_at_tick_negative_100(self):
        """Test rate at tick -100."""
        rate = TickMath.get_rate_at_tick(-100)
        expected = -((1.00005 ** 100) - 1)
        self.assertAlmostEqual(rate, expected, places=6)

    def test_rate_at_tick_with_step(self):
        """Test rate with step multiplier."""
        # tick = 10, step = 2, effective_tick = 20
        # rate = 1.00005^20 - 1
        rate = TickMath.get_rate_at_tick(10, step=2)
        expected = (1.00005 ** 20) - 1
        self.assertAlmostEqual(rate, expected, places=6)

    def test_rate_at_tick_step_1(self):
        """Test rate with step = 1 (default)."""
        rate1 = TickMath.get_rate_at_tick(50)
        rate2 = TickMath.get_rate_at_tick(50, step=1)
        self.assertEqual(rate1, rate2)

    def test_rate_symmetry(self):
        """Test that rate(tick) = -rate(-tick)."""
        rate_pos = TickMath.get_rate_at_tick(100)
        rate_neg = TickMath.get_rate_at_tick(-100)
        self.assertAlmostEqual(rate_pos, -rate_neg, places=6)


class TestGetTickAtRate(unittest.TestCase):
    """Test cases for get_tick_at_rate method."""

    def test_tick_at_rate_zero(self):
        """Test tick at rate 0 is 0."""
        tick = TickMath.get_tick_at_rate(0.0)
        self.assertEqual(tick, 0)

    def test_tick_at_rate_positive_small(self):
        """Test tick at small positive rate."""
        # rate = 0.00005 ≈ 1.00005^1 - 1
        tick = TickMath.get_tick_at_rate(0.00005)
        self.assertEqual(tick, 1)

    def test_tick_at_rate_positive_100(self):
        """Test tick at rate ~0.5%."""
        # rate = 1.00005^100 - 1 ≈ 0.005001
        rate = (1.00005 ** 100) - 1
        tick = TickMath.get_tick_at_rate(rate)
        # Should be close to 100 (accounting for rounding)
        self.assertIn(tick, [99, 100, 101])

    def test_tick_at_rate_negative_small(self):
        """Test tick at small negative rate."""
        tick = TickMath.get_tick_at_rate(-0.00005)
        self.assertIn(tick, [-1, 0, 1])

    def test_tick_at_rate_negative(self):
        """Test tick at negative rate."""
        rate = -((1.00005 ** 50) - 1)
        tick = TickMath.get_tick_at_rate(rate)
        # Should be negative
        self.assertLess(tick, 0)

    def test_tick_at_rate_with_step(self):
        """Test tick with step multiplier."""
        # rate corresponding to tick = 100, step = 2 (effective tick = 200)
        rate = (1.00005 ** 200) - 1
        tick = TickMath.get_tick_at_rate(rate, step=2)
        # Should be close to 100
        self.assertIn(tick, [99, 100, 101])

    def test_tick_at_rate_roundtrip(self):
        """Test that get_tick_at_rate(get_rate_at_tick(tick)) ≈ tick."""
        original_tick = 100
        rate = TickMath.get_rate_at_tick(original_tick)
        computed_tick = TickMath.get_tick_at_rate(rate)
        self.assertIn(computed_tick, [99, 100])


class TestTickMathIntegration(unittest.TestCase):
    """Integration tests for TickMath."""

    def test_roundtrip_positive_ticks(self):
        """Test rate -> tick -> rate roundtrip for positive ticks."""
        for tick in [1, 10, 50, 100, 500, 1000]:
            rate = TickMath.get_rate_at_tick(tick)
            computed_tick = TickMath.get_tick_at_rate(rate)
            self.assertIn(computed_tick, [tick - 1, tick, tick + 1],
                          f"Roundtrip failed for tick {tick}")

    def test_roundtrip_negative_ticks(self):
        """Test rate -> tick -> rate roundtrip for negative ticks."""
        for tick in [-1, -10, -50, -100, -500, -1000]:
            rate = TickMath.get_rate_at_tick(tick)
            computed_tick = TickMath.get_tick_at_rate(rate)
            self.assertIn(computed_tick, [tick - 1, tick, tick + 1],
                          f"Roundtrip failed for tick {tick}")

    def test_rate_monotonic_increasing(self):
        """Test that rate increases with tick."""
        rates = [TickMath.get_rate_at_tick(t) for t in range(0, 101, 10)]
        for i in range(len(rates) - 1):
            self.assertGreater(rates[i + 1], rates[i],
                              f"Rate should increase with tick")

    def test_rate_monotonic_decreasing(self):
        """Test that rate decreases with negative tick."""
        rates = [TickMath.get_rate_at_tick(-t) for t in range(0, 101, 10)]
        for i in range(len(rates) - 1):
            self.assertLess(rates[i + 1], rates[i],
                           f"Rate should decrease with negative tick")

    def test_rate_values_match_formula(self):
        """Test that rate values match the documented formula."""
        # For tick >= 0: rate = 1.00005^tick - 1
        for tick in [1, 10, 100]:
            rate = TickMath.get_rate_at_tick(tick)
            expected = (TickMath.BASE_RATE ** tick) - 1
            self.assertAlmostEqual(rate, expected, places=6)

        # For tick < 0: rate = -(1.00005^(-tick) - 1)
        for tick in [-1, -10, -100]:
            rate = TickMath.get_rate_at_tick(tick)
            expected = -((TickMath.BASE_RATE ** abs(tick)) - 1)
            self.assertAlmostEqual(rate, expected, places=6)

    def test_step_multiplier_effect(self):
        """Test that step multiplier scales the effective tick."""
        base_rate = TickMath.get_rate_at_tick(10)
        doubled_rate = TickMath.get_rate_at_tick(10, step=2)
        
        # rate(10, step=2) should equal rate(20)
        expected = TickMath.get_rate_at_tick(20)
        self.assertAlmostEqual(doubled_rate, expected, places=6)


if __name__ == '__main__':
    unittest.main()
