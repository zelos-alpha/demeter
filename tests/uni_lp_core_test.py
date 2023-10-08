import unittest
from decimal import Decimal

from demeter import TokenInfo
from demeter.uniswap import V3CoreLib, UniV3Pool
from tests.common import assert_equal_with_error

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)


class UniLpCoreTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = UniV3Pool(usdc, eth, 0.05, usdc)
        super(UniLpCoreTest, self).__init__(*args, **kwargs)

    def test_add_position1(self):
        # https://polygonscan.com/tx/0x8f4db90e734e80e7101c3247c6e9949fe1f12398edea523e6a2ace04a2dc2425#eventlog
        token0_used, token1_used, liquidity, position = V3CoreLib.new_position(self.pool,
                                                                               Decimal(1989.968727),
                                                                               Decimal(0.733658189325188910),
                                                                               193420,
                                                                               193460,
                                                                               1257384995536224536278388621443072)
        print(token0_used, token1_used, position)
        self.assertTrue(assert_equal_with_error(token0_used, Decimal(521.459929)))
        self.assertTrue(assert_equal_with_error(token1_used, Decimal(0.733658189325188900)))
        self.assertTrue(assert_equal_with_error(liquidity, Decimal(27273497828438404)))

    def test_add_position2(self):
        # https://polygonscan.com/tx/0x2615b8627ee929345ed6388676f7182d3a368cc81869b0e982bbbe62903ae22c#eventlog
        token0_used, token1_used, liquidity, position = V3CoreLib.new_position(self.pool,
                                                                               Decimal(379.902946),
                                                                               Decimal(0.42729421540077245),
                                                                               202960,
                                                                               204070,
                                                                               2095880080440004692038636567265280)
        print(token0_used, token1_used, position)
        self.assertTrue(assert_equal_with_error(token0_used, Decimal(342.361229)))
        self.assertTrue(assert_equal_with_error(token1_used, Decimal(0.427294215400771602)))
        self.assertTrue(assert_equal_with_error(liquidity, Decimal(461087602302446)))

    def test_add_position3(self):
        # https://polygonscan.com/tx/0x68a80c67a6579cd7b390784ebe9d539f6405763d799b31f55fcac2fdd1665050#eventlog
        token0_used, token1_used, liquidity, position = V3CoreLib.new_position(self.pool,
                                                                               Decimal(74.315359),
                                                                               Decimal(0.02722552310238334),
                                                                               203960,
                                                                               204090,
                                                                               2131675114632770577480861800726528)
        print(token0_used, token1_used, position)

        # for x in range(203960,204090):
        #     print(x)
        #     token0_used, token1_used, position = V3CoreLib.new_position(self.pool,
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
