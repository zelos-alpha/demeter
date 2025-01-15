import decimal
import json
import logging
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any, List

import pandas as pd

from demeter import MarketTypeEnum
from demeter.data import CacheManager
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


def order_converter(array_str) -> List:
    return json.loads(array_str)


def load_data(start_date: date, end_date: date, data_path: str) -> pd.DataFrame:
    """
    Load data from folder set in data_path. Those data file should be downloaded by demeter, and meet name rule.
    Deribit-option-book-{token}-{day.strftime('%Y%m%d')}.csv
    data can be downloaded from dropbox: https://www.dropbox.com/scl/fo/kwk5kgiseu5rvccjscd0f/ANswtRLzpCxOc6cMTH0oRlE?rlkey=ai071f9695uz287lt8k0bci5e&dl=0

    :param start_date: start day
    :type start_date: date
    :param end_date: end day, the end day will be included
    :type end_date: date
    :param data_path: path to load data
    :type data_path: str
    """
    logger = logging.getLogger("Deribit data")

    cache_key = CacheManager.get_cache_key(MarketTypeEnum.deribit_option.name, start_date, end_date, address="ETH")
    cache_df = CacheManager.load(cache_key)
    if cache_df is not None:
        return cache_df

    logger.info(f"{MarketTypeEnum.deribit_option.name} start load files from {start_date} to {end_date}...")
    day = start_date
    df = pd.DataFrame()
    from tqdm import tqdm

    with tqdm(total=(end_date - start_date).days + 1, ncols=150) as pbar:
        while day <= end_date:
            path = os.path.join(
                data_path,
                f"Deribit-option-book-ETH-{day.strftime('%Y%m%d')}.csv",
            )
            if not os.path.exists(path):
                logging.warning(f"resource file {path} not found")
                day += timedelta(days=1)
                pbar.update()
                continue

            day_df = pd.read_csv(
                str(path),
                parse_dates=["time", "expiry_time"],
                index_col=["time", "instrument_name"],
                converters={"asks": order_converter, "bids": order_converter},
            )
            day_df["t"] = pd.to_timedelta(day_df["t"])
            day_df.drop(columns=["actual_time", "min_price", "max_price"], inplace=True)
            df = pd.concat([df, day_df])
            day += timedelta(days=1)
            pbar.update()

    CacheManager.save(cache_key, df)
    logger.info("data has been prepared")
    return df
