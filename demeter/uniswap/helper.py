import math
from decimal import Decimal, getcontext
from typing import Tuple, NamedTuple

from .liquitidy_math import get_sqrt_ratio_at_tick, get_liquidity, get_amounts
from .. import DemeterError

Q96 = Decimal(2**96)
SQRT_1p0001 = math.sqrt(Decimal(1.0001))
getcontext().prec = 35  # default is 28, 33 is good enough for 3000
MIN_ERROR = Decimal("1e-31")


def _from_x96(number: int) -> Decimal:
    """
    decimal divide 2 ** 96

    :param number: sqrted x96 price
    :return: sqrted price
    """
    return Decimal(number) / Q96


def _to_x96(sqrt_price: Decimal) -> int:
    """
    decimal multiple 2 ** 96

    :param sqrt_price: price in base unit
    :return: result
    """
    if not isinstance(sqrt_price, Decimal):
        sqrt_price = Decimal(sqrt_price)
    return int(sqrt_price * Q96)


def sqrt_price_x96_to_base_unit_price(
    sqrt_price_x96, token_0_decimal: int, token_1_decimal: int, is_token0_quote: bool
) -> Decimal:
    """
    convert sqrt x96 price to decimal

    :param sqrt_price_x96: sqrt x96 price
    :param token_0_decimal: decimal of token 0
    :param token_1_decimal: decimal of token 1
    :param is_token0_quote: is token 0 the quote token
    :return: price in base unit, e.g. 1234.56 eth/usdc
    """
    sqrt_price = _from_x96(sqrt_price_x96)
    pool_price = sqrt_price**2 * Decimal(10 ** (token_0_decimal - token_1_decimal))

    return Decimal(1 / pool_price) if is_token0_quote else pool_price


def base_unit_price_to_sqrt_price_x96(
    price: Decimal, token_0_decimal: int, token_1_decimal: int, is_token0_quote: bool
) -> int:
    """
    convert quote price to sqrt

    :param price: price in base/quote
    :param token_0_decimal: token0 decimal
    :param token_1_decimal: token1 decimal
    :param is_token0_quote: token 0 is quote token
    :return: sqrt price x96
    """
    # quote price->add decimal pool price->sqrt_price ->ticker

    price = 1 / price if is_token0_quote else price
    atomic_unit_price = price / Decimal(10 ** (token_0_decimal - token_1_decimal))
    sqrt_price = Decimal.sqrt(atomic_unit_price)
    return _to_x96(sqrt_price)


# can round by spacing?
def sqrt_price_x96_to_tick(sqrt_price_x96: int) -> int:
    """
    convert sqrt_priceX96 to tick

    :param sqrt_price_x96: sqrt x96 price
    :return: tick price
    """
    sqrt_price = _from_x96(sqrt_price_x96)
    return _sqrt_price_to_tick(sqrt_price)


def _sqrt_price_to_tick(sqrt_price: Decimal) -> int:
    """
    pool price to tick price

    :param sqrt_price: sqrt price
    :return: tick price
    """
    return int(math.log(sqrt_price, SQRT_1p0001))


def tick_to_sqrt_price_x96(tick: int) -> int:
    """
    convert tick data to sqrt X96 price

    :param tick: tick price
    :return: sqrt x96 price
    """
    return get_sqrt_ratio_at_tick(tick)


def tick_to_base_unit_price(tick: int, token_0_decimal: int, token_1_decimal: int, is_token0_quote: bool):
    """
    get quote price from tick price

    :param tick: tick data
    :param token_0_decimal: token0 decimal
    :param token_1_decimal: token1 decimal
    :param is_token0_quote: quote on token0
    :return: quote price
    """
    sqrt_price_x96 = get_sqrt_ratio_at_tick(tick)
    atomic_unit_price = _from_x96(sqrt_price_x96) ** 2
    pool_price = atomic_unit_price * Decimal(10 ** (token_0_decimal - token_1_decimal))
    return Decimal(1 / pool_price) if is_token0_quote else pool_price


def base_unit_price_to_tick(price: Decimal, token_0_decimal: int, token_1_decimal: int, is_token0_quote: bool) -> int:
    """
    quote price to tick price

    :param price: price in base unit, e.g. 1234.56 eth/usdc
    :param token_0_decimal: token0 decimal
    :param token_1_decimal: token1 decimal
    :param is_token0_quote: token 0 is quote token
    :return: tick price
    """

    # quote price->add decimal pool price->sqrt_price ->tick
    price = 1 / price if is_token0_quote else price
    atomic_unit_price = price / Decimal(10 ** (token_0_decimal - token_1_decimal))
    sqrt_price = Decimal.sqrt(atomic_unit_price)
    return _sqrt_price_to_tick(sqrt_price)


def from_atomic_unit(atomic_unit_amount: int, decimal: int) -> Decimal:
    """
    Convert token amount to wei

    :param atomic_unit_amount: token amount
    :param decimal: decimal of token
    :return: token amount in base unit
    """
    return Decimal(int(atomic_unit_amount)) / Decimal(10**decimal)


def get_delta_gamma(
    lower_price: float,
    upper_price: float,
    price: float,
    liquidity: int,
    decimal0: int,
    decimal1: int,
    is_token0_quote: bool,
) -> Tuple[Decimal, Decimal]:
    """
    get delta gamma

    :param lower_price: lower price
    :param upper_price: upper price
    :param price: price
    :param liquidity: liquidity
    :param decimal0: decimal 0
    :param decimal1: decimal 1
    :param is_token0_quote: check if token 0 is quote
    :return: delta and gamma
    """
    lower_price_sqrt_x96 = base_unit_price_to_sqrt_price_x96(Decimal(lower_price), decimal0, decimal1, is_token0_quote)
    upper_price_sqrt_x96 = base_unit_price_to_sqrt_price_x96(Decimal(upper_price), decimal0, decimal1, is_token0_quote)
    if lower_price_sqrt_x96 > upper_price_sqrt_x96:
        (lower_price_sqrt_x96, upper_price_sqrt_x96) = (
            upper_price_sqrt_x96,
            lower_price_sqrt_x96,
        )
    return get_delta_gamma_sqrt_x96(
        lower_price,
        lower_price_sqrt_x96,
        upper_price,
        upper_price_sqrt_x96,
        price,
        liquidity,
        decimal0,
        decimal1,
        is_token0_quote,
    )


def get_delta_gamma_sqrt_x96(
    lower_price,
    sqrtA: int,
    upper_price,
    sqrtB: int,
    price,
    liquidity: int,
    d0: int,
    d1: int,
    is_token0_quote: bool,
) -> Tuple[Decimal, Decimal]:
    """
    Get delta gamma in sqrtX96 price

    """
    """
    Delta is calculated by integrating net worth, and gamma is calculated by integrating delta,
    Therefore, the most important thing is to find the calculation formula of the net value (with tick range, price, and liquidity as parameters),
    and then derive the formula after integration

    The following comment indicates how to calculate net value.

    * a: amount
    * p: decimal price of base token


    k = 2 ** 96
    a0 = k * (10**(-d)) * Liquidity * (1/SqrtPrice - 1/upper_price_sqrtX96)
    a1= Liquidity / k / 10**d * (SqrtPrice - lower_price_sqrtX96)


    if 0 quote:
    SqrtPrice=k / (10 ** (d/2)) / (p**0.5)
    net_value = a1 * p                    price <= lower, a1 is constant
                a0 + a1 * p               lower < price < upper
                a0                        price >= upper, a0 is constant

    a0 + a1 * p = liquidity * 10 ** (0.5 * d) / 10 ** d0 * price_float ** 0.5 - \
              k / upper_sqrt * liquidity / 10 ** d0 + \
              liquidity*  price_float ** 0.5 / 10 ** d1 / 10 ** (0.5 * d) - \
              lower_sqrt / k * price_float * liquidity / 10 ** d1


    if 1 quote
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
    k = 2**96
    d = d0 - d1
    if is_token0_quote:
        if price <= lower_price:
            delta = liquidity / 2**96 / 10**d1 * (sqrtB - sqrtA)
            gamma = 0
        elif lower_price < price < upper_price:
            m = 10 ** (0.5 * d)
            delta = liquidity * (0.5 * m / price**0.5 / 10**d0 + 0.5 / 10**d1 / m / price**0.5 - sqrtA / k / 10**d1)
            gamma = -0.25 * liquidity / price**1.5 * (m / 10**d0 + 1 / 10**d1 / m)
        else:
            delta = 0
            gamma = 0
    else:
        if price <= lower_price:
            delta = liquidity / 10**d0 * (k / sqrtA - k / sqrtB)
            gamma = 0
        elif lower_price < price < upper_price:
            m = 10 ** (0.5 * d)
            delta = liquidity * (0.5 * m / price**0.5 / 10**d0 + 0.5 / 10**d1 / m / price**0.5 - k / sqrtB / 10**d0)
            gamma = -0.25 * liquidity / price**1.5 * (m / 10**d0 + 1 / m / 10**d1)
        else:
            delta = 0
            gamma = 0

    return delta, gamma


def get_swap_value(swap_from_token_val, swap_to_token_val, fee_rate, final_ratio):
    # if needed value rate is K, calculate how many value to swap, need deduct swap fee
    # final_ratio = final_from_token_val / final_to_token_value

    # Vfrom + Vto = Vfrom_after  + Vto_after + Vswap * fee_rate
    # Vfrom - Vswap = Vfrom_after
    # Vto + Vswap = Vto_after + Vswap * fee_rate
    # Vfrom_after / Vto_after = final_ratio

    # known value: Vfrom, Vto, fee_rate, final_ratio
    # unknow value: Vfrom_after, Vto_after
    # wanted value: Vswap
    return (swap_from_token_val - swap_to_token_val * final_ratio) / (final_ratio - final_ratio * fee_rate + 1)


def get_swap_value_with_part_balance_used(
    swap_from_token_val, swap_to_token_val, total_val_after, fee_rate, final_ratio
):
    # Given current balance of A and B, and suppose you want to invest total_val_after in lp,
    # Ratio of a and b after swap is known
    # This function will calculate how much to swap,

    # Vfrom + Vto = V
    # Vswap * fee_rate + Vfrom_after + Vto_after = total_val_after
    # Vfrom_after / Vto_after = final_ratio
    # Vto + Vswap * (1 - fee_rate) = Vto_after

    if total_val_after > swap_from_token_val + swap_to_token_val:
        raise DemeterError("Target value exceed your balance")
    swap_value = (total_val_after - final_ratio * swap_to_token_val - swap_to_token_val) / (
        final_ratio - final_ratio * fee_rate + 1
    )
    total_val_after_no_fee = total_val_after - swap_value * fee_rate
    swap_to_token_val_after = total_val_after_no_fee / (final_ratio + 1)
    return total_val_after_no_fee - swap_to_token_val_after, swap_to_token_val_after, swap_value


def nearest_usable_tick(tick: int, tick_spacing: int):
    """
    Returns the closest tick that is nearest a given tick and usable for the given tick spacing
    copied from: https://github.com/Uniswap/v3-sdk/blob/main/src/utils/nearestUsableTick.ts
    :param tick: the target tick
    :param tick_spacing: the spacing of the pool
    :return:
    """
    rounded = round(tick / tick_spacing) * tick_spacing
    if rounded < -887272:
        return rounded + tick_spacing
    elif rounded > 887272:
        return rounded - tick_spacing
    else:
        return rounded


class TickResult(NamedTuple):
    final_price: Decimal
    rate: Decimal
    center_tick: int
    upper: int
    lower: int
    upper_delta: int
    lower_delta: int


def find_tick_range_at_rate(
    price: Decimal,
    rate: Decimal,
    tick_spacing: int,
    decimal0: int,
    decimal1: int,
    is_0_quote: bool,
    error=Decimal("0.00001"),
):
    """
    Find iteratively, for a specific price, what tick range can make the quantities of two tokens exactly equal to a specific ratio.
    :param price: center price, it will be trimed according to tick space
    :param rate: the rate you want. amount1/amount0
    :param tick_spacing: tick spacing of the pool
    :param decimal0: decimal 0
    :param decimal1: decimal 1
    :param is_0_quote: token 0 is the quote token
    :param error: error of rate
    :return: An object contains new price, actual rate, and tick range, if can not find a proper tick range, return none, you can make error larger
    """
    center_tick = base_unit_price_to_tick(price, decimal0, decimal1, is_0_quote)
    center_tick = nearest_usable_tick(center_tick, tick_spacing)
    idx = tick_spacing

    sqrt_price = tick_to_sqrt_price_x96(center_tick)
    price = sqrt_price_x96_to_base_unit_price(sqrt_price, decimal0, decimal1, is_0_quote)
    if is_0_quote:
        token0_amount, token1_amount = price, Decimal(1)
    else:
        token1_amount, token0_amount = price, Decimal(1)

    rate = rate.quantize(error)

    while center_tick + idx <= 887272:
        print("trying", center_tick + idx)
        upper = center_tick + idx
        lower_idx = idx
        val1, val0 = 0, 1
        while val1 / val0 <= rate:
            lower_idx += tick_spacing
            lower = center_tick - lower_idx
            liq = get_liquidity(sqrt_price, lower, upper, token0_amount, token1_amount, decimal0, decimal1)
            amount0, amount1 = get_amounts(sqrt_price, lower, upper, liq, decimal0, decimal1)
            if is_0_quote:
                val0, val1 = amount0, amount1 * price
            else:
                val0, val1 = amount0 * price, amount1

            if (val1 / val0).quantize(error) == rate:
                return TickResult(
                    final_price=tick_to_base_unit_price(center_tick, decimal0, decimal1, is_0_quote),
                    rate=val1 / val0,
                    center_tick=center_tick,
                    upper=upper,
                    lower=lower,
                    upper_delta=upper - center_tick,
                    lower_delta=lower - center_tick,
                )
        idx += tick_spacing
    return None
