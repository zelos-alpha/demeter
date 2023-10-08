import unittest
from demeter import UnitDecimal, Strategy, AccountStatus, TokenInfo


class UtilsTest(unittest.TestCase):
    def test_init_from_number(self):
        xx = UnitDecimal(23345.4, "WETH")
        self.assertEqual(xx.to_str(), "23345.400 WETH")

    def test_init_from_str(self):
        xx = UnitDecimal("23345.4", "WETH")
        self.assertEqual(xx.to_str(), "23345.4 WETH")

    def test_large_number(self):
        xx: UnitDecimal = UnitDecimal("12345678901234567890123456789012345678901234567890", "WETH")
        print(xx.to_str())

    def test_class_member_init(self):
        s1 = Strategy()
        s2 = Strategy()
        self.assertNotEqual(id(s1.markets), id(s2.markets))
        a1 = AccountStatus(None)
        a2 = AccountStatus(None)
        self.assertNotEqual(id(a1.market_status), id(a2.market_status))

    def test_token_info(self):
        t = TokenInfo("usdt", 6)
        # lower case to upper case
        self.assertEqual(t.name, "USDT")
        self.assertEqual(str(t), "USDT")
