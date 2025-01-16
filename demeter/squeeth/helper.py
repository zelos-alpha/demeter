import logging
import math
import os
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict

import pandas as pd

from demeter import DemeterError, MarketTypeEnum
from demeter.data import CacheManager
from demeter.squeeth import VaultKey, Vault
from ._typing import WETH, oSQTH
from demeter.utils import console_text, to_decimal


def calc_twap_price(prices: pd.Series) -> Decimal:
    """
    Calc TWAP(time weighted average price) as uniswap oracle.

    :param prices: given price array.
    :type prices: Series
    :return: TWAP price
    :rtype: Decimal
    """
    logged = prices.apply(lambda x: math.log(x, 1.0001))
    logged_sum = logged.sum()
    power = logged_sum / len(prices)
    avg_price = math.pow(1.0001, power)

    return Decimal(avg_price)


def vault_to_dataframe(vaults: Dict[VaultKey, Vault]) -> pd.DataFrame:
    """
    convert supply dict to a dataframe
    """
    vault_dict = {
        "id": [],
        "collateral_amount": [],
        "osqth_short_amount": [],
        "uni_nft_id": [],
    }
    for k, v in vaults.items():
        vault_dict["id"].append(v.id)
        vault_dict["collateral_amount"].append(console_text.format_value(v.collateral_amount))
        vault_dict["osqth_short_amount"].append(console_text.format_value(v.osqth_short_amount))
        vault_dict["uni_nft_id"].append(str(v.uni_nft_id))
    return pd.DataFrame(vault_dict)


def load_squeeth_data(start_date: date, end_date: date, data_path: str) -> pd.DataFrame:
    """
    Load data from .minute.csv, then update index and fill null data.

    :param start_date: start test day
    :type start_date: date
    :param end_date: end test day
    :type end_date: date
    :param data_path: path to load data
    :type data_path: str
    """
    logger = logging.getLogger("Squeeth data")

    cache_key = CacheManager.get_cache_key(MarketTypeEnum.squeeth.name, start_date, end_date)
    cache_df = CacheManager.load(cache_key)
    if cache_df is not None:
        return cache_df
    logger.info(f"{MarketTypeEnum.squeeth.name} start load files from {start_date} to {end_date}...")
    df = pd.DataFrame()
    day = start_date
    if start_date > end_date:
        raise DemeterError(f"start date {start_date} should earlier than end date {end_date}")
    while day <= end_date:
        path = os.path.join(
            data_path,
            f"ethereum-squeeth-controller-{day.strftime('%Y-%m-%d')}.minute.csv",
        )
        day_df = pd.read_csv(
            path,
            converters={"norm_factor": to_decimal, "WETH": to_decimal, "OSQTH": to_decimal},
        )
        df = pd.concat([df, day_df])
        day = day + timedelta(days=1)
    logger.info("load file complete, preparing...")

    df["block_timestamp"] = pd.to_datetime(df["block_timestamp"])
    df.set_index("block_timestamp", inplace=True)
    df = df.ffill()
    if pd.isnull(df.index[0]):
        raise DemeterError(f"start date {start_date} does not have available data, Consider start from previous day")
    CacheManager.save(cache_key, df)
    logger.info("data has been prepared")
    return df

def get_price_from_data(data:pd.DataFrame) -> pd.DataFrame:
    """
    Extract token price from relative uniswap pool. All price is quoted in usd
    """
    price_df = data[[WETH.name, oSQTH.name]].copy()
    price_df[oSQTH.name] = price_df[oSQTH.name] * price_df[WETH.name]
    return price_df