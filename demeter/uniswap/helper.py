import math
from decimal import Decimal

from .liquitidy_math import get_sqrt_ratio_at_tick


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


def tick_to_sqrtPriceX96(tick: int):
    return get_sqrt_ratio_at_tick(tick)


def tick_to_quote_price(tick: int, token_0_decimal, token_1_decimal, is_token0_base: bool):
    sqrt_price = get_sqrt_ratio_at_tick(tick)
    decimal_price = _x96_to_decimal(sqrt_price) ** 2
    pool_price = decimal_price * Decimal(10 ** (token_0_decimal - token_1_decimal))
    return Decimal(1 / pool_price) if is_token0_base else pool_price


def quote_price_to_tick(based_price: Decimal, token_0_decimal: int, token_1_decimal: int, is_token_base) -> int:
    # quote price->add decimal pool price->sqrt_price ->ticker
    sqrt_price = quote_price_to_sqrt(based_price, token_0_decimal, token_1_decimal, is_token_base)
    tick = sqrt_price_to_tick(sqrt_price)
    return tick


def quote_price_to_sqrt(based_price: Decimal, token_0_decimal: int, token_1_decimal: int, is_token_base) -> int:
    # quote price->add decimal pool price->sqrt_price ->ticker

    price = 1 / based_price if is_token_base else based_price
    pool_price = price / Decimal(10 ** (token_0_decimal - token_1_decimal))
    decimal_price = Decimal.sqrt(pool_price)
    return decimal_to_x96(decimal_price)


def from_wei(token_amt: int, decimal: int) -> Decimal:
    return Decimal(int(token_amt)) / Decimal(10 ** decimal)


def get_delta_gamma(lower_price: float, upper_price: float, price: float,
                    liquidity: int, decimal0: int, decimal1: int, is_0_base: bool):
    lower_price_sqrtX96 = quote_price_to_sqrt(Decimal(lower_price), decimal0, decimal1, is_0_base)
    upper_price_sqrtX96 = quote_price_to_sqrt(Decimal(upper_price), decimal0, decimal1, is_0_base)
    if lower_price_sqrtX96 > upper_price_sqrtX96:
        (lower_price_sqrtX96, upper_price_sqrtX96) = (upper_price_sqrtX96, lower_price_sqrtX96)
    return get_delta_gamma_sqrtX96(lower_price,
                                   lower_price_sqrtX96,
                                   upper_price,
                                   upper_price_sqrtX96,
                                   price,
                                   liquidity,
                                   decimal0, decimal1,
                                   is_0_base)


def get_delta_gamma_sqrtX96(lower_price, sqrtA: int,
                            upper_price, sqrtB: int,
                            price,
                            liquidity: int,
                            d0: int,
                            d1: int,
                            is_0_base: bool):
    """
    k = 2 ** 96
    a0 = k * (10**(-d)) * Liquidity * (1/SqrtPrice - 1/upper_price_sqrtX96)
    a1= Liquidity / k / 10**d * (SqrtPrice - lower_price_sqrtX96)


    if 0 base:
    SqrtPrice=k / (10 ** (d/2)) / (p**0.5)
    net_value = a1 * p                    price <= lower, a0 is constant
                a0 + a1 * p               lower < price < upper
                a0                        price >= upper

    a0 + a1 * p = liquidity * 10 ** (0.5 * d) / 10 ** d0 * price_float ** 0.5 - \
              k / upper_sqrt * liquidity / 10 ** d0 + \
              liquidity*  price_float ** 0.5 / 10 ** d1 / 10 ** (0.5 * d) - \
              lower_sqrt / k * price_float * liquidity / 10 ** d1


    if 1 base
    SqrtPrice = k * p**0.5 / (10 ** (d/2))

    net_value = a0 * p                         price <= lower, a0 is constant
                a0 * p + a1                    lower < price < upper
                a1                             price >= upper, a1 is constant

    a0 * p + a1 = liquidity * price_float ** 0.5 * 10 ** (0.5 * d) / 10 ** d0 - \
                  k / upper_sqrt * liquidity * price_float / 10 ** d0 + \
                  liquidity * price_float ** 0.5 / 10 ** d1 / 10 ** (0.5 * d) - \
                  lower_sqrt / k * liquidity / 10 ** d1



    a0 + p * a1 =  Liquidity / 10**(d/2) / p**(1/2) + Liquidity * p**(1.5) / 10 ** (1.5*d) -
                   Liquidity * lower_price_sqrtX96 * p / 2**96 / 10**d
    """
    k = 2 ** 96
    d = d0 - d1
    if is_0_base:
        if price <= lower_price:
            delta = liquidity / 2 ** 96 / 10 ** d1 * (sqrtB - sqrtA)
            gamma = 0
        elif lower_price < price < upper_price:
            m = 10 ** (0.5 * d)
            delta = liquidity * (0.5 * m / price ** 0.5 / 10 ** d0 + \
                                 0.5 / 10 ** d1 / m / price ** 0.5 - \
                                 sqrtA / k / 10 ** d1)
            gamma = -0.25 * liquidity / price ** 1.5 * (m / 10 ** d0 + 1 / 10 ** d1 / m)
        else:
            delta = 0
            gamma = 0
    else:
        if price <= lower_price:
            delta = liquidity / 10 ** d0 * (k / sqrtA - k / sqrtB)
            gamma = 0
        elif lower_price < price < upper_price:
            m = 10 ** (0.5 * d)
            delta = liquidity * (0.5 * m / price ** 0.5 / 10 ** d0 + \
                                 0.5 / 10 ** d1 / m / price ** 0.5 - \
                                 k / sqrtB / 10 ** d0)
            gamma = -0.25 * liquidity / price ** 1.5 * (m / 10 ** d0 + 1 / m / 10 ** d1)
        else:
            delta = 0
            gamma = 0

    return delta, gamma
