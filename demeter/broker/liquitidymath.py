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
def get_amount0(sqrtA: Decimal, sqrtB: Decimal, liquidity: Decimal, decimals: int) -> Decimal:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)
    amount0 = ((liquidity * 2 ** 96 * (sqrtB - sqrtA) / sqrtB / sqrtA) / 10 ** decimals)
    return amount0


def get_amount1(sqrtA: Decimal, sqrtB: Decimal, liquidity: Decimal, decimals: int) -> Decimal:
    if sqrtA > sqrtB:
        (sqrtA, sqrtB) = (sqrtB, sqrtA)
    amount1 = liquidity * (sqrtB - sqrtA) / 2 ** 96 / 10 ** decimals
    return Decimal(amount1)


def get_amounts(tick: int, tickA: int, tickB: int, liquidity: int, decimal0: int, decimal1: int) -> \
        (Decimal, Decimal):
    sqrt = Decimal(1.0001 ** (tick / 2) * (2 ** 96))
    sqrtA = Decimal(1.0001 ** (tickA / 2) * (2 ** 96))
    sqrtB = Decimal(1.0001 ** (tickB / 2) * (2 ** 96))

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


def get_liquidity(tick: int, tickA: int, tickB: int, amount0: Decimal, amount1: Decimal, decimal0: int,
                  decimal1: int) -> Decimal:
    sqrt = Decimal(1.0001 ** (tick / 2) * (2 ** 96))
    sqrtA = Decimal(1.0001 ** (tickA / 2) * (2 ** 96))
    sqrtB = Decimal(1.0001 ** (tickB / 2) * (2 ** 96))

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
