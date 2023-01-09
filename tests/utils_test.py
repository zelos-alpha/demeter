import unittest
from demeter import UnitDecimal


class TestBigQuery(unittest.TestCase):
    def test_init_from_number(self):
        xx = UnitDecimal(23345.4, "WETH")
        self.assertEqual(xx.to_str(),"23345.400 WETH")

    def test_init_from_str(self):
        xx = UnitDecimal("23345.4", "WETH")
        self.assertEqual(xx.to_str(),"23345.4 WETH")

    def test_large_number(self):
        xx: UnitDecimal = UnitDecimal("12345678901234567890123456789012345678901234567890", "WETH")
        print(xx.to_str())
