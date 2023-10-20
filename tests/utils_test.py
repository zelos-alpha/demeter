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
        print(get_formatted('正常显示'))
        print('')
        print("测试显示模式")
        print(get_formatted('高亮', mode=ModeEnum.bold), )
        print(get_formatted('下划线', mode=ModeEnum.underline), )
        print(get_formatted('闪烁', mode=ModeEnum.blink), )
        print(get_formatted('反白', mode=ModeEnum.invert), )
        print(get_formatted('不可见', mode=ModeEnum.hide))
        print('')
        print("测试前景色")
        print(get_formatted('黑色', fore=ForColorEnum.black), )
        print(get_formatted('红色', fore=ForColorEnum.red), )
        print(get_formatted('绿色', fore=ForColorEnum.green), )
        print(get_formatted('黄色', fore=ForColorEnum.yellow), )
        print(get_formatted('蓝色', fore=ForColorEnum.blue), )
        print(get_formatted('紫红色', fore=ForColorEnum.purple), )
        print(get_formatted('青蓝色', fore=ForColorEnum.cyan), )
        print(get_formatted('白色', fore=ForColorEnum.white))
        print('')
        print("测试背景色")
        print(get_formatted('黑色', back=BackColorEnum.black), )
        print(get_formatted('红色', back=BackColorEnum.red), )
        print(get_formatted('绿色', back=BackColorEnum.green), )
        print(get_formatted('黄色', back=BackColorEnum.yellow), )
        print(get_formatted('蓝色', back=BackColorEnum.blue), )
        print(get_formatted('紫红色', back=BackColorEnum.purple), )
        print(get_formatted('青蓝色', back=BackColorEnum.cyan), )
        print(get_formatted('白色', back=BackColorEnum.white))
        print('')
        print(get_formatted("综合", ModeEnum.invert, ForColorEnum.red))