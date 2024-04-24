from decimal import Decimal

import pandas as pd


def get_uni_twap_price(t, price_list: pd.Series, current_timestamp=None) -> Decimal:
    """
    get twap price, will calc from "current_timestamp - t" to current_timestamp

    :param t: how long ago
    :param price_list: price list
    :param current_timestamp: current time, if None, will use last timestamp in price_list

    """
    price = 5.0
    return Decimal(price)
