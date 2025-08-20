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


def load_gmx_v2_data(chain: ChainType, gm_token_address: str, start_date: date, end_date: date, data_path: str) -> pd.DataFrame:
    logger = logging.getLogger("Gmx v2 data")

    cache_key = CacheManager.get_cache_key(MarketTypeEnum.gmx_v2.name, start_date, end_date, chain.name, gm_token_address)
    cache_df = CacheManager.load(cache_key)
    if cache_df is not None:
        return cache_df

    logger.info(f"{MarketTypeEnum.gmx_v2.name} start load files from {start_date} to {end_date}...")
    assert start_date <= end_date, f"start date {start_date} should earlier than end date {end_date}"
    df = pd.DataFrame()
    day = start_date
    while day <= end_date:
        csv_path = os.path.join(data_path, f"{chain.name.lower()}-GmxV2-{gm_token_address}-{day.strftime('%Y-%m-%d')}.minute.csv")
        day_df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        if len(day_df.index) > 0:
            df = pd.concat([df, day_df])
        day = day + timedelta(days=1)
    logger.info("data has been prepared")

    # .shift(1)的作用:
    # demeter用的是0秒的价格, 而不是59秒的价格. 所以瞬时量和累计量相加会出问题, 比如pending pnl, realized pnl在0秒是5,0,
    # 在30秒的时候, 有个人兑现了(也就是5从pending转移到realized), 所以在这一分钟末尾pending pnl, realized pnl是0,5,
    # 在现实世界中, pnl总量是相等的(5+0,0+5),都是5.
    # 在demeter中, 由于当前分钟用的是开始的值, 那么pending pnl是5, 对于realized pnl, 由于是这分钟发生的, 所以也是5. 所以
    # 前一个分钟的值是5+0=5, 当前分钟的值会是5+5=10, 下一个分钟才恢复为0+5=5, 这显然有问题
    # 所以于realized_pnl和realizedProfit, 用shift(1)推迟到下一分钟.
    # 如果pending pnl用结束(59秒)值(0)就没这个问题, 但这会让净值看起来推迟了一分钟.
    # df[["realizedProfit", "realizedPnl"]] = df[["realizedProfit", "realizedPnl"]].shift(1).fillna(0)
    CacheManager.save(cache_key, df)
    return df
