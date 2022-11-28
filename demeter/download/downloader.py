import os
from datetime import date, timedelta

import pandas as pd
from tqdm import tqdm  # process bar

from ._typing import ChainType, DownloadParam
from .process import process_raw_data
from .source_bigquery import download_bigquery_pool_event_oneday
from .source_rpc import download_and_save_by_day
from .utils import get_file_name


def download_from_rpc(config: DownloadParam):
    if config.rpc.end_height <= config.rpc.start_height:
        raise RuntimeError("start height should less than end height")

    downloaded_day = download_and_save_by_day(config)
    # downloaded_day = ["2022-06-30", "2022-07-01", "2022-07-02"]

    if len(downloaded_day) <= 2:
        raise RuntimeError("As first day and last day will be dropped, "
                           "day length should at least 3, current length is " + len(downloaded_day))
    print(f"now will drop data in {downloaded_day[0]} and {downloaded_day[len(downloaded_day) - 1]} "
          f"as they a highly likely insufficient for a whole day")
    downloaded_day = downloaded_day[1:len(downloaded_day) - 1]
    for day in downloaded_day:
        day_df = pd.read_csv(get_file_name(config.save_path, config.chain.name, config.pool_address, day, True))
        processed_day_data = process_raw_data(day_df)
        processed_day_data.to_csv(get_file_name(config.save_path, config.chain.name, config.pool_address, day, False),
                                  header=True, index=False)


def download_from_bigquery(chain: ChainType, pool_address: str, start: date, end: date,
                           save_path=os.getcwd(), save_raw_file=False, skip_exist=True):
    """
    Download transfer data by day
    :param chain: which chain
    :param pool_address: contract address of swap pool
    :param start: start date
    :param end: end date
    :param data_source: which data source to download
    :param save_path: save to path
    :param save_raw_file: save raw data or not
    :param skip_exist: if file exist, skip.
    :return:
    """
    pool_address = pool_address.lower()
    end = end + timedelta(days=1)  # make date range is [a,b], instead of [a,b)
    if start > end:
        raise RuntimeError("start date should earlier than end date")
    date_array = split_date_range_to_array(start, end)
    for i in tqdm(range(len(date_array)), ncols=150):
        day = date_array[i]
        date_str = day.strftime("%Y-%m-%d")
        file_name = get_file_name(save_path, chain.name, pool_address, date_str, False)
        if skip_exist and os.path.exists(file_name):
            continue
        raw_day_data = download_bigquery_pool_event_oneday(chain, pool_address, day)
        if save_raw_file:
            raw_day_data.to_csv(get_file_name(save_path, chain.name, pool_address, date_str, True),
                                header=True,
                                index=False)
        processed_day_data = process_raw_data(raw_day_data)
        # save processed
        processed_day_data.to_csv(file_name, header=True, index=False)
        # time.sleep(1)


def split_date_range_to_array(start: date, end: date) -> "array":
    return [start + timedelta(days=x) for x in range(0, (end - start).days)]
