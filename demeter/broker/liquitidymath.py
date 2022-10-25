from decimal import Decimal

# -*- coding: utf-8 -*-
"""
Created on Mon Jun 14 18:53:09 2021

@author: JNP
"""

'''liquitidymath'''
'''Python library to emulate the calculations done in liquiditymath.sol of UNI_V3 peryphery contract'''

# sqrtP: format X96 = int(1.0001**(tick/2)*(2**96))
# liquidity: int
# sqrtA = price for lower tick
# sqrtB = price for upper tick
'''get_amounts function'''


# Use 'get_amounts' function to calculate amounts as a function of liquitidy and price range
def get_amount0(sqrtA: int, sqrtB: int, liquidity: int, decimals: int) -> Decimal:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)
    amount0 = (Decimal(liquidity * 2 ** 96 * (sqrtB - sqrtA)) / sqrtB / sqrtA) / 10 ** decimals
    return amount0


def get_amount1(sqrtA: int, sqrtB: int, liquidity: int, decimals: int) -> Decimal:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)
    amount1 = Decimal(liquidity * (sqrtB - sqrtA)) / 2 ** 96 / 10 ** decimals
    return amount1


def get_sqrt(tick):
    return Decimal(1.0001 ** (tick / 2) * (2 ** 96))


def get_amounts(sqrt_price_x96: int, tickA: int, tickB: int, liquidity: int, decimal0: int, decimal1: int) -> \
        (Decimal, Decimal):
    sqrt = sqrt_price_x96
    sqrtA = getSqrtRatioAtTick(tickA)
    sqrtB = getSqrtRatioAtTick(tickB)

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


'''get token amounts relation'''


# Use this formula to calculate amount of t0 based on amount of t1 (required before calculate liquidity)
# relation = t1/t0
def amounts_relation(tick: int, tickA: int, tickB: int, decimals0: int, decimals1: int) -> Decimal:
    sqrt = (1.0001 ** tick / 10 ** (decimals1 - decimals0)) ** (1 / 2)
    sqrtA = (1.0001 ** tickA / 10 ** (decimals1 - decimals0)) ** (1 / 2)
    sqrtB = (1.0001 ** tickB / 10 ** (decimals1 - decimals0)) ** (1 / 2)

    if sqrt == sqrtA or sqrt == sqrtB:
        relation = 0

    relation = (sqrt - sqrtA) / ((1 / sqrt) - (1 / sqrtB))
    return relation


'''get_liquidity function'''


# Use 'get_liquidity' function to calculate liquidity as a function of amounts and price range
def get_liquidity0(sqrtA: Decimal, sqrtB: Decimal, amount0: Decimal, decimals: int) -> Decimal:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)

    liquidity = amount0 / ((2 ** 96 * (sqrtB - sqrtA) / sqrtB / sqrtA) / 10 ** decimals)
    return liquidity


def get_liquidity1(sqrtA: Decimal, sqrtB: Decimal, amount1: Decimal, decimals: int) -> Decimal:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)

    liquidity = amount1 / ((sqrtB - sqrtA) / 2 ** 96 / 10 ** decimals)
    return liquidity


def get_liquidity(tick: int, tickA: int, tickB: int,
                  amount0: Decimal, amount1: Decimal,
                  decimal0: int, decimal1: int) -> Decimal:
    sqrt = get_sqrt(tick)
    sqrtA = get_sqrt(tickA)
    sqrtB = get_sqrt(tickB)

    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)

    if sqrt <= sqrtA:
        liquidity0 = get_liquidity0(sqrtA, sqrtB, amount0, decimal0)
        return liquidity0
    elif sqrtB > sqrt > sqrtA:
        liquidity0 = get_liquidity0(sqrt, sqrtB, amount0, decimal0)
        liquidity1 = get_liquidity1(sqrtA, sqrt, amount1, decimal1)
        liquidity = liquidity0 if liquidity0 < liquidity1 else liquidity1
        return liquidity
    else:
        liquidity1 = get_liquidity1(sqrtA, sqrtB, amount1, decimal1)
        return liquidity1


def mulDiv(a: int, b: int, denominator: int) -> int:
    return a * b // denominator


def getLiquidityForAmount0(sqrtA: int, sqrtB: int, amount: int) -> int:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)

    intermediate = mulDiv(sqrtA, sqrtB, 2 ** 96)
    return mulDiv(amount, intermediate, sqrtB - sqrtA)


def getLiquidityForAmount1(sqrtA: int, sqrtB: int, amount: int) -> int:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)

    return mulDiv(amount, 2 ** 96, sqrtB - sqrtA)


def to_wei(amount, decimals) -> int:
    return int(amount * 10 ** decimals)


def getLiquidity(sqrt_price_x96: int, tickA: int, tickB: int,
                 amount0: Decimal, amount1: Decimal,
                 decimal0: int, decimal1: int) -> Decimal:
    sqrt = sqrt_price_x96
    sqrtA = getSqrtRatioAtTick(tickA)
    sqrtB = getSqrtRatioAtTick(tickB)

    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)
    amount0wei: int = to_wei(amount0, decimal0)
    amount1wei: int = to_wei(amount1, decimal1)
    if sqrt <= sqrtA:
        liquidity0 = getLiquidityForAmount0(sqrtA, sqrtB, amount0wei)
        return liquidity0
    elif sqrtB > sqrt > sqrtA:
        liquidity0 = getLiquidityForAmount0(sqrt, sqrtB, amount0wei)
        liquidity1 = getLiquidityForAmount1(sqrtA, sqrt, amount1wei)
        liquidity = liquidity0 if liquidity0 < liquidity1 else liquidity1
        return liquidity
    else:
        liquidity1 = getLiquidityForAmount1(sqrtA, sqrtB, amount1wei)
        return liquidity1


def getSqrtRatioAtTick(tick: int) -> int:
    absTick = tick if tick >= 0 else -tick
    assert absTick <= 887272

    # 这些魔数分别表示 1/sqrt(1.0001)^1, 1/sqrt(1.0001)^2, 1/sqrt(1.0001)^4....
    ratio: int = 0xfffcb933bd6fad37aa2d162d1a594001 if absTick & 0x1 != 0 else 0x100000000000000000000000000000000
    if absTick & 0x2 != 0: ratio = (ratio * 0xfff97272373d413259a46990580e213a) >> 128
    if absTick & 0x4 != 0: ratio = (ratio * 0xfff2e50f5f656932ef12357cf3c7fdcc) >> 128
    if absTick & 0x8 != 0: ratio = (ratio * 0xffe5caca7e10e4e61c3624eaa0941cd0) >> 128
    if absTick & 0x10 != 0: ratio = (ratio * 0xffcb9843d60f6159c9db58835c926644) >> 128
    if absTick & 0x20 != 0: ratio = (ratio * 0xff973b41fa98c081472e6896dfb254c0) >> 128
    if absTick & 0x40 != 0: ratio = (ratio * 0xff2ea16466c96a3843ec78b326b52861) >> 128
    if absTick & 0x80 != 0: ratio = (ratio * 0xfe5dee046a99a2a811c461f1969c3053) >> 128
    if absTick & 0x100 != 0: ratio = (ratio * 0xfcbe86c7900a88aedcffc83b479aa3a4) >> 128
    if absTick & 0x200 != 0: ratio = (ratio * 0xf987a7253ac413176f2b074cf7815e54) >> 128
    if absTick & 0x400 != 0: ratio = (ratio * 0xf3392b0822b70005940c7a398e4b70f3) >> 128
    if absTick & 0x800 != 0: ratio = (ratio * 0xe7159475a2c29b7443b29c7fa6e889d9) >> 128
    if absTick & 0x1000 != 0: ratio = (ratio * 0xd097f3bdfd2022b8845ad8f792aa5825) >> 128
    if absTick & 0x2000 != 0: ratio = (ratio * 0xa9f746462d870fdf8a65dc1f90e061e5) >> 128
    if absTick & 0x4000 != 0: ratio = (ratio * 0x70d869a156d2a1b890bb3df62baf32f7) >> 128
    if absTick & 0x8000 != 0: ratio = (ratio * 0x31be135f97d08fd981231505542fcfa6) >> 128
    if absTick & 0x10000 != 0: ratio = (ratio * 0x9aa508b5b7a84e1c677de54f3e99bc9) >> 128
    if absTick & 0x20000 != 0: ratio = (ratio * 0x5d6af8dedb81196699c329225ee604) >> 128
    if absTick & 0x40000 != 0: ratio = (ratio * 0x2216e584f5fa1ea926041bedfe98) >> 128
    if absTick & 0x80000 != 0: ratio = (ratio * 0x48a170391f7dc42444e8fa2) >> 128

    if tick > 0:
        # type(uint256).max
        ratio = int(115792089237316195423570985008687907853269984665640564039457584007913129639935 // ratio)

    # this divides by 1<<32 rounding up to go from a Q128.128 to a Q128.96.
    # we then downcast because we know the result always fits within 160 bits due to our tick input constraint
    # we round up in the division so getTickAtSqrtRatio of the output price is always consistent
    sqrtPriceX96 = (ratio >> 32) + (0 if ratio % (1 << 32) == 0 else 1)
    return sqrtPriceX96
