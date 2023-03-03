import unittest
from decimal import Decimal

from demeter.uniswap import helper, liquitidy_math
from tests.common import assert_equal_with_error


class UniLpDataTest(unittest.TestCase):

    def test_delta_gamma_is_0_base(self):
        price = Decimal(1000)
        price_diff = 100
        sqrt = helper.quote_price_to_sqrt(price, 6, 18, True)
        lower_tick = helper.quote_price_to_tick(price - price_diff, 6, 18, True)
        upper_tick = helper.quote_price_to_tick(price + price_diff, 6, 18, True)

        liquidity = liquitidy_math.get_liquidity(sqrt, lower_tick, upper_tick, Decimal(1000), Decimal(1), 6, 18)

        low_price_float = float(price) - price_diff
        high_price_float = float(price) + price_diff

        very_low_sqrt = helper.quote_price_to_sqrt(Decimal(1), 6, 18, True)
        amount0, amount1 = liquitidy_math.get_amounts(very_low_sqrt, lower_tick, upper_tick, liquidity, 6, 18)
        delta, gamma = helper.get_delta_gamma(low_price_float, high_price_float, 1, liquidity, 6, 18, True)
        self.assertTrue(assert_equal_with_error(amount1, Decimal(delta), allowed_error=0.01))
        self.assertTrue(gamma == 0)

        delta, gamma = helper.get_delta_gamma(low_price_float, high_price_float, 2000, liquidity, 6, 18, True)
        self.assertEqual(delta, 0)
        self.assertEqual(gamma, 0)

        delta, gamma = helper.get_delta_gamma(low_price_float, high_price_float, float(price), liquidity, 6, 18, True)
        print(delta, gamma)

        self.assertTrue(assert_equal_with_error(delta, 0.9074351443912998))
        self.assertTrue(assert_equal_with_error(gamma, -0.009749523337042907))

    def test_amount_is_0_base(self):
        """
        verify calculation of net value is right.
        :return:
        :rtype:
        """
        k = 2 ** 96
        price = Decimal(1100)
        price_float = float(price)
        d0 = 6
        d1 = 18
        d = d0 - d1
        sqrt = helper.quote_price_to_sqrt(price, 6, 18, True)
        lower_tick = helper.quote_price_to_tick(Decimal(600), d0, d1, True)
        upper_tick = helper.quote_price_to_tick(Decimal(1100), d0, d1, True)
        lower_sqrt = helper.quote_price_to_sqrt(Decimal(1100), d0, d1, True)
        upper_sqrt = helper.quote_price_to_sqrt(Decimal(600), d0, d1, True)

        liquidity = liquitidy_math.get_liquidity(sqrt, lower_tick, upper_tick, Decimal(1000), Decimal(1), d0, d1)

        amount0, amount1 = liquitidy_math.get_amounts(sqrt, lower_tick, upper_tick, liquidity, d0, d1)
        net_value_old = amount0 + amount1 * price
        print(amount0, amount1)

        net_value_new = liquidity * 10 ** (0.5 * d) / 10 ** d0 * price_float ** 0.5 - \
                        k / upper_sqrt * liquidity / 10 ** d0 + \
                        liquidity * price_float ** 0.5 / 10 ** d1 / 10 ** (0.5 * d) - \
                        lower_sqrt / k * price_float * liquidity / 10 ** d1
        print(net_value_old, net_value_new)
        self.assertTrue(assert_equal_with_error(net_value_old, Decimal(net_value_new), allowed_error=0.001))

    def test_delta_gamma_is_1_base(self):
        price = Decimal("1000")
        price_diff = 100
        sqrt = helper.quote_price_to_sqrt(price, 18, 6, False)
        lower_tick = helper.quote_price_to_tick(price - price_diff, 18, 6, False)
        upper_tick = helper.quote_price_to_tick(price + price_diff, 18, 6, False)

        liquidity = liquitidy_math.get_liquidity(sqrt, lower_tick, upper_tick, Decimal(1), Decimal(1000), 18, 6)

        low_price_float = float(price) - price_diff
        high_price_float = float(price) + price_diff

        delta, gamma = helper.get_delta_gamma(low_price_float, high_price_float, 2000, liquidity, 18, 6, False)
        self.assertEqual(delta, 0)
        self.assertEqual(gamma, 0)

        very_low_sqrt = helper.quote_price_to_sqrt(Decimal(1), 18, 6, False)
        amount0, amount1 = liquitidy_math.get_amounts(very_low_sqrt, lower_tick, upper_tick, liquidity, 18, 6)
        delta, gamma = helper.get_delta_gamma(low_price_float, high_price_float, 1, liquidity, 18, 6, False)
        self.assertTrue(assert_equal_with_error(amount0, Decimal(delta), allowed_error=0.01))
        self.assertTrue(gamma == 0)

        delta, gamma = helper.get_delta_gamma(low_price_float, high_price_float, float(price), liquidity, 18, 6,
                                              False)
        print(delta, gamma)
        self.assertTrue(assert_equal_with_error(delta, 0.9074351443912998))
        self.assertTrue(assert_equal_with_error(gamma, -0.009749523337042907))

    def test_amount_is_1_base(self):
        """
        verify calculation of net value is right.
        :return:
        :rtype:
        """
        k = 2 ** 96
        price = Decimal(850)
        price_float = float(price)
        d0 = 18
        d1 = 6
        d = d0 - d1
        sqrt = helper.quote_price_to_sqrt(price, d0, d1, False)
        lower_tick = helper.quote_price_to_tick(Decimal(600), d0, d1, False)
        upper_tick = helper.quote_price_to_tick(Decimal(1100), d0, d1, False)
        lower_sqrt = helper.quote_price_to_sqrt(Decimal(600), d0, d1, False)
        upper_sqrt = helper.quote_price_to_sqrt(Decimal(1100), d0, d1, False)

        liquidity = liquitidy_math.get_liquidity(sqrt, lower_tick, upper_tick, Decimal(1), Decimal(1000), d0, d1)

        amount0, amount1 = liquitidy_math.get_amounts(sqrt, lower_tick, upper_tick, liquidity, d0, d1)
        net_value_old = amount0 * price + amount1
        print(amount0, amount1)

        net_value_new = liquidity * price_float ** 0.5 * 10 ** (0.5 * d) / 10 ** d0 - \
                        k / upper_sqrt * liquidity * price_float / 10 ** d0 + \
                        liquidity * price_float ** 0.5 / 10 ** d1 / 10 ** (0.5 * d) - \
                        lower_sqrt / k * liquidity / 10 ** d1
        print(net_value_old, net_value_new)
        self.assertTrue(assert_equal_with_error(net_value_old, Decimal(net_value_new), allowed_error=0.001))
