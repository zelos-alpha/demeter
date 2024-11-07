import math
import unittest
from bdb import effective
from decimal import Decimal

from demeter import TokenInfo
from demeter.uniswap import V3CoreLib, UniV3Pool, UniV3PoolStatus, PositionInfo, Position
from demeter.uniswap.helper import (
    tick_to_sqrt_price_x96,
    get_swap_value,
    get_swap_value_with_part_balance_used,
)
from demeter.uniswap.liquitidy_math import get_amounts, estimate_ratio
from tests.common import assert_equal_with_error

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)


class UniLpCoreTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = UniV3Pool(usdc, eth, 0.05, usdc)
        super(UniLpCoreTest, self).__init__(*args, **kwargs)

    def test_add_position1(self):
        # https://polygonscan.com/tx/0x8f4db90e734e80e7101c3247c6e9949fe1f12398edea523e6a2ace04a2dc2425#eventlog
        token0_used, token1_used, liquidity, position = V3CoreLib.new_position(
            self.pool,
            Decimal(1989.968727),
            Decimal(0.733658189325188910),
            193420,
            193460,
            1257384995536224536278388621443072,
        )
        print(token0_used, token1_used, position)
        self.assertTrue(assert_equal_with_error(token0_used, Decimal(521.459929)))
        self.assertTrue(assert_equal_with_error(token1_used, Decimal(0.733658189325188900)))
        self.assertTrue(assert_equal_with_error(liquidity, Decimal(27273497828438404)))

    def test_add_position2(self):
        # https://polygonscan.com/tx/0x2615b8627ee929345ed6388676f7182d3a368cc81869b0e982bbbe62903ae22c#eventlog
        token0_used, token1_used, liquidity, position = V3CoreLib.new_position(
            self.pool,
            Decimal(379.902946),
            Decimal(0.42729421540077245),
            202960,
            204070,
            2095880080440004692038636567265280,
        )
        print(token0_used, token1_used, position)
        self.assertTrue(assert_equal_with_error(token0_used, Decimal(342.361229)))
        self.assertTrue(assert_equal_with_error(token1_used, Decimal(0.427294215400771602)))
        self.assertTrue(assert_equal_with_error(liquidity, Decimal(461087602302446)))

    def test_add_position3(self):
        # https://polygonscan.com/tx/0x68a80c67a6579cd7b390784ebe9d539f6405763d799b31f55fcac2fdd1665050#eventlog
        token0_used, token1_used, liquidity, position = V3CoreLib.new_position(
            self.pool,
            Decimal(74.315359),
            Decimal(0.02722552310238334),
            203960,
            204090,
            2131675114632770577480861800726528,
        )
        print(token0_used, token1_used, position)

        # for x in range(203960,204090):
        #     print(x)
        #     token0_used, token1_used, get_position = V3CoreLib.new_position(self.pool,
        #                                                                 Decimal(74.315359),
        #                                                                 Decimal(0.02722552310238334),
        #                                                                 203960,
        #                                                                 204090,
        #                                                                 x)
        #     print(token0_used / Decimal(56.491219))
        #     print(token1_used / Decimal(0.027225523102383337))
        #     print("---")
        #
        self.assertTrue(assert_equal_with_error(token0_used, Decimal(56.491219)))
        self.assertTrue(assert_equal_with_error(token1_used, Decimal(0.027225523102383337)))
        self.assertTrue(assert_equal_with_error(liquidity, Decimal(390188993876725)))

    # ======================================================================================
    def test_price_change(self):
        # tick 193533
        amount0, amount1 = get_amounts(1262403844616650899412456819409549, 193433, 193633, 425150078827843054, 6, 18)
        print(amount0, amount1)
        # if 0(usdc) is quote, base token(eth) price is down (actually from 39XX -> 38XX)
        # so, if 1(eth) is quote, baes token(usdc) price is up

        # tick 193741
        amount0_after, amount1_after = get_amounts(
            1275614182500083049189169924480275, 193433, 193633, 425150078827843054, 6, 18
        )
        # get more eth
        print(amount0_after, amount1_after)
        self.assertTrue(amount1_after > amount1)

    # =======================================================================================

    def test_amount_convert(self):
        """
        Estimate ratio of amount 0 and amount 1 before adding liquidity,
        :return:
        """
        pool = UniV3Pool(TokenInfo("usdc", 6), TokenInfo("eth", 18), 0.05, TokenInfo("usdc", 6))

        current_tick = 193533
        amp = estimate_ratio(current_tick, 193433, 193633)
        sqrt_price_x96 = tick_to_sqrt_price_x96(current_tick)
        amp_with_decimal = amp * 10 ** (pool.token1.decimal - pool.token0.decimal)
        print(f"eth:usdc => 1:{amp_with_decimal}")

        token0_in_position, token1_in_position, position_liq, new_position_entity = V3CoreLib.new_position(
            pool, amp_with_decimal, 1, 193433, 193633, sqrt_price_x96
        )
        print(f" in usdc:{amp_with_decimal},                    eth: {1}")
        print(f"out usdc:{token0_in_position}, eth: {token1_in_position}, liq: {position_liq}")

        self.assertEqual(Decimal(token1_in_position).quantize(Decimal("0.000001")), Decimal(1))
        self.assertEqual(
            Decimal(token0_in_position).quantize(Decimal("0.000001")),
            Decimal(amp_with_decimal).quantize(Decimal("0.000001")),
        )

    def test_keep_value_ratio_after_swap(self):

        from_val = 3000
        to_val = 1000
        fee_rate = 0.01
        final_ratio = 1
        m = get_swap_value(from_val, to_val, fee_rate, final_ratio)
        print(m)
        self.assertEqual((from_val - m) / (to_val + m * (1 - fee_rate)), final_ratio)

        from_val = 3000
        to_val = 1000
        fee_rate = 0.01
        final_ratio = 2
        m = get_swap_value(from_val, to_val, fee_rate, final_ratio)
        print(m)
        self.assertEqual((from_val - m) / (to_val + m * (1 - fee_rate)), final_ratio)

        from_val = 1000
        to_val = 5000
        fee_rate = 0.01
        final_ratio = 1 / 8
        m = get_swap_value(from_val, to_val, fee_rate, final_ratio)
        print(m)
        self.assertEqual((from_val - m) / (to_val + m * (1 - fee_rate)), final_ratio)

    def test_get_swap_value_with_part_balance_used(self):

        from_val = 3000
        to_val = 1000
        fee_rate = 0.01
        final_ratio = 1
        to_invest_t = 1500
        to_invest_f = final_ratio * to_invest_t
        actual_from, actual_to, m = get_swap_value_with_part_balance_used(
            from_val, to_val, to_invest_f + to_invest_t, fee_rate, final_ratio
        )
        print("from", actual_from, "to", actual_to, "swap", m, "fee", m * fee_rate)
        self.assertEqual(actual_from / actual_to, final_ratio)
        self.assertEqual(actual_from + actual_to + m * fee_rate, to_invest_f + to_invest_t)
        self.assertGreaterEqual(from_val + to_val, actual_from + actual_to + m * fee_rate)
        from_val = 3000
        to_val = 1000
        fee_rate = 0.01
        final_ratio = 2
        to_invest_t = 1100
        to_invest_f = final_ratio * to_invest_t
        actual_from, actual_to, m = get_swap_value_with_part_balance_used(
            from_val, to_val, to_invest_f + to_invest_t, fee_rate, final_ratio
        )
        print("from", actual_from, "to", actual_to, "swap", m, "fee", m * fee_rate)
        self.assertTrue(math.isclose(actual_from / actual_to, final_ratio, abs_tol=0.000001))
        self.assertTrue(
            math.isclose(actual_from + actual_to + m * fee_rate, to_invest_f + to_invest_t, abs_tol=0.000001)
        )
        self.assertGreaterEqual(from_val + to_val, actual_from + actual_to + m * fee_rate)

    def test_compare_two_algrim(self):

        from_val = 2400
        to_val = 900
        fee_rate = 0.01
        final_ratio = 2
        to_invest_t = 1100
        to_invest_f = final_ratio * to_invest_t
        actual_from, actual_to, m = get_swap_value_with_part_balance_used(
            from_val, to_val, to_invest_f + to_invest_t, fee_rate, final_ratio
        )
        print("from", actual_from, "to", actual_to, "swap", m, "fee", m * fee_rate)

        self.assertTrue(math.isclose(actual_from / actual_to, final_ratio, abs_tol=0.000001))
        self.assertTrue(
            math.isclose(actual_from + actual_to + m * fee_rate, to_invest_f + to_invest_t, abs_tol=0.000001)
        )
        self.assertGreaterEqual(from_val + to_val, actual_from + actual_to + m * fee_rate)

        m2 = get_swap_value(from_val, to_val, fee_rate, final_ratio)

        print("from", from_val - m2, "to", to_val + m2 - m2 * fee_rate, "swap", m2, "fee", m2 * fee_rate)
        self.assertEqual((from_val - m2) / (to_val + m2 * (1 - fee_rate)), final_ratio)

        self.assertEqual(m, m2)

    def test_nearly_full(self):

        from_val = 2400
        to_val = 900
        fee_rate = 0.01
        final_ratio = 2
        to_invest_t = 1100
        to_invest_f = final_ratio * to_invest_t
        actual_from, actual_to, m = get_swap_value_with_part_balance_used(
            from_val, to_val, to_invest_f + to_invest_t, fee_rate, final_ratio
        )
        print("from", actual_from, "to", actual_to, "swap", m, "fee", m * fee_rate)

        from_val = 2400
        to_val = 900
        fee_rate = 0.01
        final_ratio = 2
        to_invest_t = 1099.8
        to_invest_f = final_ratio * to_invest_t
        actual_from, actual_to, m = get_swap_value_with_part_balance_used(
            from_val, to_val, to_invest_f + to_invest_t, fee_rate, final_ratio
        )
        print("from", actual_from, "to", actual_to, "swap", m, "fee", m * fee_rate)

        self.assertTrue(math.isclose(actual_from / actual_to, final_ratio, abs_tol=0.000001))
        self.assertTrue(
            math.isclose(actual_from + actual_to + m * fee_rate, to_invest_f + to_invest_t, abs_tol=0.000001)
        )
        self.assertGreaterEqual(from_val + to_val, actual_from + actual_to + m * fee_rate)

    def test_fee(self):
        token0 = TokenInfo("eth", 0)
        token1 = TokenInfo("usd", 0)
        pool = UniV3Pool(token0, token1, 1, token1)
        state = UniV3PoolStatus(currentLiquidity=10000, inAmount0=10000, inAmount1=10000, price=Decimal(1))
        pos: PositionInfo = PositionInfo(5, 10)
        # =======In range==============
        position: Position = Position(Decimal(0), Decimal(0), 500, None, None)
        last_tick = 6
        state.closeTick = 7
        V3CoreLib.update_fee(last_tick, pool, pos, position, state)
        self.assertEqual(position.pending_amount0, Decimal("5"))
        # =======out range=============
        position: Position = Position(Decimal(0), Decimal(0), 500, None, None)
        last_tick = 12
        state.closeTick = 14
        V3CoreLib.update_fee(last_tick, pool, pos, position, state)
        self.assertEqual(position.pending_amount0, Decimal("0"))
        # =======out then in, share should be 1=============
        position: Position = Position(Decimal(0), Decimal(0), 500, None, None)
        last_tick = 1
        state.closeTick = 6
        V3CoreLib.update_fee(last_tick, pool, pos, position, state)
        self.assertEqual(position.pending_amount0, Decimal(1))

        # =======in then out, share should be 2=============
        position: Position = Position(Decimal(0), Decimal(0), 500, None, None)
        last_tick = 8
        state.closeTick = 13
        V3CoreLib.update_fee(last_tick, pool, pos, position, state)
        self.assertEqual(position.pending_amount0, Decimal(2))

        # =======from upper out to lower out=============
        position: Position = Position(Decimal(0), Decimal(0), 500, None, None)
        last_tick = 3
        state.closeTick = 13
        V3CoreLib.update_fee(last_tick, pool, pos, position, state)
        self.assertEqual(position.pending_amount0, Decimal("2.5"))