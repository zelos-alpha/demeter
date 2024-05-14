import math
from decimal import Decimal

import pandas as pd


def calc_twap_price(prices: pd.Series) -> Decimal:
    """
    Calc TWAP(time weighted average price) as uniswap oracle.
    :param prices: given price array.
    :param prices: Series
    :return: TWAP price
    :rtype: Decimal
    """
    logged = prices.apply(lambda x: math.log(x, 1.0001))
    logged_sum = logged.sum()
    power = logged_sum / len(prices)
    avg_price = math.pow(1.0001, power)

    return Decimal(avg_price)
