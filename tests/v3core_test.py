import unittest
from decimal import Decimal

from demeter import TokenInfo, PoolBaseInfo
from demeter.broker.v3_core import V3CoreLib

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)


class V3CoreTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = PoolBaseInfo(usdc, eth, 0.05, usdc)
        super(V3CoreTest, self).__init__(*args, **kwargs)

    def test_add_position(self):
        # https://polygonscan.com/tx/0x8f4db90e734e80e7101c3247c6e9949fe1f12398edea523e6a2ace04a2dc2425#eventlog
        token0_used, token1_used, position = V3CoreLib.new_position(self.pool,
                                                                    Decimal(1989968727),
                                                                    Decimal(733658189325188910),
                                                                    193420,
                                                                    193460,
                                                                    193453)
        self.assertEqual(token0_used, Decimal(521459929))
        self.assertEqual(token1_used, Decimal(733658189325188900))
        self.assertEqual(position.liquidity, Decimal(27273497828438404))
