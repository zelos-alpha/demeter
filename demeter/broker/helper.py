import math
from decimal import Decimal
from .liquitidymath import getSqrtRatioAtTick


def _x96_to_decimal(number: int):
    return Decimal(number) / 2 ** 96


def decimal_to_x96(number: Decimal):
    return int(Decimal(number) * 2 ** 96)


def _x96_sqrt_to_decimal(sqrt_priceX96, token_decimal_diff=12):
    price = _x96_to_decimal(sqrt_priceX96)
    return (price ** 2) / 10 ** token_decimal_diff


## can round by spacing?
def sqrt_price_to_tick(sqrt_priceX96: int) -> int:
    decimal_price = _x96_to_decimal(sqrt_priceX96)
    return pool_price_to_tick(decimal_price)


def pool_price_to_tick(price_decimal: Decimal):
    return int(math.log(price_decimal, math.sqrt(1.0001)))


def tick_to_quote_price(tick: int, token_0_decimal, token_1_decimal, is_token0_base: bool):
    sqrt_price = getSqrtRatioAtTick(tick)
    decimal_price = _x96_to_decimal(sqrt_price) ** 2
    pool_price = decimal_price * Decimal(10 ** (token_0_decimal - token_1_decimal))
    return Decimal(1 / pool_price) if is_token0_base else pool_price


def quote_price_to_tick(based_price: Decimal, token_0_decimal: int, token_1_decimal: int, is_token_base) -> int:
    # quote price->add decimal pool price->sqrt_price ->ticker

    price = 1 / based_price if is_token_base else based_price
    pool_price = price / Decimal(10 ** (token_0_decimal - token_1_decimal))
    decimal_price = Decimal.sqrt(pool_price)
    sqrt_price = decimal_to_x96(decimal_price)
    tick = sqrt_price_to_tick(sqrt_price)
    return tick


def from_wei(token_amt: int, decimal: int):
    return Decimal(token_amt) / Decimal(10 ** decimal)
