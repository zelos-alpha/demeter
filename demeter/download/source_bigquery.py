import datetime
from datetime import date

import pandas
from pandas import Timestamp

from ._typing import ChainType, MarketData, OnchainTxType, MarketDataNames
from .swap_contract import Constant, handle_event
from .utils import TextUtil, TimeUtil, DataUtil


def download_bigquery_pool_event_oneday(chain: ChainType, contract_address: str, one_date: date) -> "pandas.DataFrame":
    """
    query log data from big_query
    sample response
    [{
          "log_index": "38",
          "transaction_hash": "0xb013afdc4272ccf59a19cfa3943d2af9e818dd3a88981fc0e31e043233d31d1a",
          "transaction_index": "1",
          "address": "0x8ef34625aec17541b6147a40a3840c918263655e",
          "data": "0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002022f034f3ae810000000000000000000000000000000000000000000000c30329a44dfdbf0de60000000000000000000000000000000000000000000000000000000000000000",
          "topics": ["0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822", "0x0000000000000000000000007a250d5630b4cf539739df2c5dacb4c659f2488d", "0x000000000000000000000000700000f7c2c71caab6b250ca85237117ff702ebb"],
          "block_timestamp": "2022-09-01T01:01:52Z",
          "block_number": "15449884",
          "block_hash": "0x48268cc49b9a68fa08a5954a4a841f36205f8ba5a957cb632165a817c6817b05"
    }]
    :param chain:
    :param contract_address:
    :param one_date:
    :return:
    """
    from google.cloud import bigquery
    client = bigquery.Client()
    # no index on blocknum for bigquery. Do not use blocknum in where. slow.
    query = f"""SELECT
        block_timestamp,
        block_number,
        transaction_hash,
        transaction_index,
        log_index,
        topics,
        DATA
        FROM
        {ModuleUtils.get_table_name(chain)}
        WHERE
            (topics[SAFE_OFFSET(0)] = '{Constant.MINT_KECCAK}'
            OR topics[SAFE_OFFSET(0)] = '{Constant.BURN_KECCAK}'
            OR topics[SAFE_OFFSET(0)] = '{Constant.SWAP_KECCAK}')
            AND DATE(block_timestamp) >=  DATE("{one_date}")
            AND DATE(block_timestamp) <=  DATE("{one_date}")
            AND address = "{contract_address}"  order by block_number asc,log_index asc"""
    # print(query);
    query_job = client.query(query)  # Make an API request.
    result = query_job.to_dataframe(create_bqstorage_client=False)
    return result


def process_raw_data(raw_data: pandas.DataFrame) -> "pandas.DataFrame":
    if raw_data.size <= 0:
        return raw_data
    start_time = TimeUtil.get_minute(ModuleUtils.get_datetime(raw_data.loc[0, "block_timestamp"]))
    minute_rows = []
    data = []
    total_index = 1
    for index, row in raw_data.iterrows():
        current_time = TimeUtil.get_minute(ModuleUtils.get_datetime(row["block_timestamp"]))
        if start_time == current_time:  # middle of a minute
            minute_rows.append(row)
        else:  #
            data.append(sample_data_to_one_minute(start_time, minute_rows))
            total_index += 1
            # start next minute
            start_time = current_time
            minute_rows = [row]
    data = DataUtil.fill_missing(data)
    df = pandas.DataFrame(columns=MarketDataNames, data=map(lambda d: d.to_array(), data))
    return df


def sample_data_to_one_minute(current_time, minute_rows) -> MarketData:
    data = MarketData()
    data.timestamp = current_time
    i = 1
    for r in minute_rows:
        tx_type, sender, receipt, amount0, amount1, sqrtPriceX96, current_liquidity, current_tick, tick_lower, tick_upper, delta_liquidity = handle_event(
            r.topics, r.DATA)
        # print(tx_type, sender, receipt, amount0, amount1, sqrtPriceX96, current_liquidity, current_tick, tick_lower,
        #       tick_upper, delta_liquidity)
        match tx_type:
            case OnchainTxType.MINT:
                pass
            case OnchainTxType.BURN:
                pass
            case OnchainTxType.COLLECT:
                pass
            case OnchainTxType.SWAP:
                data.netAmount0 += amount0
                data.netAmount1 += amount1
                if amount0 > 0:
                    data.inAmount0 += amount0
                if amount1 > 0:
                    data.inAmount1 += amount1
                if data.openTick is None:  # first
                    data.openTick = current_tick
                    data.highestTick = current_tick
                    data.lowestTick = current_tick
                if data.highestTick < current_tick:
                    data.highestTick = current_tick
                if data.lowestTick > current_tick:
                    data.lowestTick = current_tick
                if i == len(minute_rows):  # last
                    data.closeTick = current_tick
                    data.currentLiquidity = current_liquidity

        i += 1
    return data


class ModuleUtils(object):
    @staticmethod
    def get_table_name(chain_type: ChainType) -> str:
        match chain_type:
            case ChainType.Polygon:
                return "public-data-finance.crypto_polygon.logs"
            case ChainType.Ethereum:
                return "bigquery-public-data.crypto_ethereum.logs"
            case _:
                raise RuntimeError("chain type {} is not supported by BigQuery", chain_type)

    @staticmethod
    def get_datetime(date_str: str) -> datetime:
        if type(date_str) == Timestamp:
            return date_str.to_pydatetime()
        else:
            return datetime.datetime.strptime(TextUtil.cut_after(str(date_str), "+"), "%Y-%m-%d %H:%M:%S")
