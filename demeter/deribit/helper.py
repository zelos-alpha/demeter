import decimal
from decimal import Decimal
from typing import Any


def round_decimal(num: Any, exponent: int) -> Decimal:
    if not isinstance(num, Decimal):
        num = Decimal(num)
    val = num.quantize(Decimal(f"1e{exponent}"), rounding=decimal.ROUND_HALF_UP)
    if exponent > 0:
        val = val.quantize(Decimal(0))
    return val
