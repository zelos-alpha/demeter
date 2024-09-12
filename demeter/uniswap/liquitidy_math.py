import math
from decimal import Decimal

# -*- coding: utf-8 -*-
"""
!!! IMPORTANT 

this module is developed and enhanced from active-strategy-framework of GammaStrategies
source code: https://github.com/GammaStrategies/active-strategy-framework/blob/main/UNI_v3_funcs.py

Original author information: 
=============================================

Created on Mon Jun 14 18:53:09 2021

@author: JNP
"""

"""liquitidymath"""
"""Python library to emulate the calculations done in liquiditymath.sol of UNI_V3 peryphery contract"""

# sqrtP: format X96 = int(1.0001**(tick/2)*(2**96))
# liquidity: int
# sqrtA = price for lower tick
# sqrtB = price for upper tick
"""get_amounts function"""


# Use 'get_amounts' function to calculate amounts as a function of liquitidy and price range
def get_amount0(sqrtA: int, sqrtB: int, liquidity: int, decimals: int) -> Decimal:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)
    amount0 = (Decimal(liquidity * 2**96 * (sqrtB - sqrtA)) / sqrtB / sqrtA) / 10**decimals
    return amount0


def get_amount1(sqrtA: int, sqrtB: int, liquidity: int, decimals: int) -> Decimal:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)
    amount1 = Decimal(liquidity * (sqrtB - sqrtA)) / 2**96 / 10**decimals
    return amount1


def get_sqrt(tick: int):
    return Decimal(1.0001 ** (tick / 2) * (2**96))


def get_amounts(
    sqrt_price_x96: int,
    tickA: int,
    tickB: int,
    liquidity: int,
    decimal0: int,
    decimal1: int,
) -> (Decimal, Decimal):
    sqrt = sqrt_price_x96
    sqrtA = get_sqrt_ratio_at_tick(tickA)
    sqrtB = get_sqrt_ratio_at_tick(tickB)

    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)

    if sqrt <= sqrtA:
        amount0 = get_amount0(sqrtA, sqrtB, liquidity, decimal0)
        return amount0, Decimal(0)
    elif sqrtB > sqrt > sqrtA:
        amount0 = get_amount0(sqrt, sqrtB, liquidity, decimal0)
        amount1 = get_amount1(sqrtA, sqrt, liquidity, decimal1)
        return amount0, amount1
    else:
        amount1 = get_amount1(sqrtA, sqrtB, liquidity, decimal1)
        return Decimal(0), amount1


"""get token amounts relation"""


# Use this formula to calculate amount of t0 based on amount of t1 (required before calculate liquidity)
# relation = t1/t0
def amounts_relation(tick: int, tickA: int, tickB: int, decimals0: int, decimals1: int) -> Decimal:
    sqrt = (1.0001**tick / 10 ** (decimals1 - decimals0)) ** (1 / 2)
    sqrtA = (1.0001**tickA / 10 ** (decimals1 - decimals0)) ** (1 / 2)
    sqrtB = (1.0001**tickB / 10 ** (decimals1 - decimals0)) ** (1 / 2)

    if sqrt == sqrtA or sqrt == sqrtB:
        relation = 0

    relation = (sqrt - sqrtA) / ((1 / sqrt) - (1 / sqrtB))
    return relation


"""get_liquidity function"""


def mul_div(a: int, b: int, denominator: int) -> int:
    """
    this function is very long in contract. but It's because max length in solidity is limited.

    But python has unlimit integer.

    ensure all the parameter is int !
    """
    return a * b // denominator


def get_liquidity_for_amount0(sqrtA: int, sqrtB: int, amount: int) -> int:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)

    intermediate = mul_div(sqrtA, sqrtB, 2**96)
    return mul_div(amount, intermediate, sqrtB - sqrtA)


def get_liquidity_for_amount1(sqrtA: int, sqrtB: int, amount: int) -> int:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)

    return mul_div(amount, 2**96, sqrtB - sqrtA)


def to_wei(amount, decimals) -> int:
    return int(amount * 10**decimals)


def get_liquidity(
    sqrt_price_x96: int,
    tickA: int,
    tickB: int,
    amount0: Decimal,
    amount1: Decimal,
    decimal0: int,
    decimal1: int,
) -> int:
    sqrt = sqrt_price_x96
    sqrtA = get_sqrt_ratio_at_tick(tickA)
    sqrtB = get_sqrt_ratio_at_tick(tickB)

    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)
    amount0wei: int = to_wei(amount0, decimal0)
    amount1wei: int = to_wei(amount1, decimal1)
    if sqrt <= sqrtA:
        liquidity0 = get_liquidity_for_amount0(sqrtA, sqrtB, amount0wei)
        return liquidity0
    elif sqrtB > sqrt > sqrtA:
        liquidity0 = get_liquidity_for_amount0(sqrt, sqrtB, amount0wei)
        liquidity1 = get_liquidity_for_amount1(sqrtA, sqrt, amount1wei)
        liquidity = liquidity0 if liquidity0 < liquidity1 else liquidity1
        return liquidity
    else:
        liquidity1 = get_liquidity_for_amount1(sqrtA, sqrtB, amount1wei)
        return liquidity1


def get_sqrt_ratio_at_tick(tick: int) -> int:
    """
    (sqrt(1.0001) ** tick) * (2**96)
    """
    tick = int(tick)
    abs_tick = tick if tick >= 0 else -tick
    assert abs_tick <= 887272

    # Those magic number stands for 1/sqrt(1.0001)^1, 1/sqrt(1.0001)^2, 1/sqrt(1.0001)^4....
    ratio: int = 0xFFFCB933BD6FAD37AA2D162D1A594001 if abs_tick & 0x1 != 0 else 0x100000000000000000000000000000000
    if abs_tick & 0x2 != 0:
        ratio = (ratio * 0xFFF97272373D413259A46990580E213A) >> 128
    if abs_tick & 0x4 != 0:
        ratio = (ratio * 0xFFF2E50F5F656932EF12357CF3C7FDCC) >> 128
    if abs_tick & 0x8 != 0:
        ratio = (ratio * 0xFFE5CACA7E10E4E61C3624EAA0941CD0) >> 128
    if abs_tick & 0x10 != 0:
        ratio = (ratio * 0xFFCB9843D60F6159C9DB58835C926644) >> 128
    if abs_tick & 0x20 != 0:
        ratio = (ratio * 0xFF973B41FA98C081472E6896DFB254C0) >> 128
    if abs_tick & 0x40 != 0:
        ratio = (ratio * 0xFF2EA16466C96A3843EC78B326B52861) >> 128
    if abs_tick & 0x80 != 0:
        ratio = (ratio * 0xFE5DEE046A99A2A811C461F1969C3053) >> 128
    if abs_tick & 0x100 != 0:
        ratio = (ratio * 0xFCBE86C7900A88AEDCFFC83B479AA3A4) >> 128
    if abs_tick & 0x200 != 0:
        ratio = (ratio * 0xF987A7253AC413176F2B074CF7815E54) >> 128
    if abs_tick & 0x400 != 0:
        ratio = (ratio * 0xF3392B0822B70005940C7A398E4B70F3) >> 128
    if abs_tick & 0x800 != 0:
        ratio = (ratio * 0xE7159475A2C29B7443B29C7FA6E889D9) >> 128
    if abs_tick & 0x1000 != 0:
        ratio = (ratio * 0xD097F3BDFD2022B8845AD8F792AA5825) >> 128
    if abs_tick & 0x2000 != 0:
        ratio = (ratio * 0xA9F746462D870FDF8A65DC1F90E061E5) >> 128
    if abs_tick & 0x4000 != 0:
        ratio = (ratio * 0x70D869A156D2A1B890BB3DF62BAF32F7) >> 128
    if abs_tick & 0x8000 != 0:
        ratio = (ratio * 0x31BE135F97D08FD981231505542FCFA6) >> 128
    if abs_tick & 0x10000 != 0:
        ratio = (ratio * 0x9AA508B5B7A84E1C677DE54F3E99BC9) >> 128
    if abs_tick & 0x20000 != 0:
        ratio = (ratio * 0x5D6AF8DEDB81196699C329225EE604) >> 128
    if abs_tick & 0x40000 != 0:
        ratio = (ratio * 0x2216E584F5FA1EA926041BEDFE98) >> 128
    if abs_tick & 0x80000 != 0:
        ratio = (ratio * 0x48A170391F7DC42444E8FA2) >> 128

    if tick > 0:
        # type(uint256).max
        ratio = int(115792089237316195423570985008687907853269984665640564039457584007913129639935 // ratio)

    # this divides by 1<<32 rounding up to go from a Q128.128 to a Q128.96.
    # we then downcast because we know the result always fits within 160 bits due to our tick input constraint
    # we round up in the division so getTickAtSqrtRatio of the output price is always consistent
    sqrt_price_x96 = (ratio >> 32) + (0 if ratio % (1 << 32) == 0 else 1)
    return sqrt_price_x96


def estimate_ratio(tick, lower_tick, upper_tick):
    """
    Emulate amount ratio of token 0,1 before adding to liquidity.
    The ratio should multiple 10 ** (decimal1-decimal0)

    :param tick: current tick
    :param lower_tick: lower tick
    :param upper_tick: upper tick
    :return:
    """
    T = math.sqrt(1.0001)
    if not lower_tick < tick < upper_tick:
        from demeter import DemeterError

        raise DemeterError("tick should in tick range")
    ratio = (T**upper_tick - T**tick) / (T**tick * T**upper_tick * (T**tick - T**lower_tick))
    return ratio


