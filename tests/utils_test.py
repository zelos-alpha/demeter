import unittest
from demeter import UnitDecimal, Strategy, AccountStatus, TokenInfo
from demeter.utils import get_formatted, ModeEnum, ForColorEnum, BackColorEnum


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

    def test_console_text(self):
        print(get_formatted("Normal"))
        print("")
        print("test mode")
        print(
            get_formatted("bold", mode=ModeEnum.bold),
        )
        print(
            get_formatted("underline", mode=ModeEnum.underline),
        )
        print(
            get_formatted("blink", mode=ModeEnum.blink),
        )
        print(
            get_formatted("invert", mode=ModeEnum.invert),
        )
        print(get_formatted("hide", mode=ModeEnum.hide))
        print("")
        print("test forecolor")
        print(
            get_formatted("black", fore=ForColorEnum.black),
        )
        print(
            get_formatted("red", fore=ForColorEnum.red),
        )
        print(
            get_formatted("green", fore=ForColorEnum.green),
        )
        print(
            get_formatted("yellow", fore=ForColorEnum.yellow),
        )
        print(
            get_formatted("blue", fore=ForColorEnum.blue),
        )
        print(
            get_formatted("purple", fore=ForColorEnum.purple),
        )
        print(
            get_formatted("white", fore=ForColorEnum.white),
        )
        print(get_formatted("white", fore=ForColorEnum.white))
        print("")
        print("Test background")
        print(
            get_formatted("black", back=BackColorEnum.black),
        )
        print(
            get_formatted("red", back=BackColorEnum.red),
        )
        print(
            get_formatted("green", back=BackColorEnum.green),
        )
        print(
            get_formatted("yellow", back=BackColorEnum.yellow),
        )
        print(
            get_formatted("blue", back=BackColorEnum.blue),
        )
        print(
            get_formatted("purple", back=BackColorEnum.purple),
        )
        print(
            get_formatted("cyan", back=BackColorEnum.cyan),
        )
        print(get_formatted("white", back=BackColorEnum.white))
        print("")
        print(get_formatted("Compound", ModeEnum.invert, ForColorEnum.red))
