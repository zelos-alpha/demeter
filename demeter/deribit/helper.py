import decimal
from decimal import Decimal
from typing import Any


def round_decimal(num: Any, exponent: int) -> Decimal:
    """
    | Adjusting the number to a specific number of digits, eg:
    | self.assertEqual(Decimal("123500000"), round_decimal("123456789", 5))
    | self.assertEqual(Decimal("123000000"), round_decimal("123456789", 6))
    | self.assertEqual(Decimal("120"), round_decimal("123", 1))
    | self.assertEqual(Decimal("123"), round_decimal("123", 0))
    | self.assertEqual(Decimal("1.2"), round_decimal("1.23456789", -1))
    | self.assertEqual(Decimal("1.2346"), round_decimal("1.23456789", -4))


    :param num: number in any type, such as int/float/Decimal/str
    :type num: Any
    :param exponent: specific number of digits,
    :type exponent: int
    """
    if not isinstance(num, Decimal):
        num = Decimal(num)
    val = num.quantize(Decimal(f"1e{exponent}"), rounding=decimal.ROUND_HALF_UP)
    if exponent > 0:
        val = val.quantize(Decimal(0))
    return val
