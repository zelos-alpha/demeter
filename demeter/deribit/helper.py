import decimal
from datetime import datetime
from decimal import Decimal
from typing import Any

import pandas as pd

from demeter.utils import console_text


def round_decimal(num: Any, exponent: int) -> Decimal:
    """
    | Adjusting the number to a specific number of digits, eg:
    | self.assertEqual(Decimal("123500000"), round_decimal("123456789", 5))
    | self.assertEqual(Decimal("123000000"), round_decimal("123456789", 6))
    | self.assertEqual(Decimal("120"), round_decimal("123", 1))
    | self.assertEqual(Decimal("123"), round_decimal("123", 0))
    | self.assertEqual(Decimal("1.2"), round_decimal("1.23456789", -1))
    | self.assertEqual(Decimal("1.2346"), round_decimal("1.23456789", -4))


    :param num: number in any type, such as int/float/Decimal/str
    :type num: Any
    :param exponent: specific number of digits,
    :type exponent: int
    """
    if not isinstance(num, Decimal):
        num = Decimal(num)
    val = num.quantize(Decimal(f"1e{exponent}"), rounding=decimal.ROUND_HALF_UP)
    if exponent > 0:
        val = val.quantize(Decimal(0))
    return val


def position_to_df(positions) -> pd.DataFrame:
    pos_dict = {
        "instrument_name": [],
        "expiry_time": [],
        "strike_price": [],
        "type": [],
        "amount": [],
        "avg_buy_price": [],
        "buy_amount": [],
        "avg_sell_price": [],
        "sell_amount": [],
    }
    for k, v in positions.items():
        pos_dict["instrument_name"].append(console_text.format_value(v.instrument_name))
        pos_dict["expiry_time"].append(console_text.format_value(v.expiry_time))
        pos_dict["strike_price"].append(console_text.format_value(v.strike_price))
        pos_dict["type"].append(console_text.format_value(v.type))
        pos_dict["amount"].append(console_text.format_value(v.amount))
        pos_dict["avg_buy_price"].append(console_text.format_value(v.avg_buy_price))
        pos_dict["buy_amount"].append(console_text.format_value(v.buy_amount))
        pos_dict["avg_sell_price"].append(console_text.format_value(v.avg_sell_price))
        pos_dict["sell_amount"].append(console_text.format_value(v.sell_amount))

    return pd.DataFrame(pos_dict)


def decode_instrument(instrument_name):
    split = instrument_name.split("-")
    type_ = "PUT" if split[3] == "P" else "CALL"
    k = int(split[2])
    exec_time = datetime.strptime(split[1] + " 08:00:00", "%d%b%y %H:%M:%S")
    token = split[0]
    return token, exec_time, k, type_
