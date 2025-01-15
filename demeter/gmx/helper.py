import logging
import os
from datetime import date, timedelta

import pandas as pd

from demeter import ChainType, MarketTypeEnum
from demeter.data import CacheManager
from demeter.utils import to_decimal


def load_gmx_v1_data(chain: ChainType, start_date: date, end_date: date, data_path: str) -> pd.DataFrame:
    logger = logging.getLogger("Gmx v1 data")

    cache_key = CacheManager.get_cache_key(MarketTypeEnum.gmx_v1.name, start_date, end_date)
    cache_df = CacheManager.load(cache_key)
    if cache_df is not None:
        return cache_df

    logger.info(f"{MarketTypeEnum.gmx_v1.name} start load files from {start_date} to {end_date}...")
    assert start_date <= end_date, f"start date {start_date} should earlier than end date {end_date}"
    df = pd.DataFrame()
    day = start_date
    while day <= end_date:
        csv_path = os.path.join(data_path, f"{chain.name.lower()}_gmx_{day.strftime('%Y-%m-%d')}.csv")
        day_df = pd.read_csv(
            csv_path,
            index_col=0,
            parse_dates=True,
            converters={
                "glp_price": to_decimal,
                "weth_price": to_decimal,
                "wavax_price": to_decimal,
                "glp": to_decimal,
                "aum": to_decimal,
            },
        )
        if len(day_df.index) > 0:
            df = pd.concat([df, day_df])
        day = day + timedelta(days=1)
    logger.info("data has been prepared")
    CacheManager.save(cache_key, df)
    return df
