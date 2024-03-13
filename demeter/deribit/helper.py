from decimal import Decimal
from typing import Any


def round_decimal(num: Any, exponent: int) -> Decimal:
    num = Decimal(num)
    val = num.quantize(Decimal(f"1e{exponent}"))
    if exponent > 0:
        val = val.quantize(Decimal(0))
    return val
