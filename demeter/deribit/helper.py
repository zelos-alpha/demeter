from decimal import Decimal


def round_decimal(num: Decimal, exponent: int) -> Decimal:
    val = num.quantize(Decimal(f"1e{exponent}"))
    if exponent > 0:
        val = val.quantize(Decimal(0))
    return val
