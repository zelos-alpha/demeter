import os
from datetime import date, timedelta

from tqdm import tqdm  # process bar

from ._typing import ChainType, DataSource
from .source_bigquery import download_bigquery_pool_event_oneday, process_raw_data


def download_by_day(chain: ChainType, pool_address: str, start: date, end: date, data_source=DataSource.BigQuery,
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
    for i in tqdm(range(len(date_array))):
        day = date_array[i]
        date_str = day.strftime("%Y-%m-%d")
        file_name = f"{chain.name}-{pool_address}-{date_str}.csv"
        if skip_exist and os.path.exists(save_path + "//" + file_name):
            continue
        if data_source == DataSource.BigQuery:
            raw_day_data = download_bigquery_pool_event_oneday(chain, pool_address, day)
            if save_raw_file:
                raw_day_data.to_csv(f"{save_path}//raw_{chain.name}-{pool_address}-{date_str}.csv",
                                    header=True,
                                    index=False)
            processed_day_data = process_raw_data(raw_day_data)
        else:
            raise RuntimeError("Data source {} is not supported".format(data_source))
        # save processed
        processed_day_data.to_csv(save_path + "//" + file_name, header=True, index=False)
        # time.sleep(1)


def split_date_range_to_array(start: date, end: date) -> "array":
    return [start + timedelta(days=x) for x in range(0, (end - start).days)]
