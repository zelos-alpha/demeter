import logging
import os
from datetime import date, timedelta

import pandas as pd

from demeter import ChainType, MarketTypeEnum
from demeter.data import CacheManager
from demeter.utils import to_decimal
from ._typing import PRICE_PRECISION
from ._typing2 import GmxV2Pool


def get_price_from_v2_data(data: pd.DataFrame, pool: GmxV2Pool) -> pd.DataFrame:
    price_df = data[["longPrice", "shortPrice"]]
    price_df = price_df.rename(columns={"longPrice": pool.long_token.name, "shortPrice": pool.short_token.name})
    if pool.long_token != pool.index_token:
        price_df[pool.index_token.name] = data["indexPrice"]
    return price_df


def load_gmx_v2_data(
    chain: ChainType, gm_token_address: str, start_date: date, end_date: date, data_path: str
) -> pd.DataFrame:
    logger = logging.getLogger("Gmx v2 data")

    cache_key = CacheManager.get_cache_key(
        MarketTypeEnum.gmx_v2.name, start_date, end_date, chain.name, gm_token_address
    )
    cache_df = CacheManager.load(cache_key)
    if cache_df is not None:
        return cache_df

    logger.info(f"{MarketTypeEnum.gmx_v2.name} start load files from {start_date} to {end_date}...")
    assert start_date <= end_date, f"start date {start_date} should earlier than end date {end_date}"
    df = pd.DataFrame()
    day = start_date
    while day <= end_date:
        csv_path = os.path.join(
            data_path, f"{chain.name.lower()}-GmxV2-{gm_token_address}-{day.strftime('%Y-%m-%d')}.minute.csv"
        )
        day_df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        if len(day_df.index) > 0:
            df = pd.concat([df, day_df])
        day = day + timedelta(days=1)
    logger.info("data has been prepared")
    CacheManager.save(cache_key, df)
    return df
