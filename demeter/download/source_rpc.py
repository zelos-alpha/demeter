import csv
import datetime
import operator
import os.path
import pickle
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from operator import itemgetter
from .eth_req import EthRequestClient, GetLogsParam
from tqdm import tqdm  # process bar
import json
from ._typing import DownloadParam, ChainType
from .swap_contract import Constant
from .utils import get_file_name

height_cache_file_name = "_height_timestamp.pkl"
# preserved for future extension. such as special logic for each chain.
CHAINS = {
    ChainType.Polygon: {
        "is_poa": True
    },
    ChainType.Arbitrum: {
        "is_poa": True
    },
    ChainType.Optimism: {
        "is_poa": True
    },
    ChainType.Ethereum: {
        "is_poa": False
    },
}


@dataclass
class ContractConfig:
    address: str
    topics: list[str]
    batch_size: int
    one_by_one: bool


def save_block_dict(height_cache_path, block_dict):
    with open(height_cache_path, 'wb') as f:
        pickle.dump(block_dict, f)


# def dict_factory(cursor, row):
#     d = {}
#     for idx, col in enumerate(cursor.description):
#         d[col[0]] = row[idx]
#     return d


def cut(obj, sec):
    return [obj[i:i + sec] for i in range(0, len(obj), sec)]


def fill_block_info(log, client: EthRequestClient, block_dict):
    height = log['block_number']
    if height not in block_dict:
        block_dt = client.get_block_timestamp(height)
        block_dict[height] = block_dt
    log['block_timestamp'] = block_dict[height].isoformat()
    log['block_dt'] = block_dict[height]
    return log


def query_event_log(client: EthRequestClient, contract_config: ContractConfig, start_height: int, end_height: int,
                    save_path: str,
                    block_dict, chain):
    collect_dt, log_by_day_dict, collect_start = None, OrderedDict(), None  # collect date, date log by day，collect start time
    start_tp = time.time()
    downloaded_day = []
    with tqdm(total=(end_height - start_height + 1), ncols=150) as pbar:
        for height_slice in cut([i for i in range(start_height, end_height + 1)], contract_config.batch_size):
            start = height_slice[0]
            end = height_slice[-1]
            if contract_config.one_by_one:
                logs = []
                for topic_hex in contract_config.topics:
                    tmp_logs = client.get_logs(GetLogsParam(contract_config.address,
                                                            start,
                                                            end,
                                                            [topic_hex]))
                    logs.extend(tmp_logs)
            else:
                logs = client.get_logs(GetLogsParam(contract_config.address, start, end, None))
            log_lst = []
            for log in logs:
                log['blockNumber'] = int(log['blockNumber'], 16)
                if len(log['topics']) > 0 and (log['topics'][0] in contract_config.topics):
                    if log["removed"]:
                        continue
                    log_lst.append({
                        'block_number': log['blockNumber'],
                        'transaction_hash': log['transactionHash'],
                        'transaction_index': log['transactionIndex'],
                        'log_index': log['logIndex'],
                        'DATA': log["data"],
                        'topics': json.dumps(log['topics'])
                    })
            with ThreadPoolExecutor(max_workers=10) as t:
                obj_lst = []
                for data in log_lst:
                    obj = t.submit(fill_block_info, data, client, block_dict)
                    obj_lst.append(obj)
                for future in as_completed(obj_lst):
                    data = future.result()
                    block_time_by_day = data['block_dt'].date()
                    data.pop('block_dt')
                    if block_time_by_day not in log_by_day_dict:
                        log_by_day_dict[block_time_by_day] = [data]
                    else:
                        log_by_day_dict[block_time_by_day].append(data)

            pbar.update(n=len(height_slice))
            if (len(height_slice) < contract_config.batch_size) or (
                    len(height_slice) >= contract_config.batch_size and len(log_by_day_dict) >= 2):
                # collect_dt/collect_start
                if len(log_by_day_dict) > 0:
                    log_by_day_dict = OrderedDict(sorted(log_by_day_dict.items(), key=operator.itemgetter(0)))

                    collect_dt, one_day_data = log_by_day_dict.popitem(last=False)
                    one_day_data = sorted(one_day_data,
                                          key=itemgetter('block_number', 'transaction_index', 'log_index'))
                    collect_dt = collect_dt.strftime('%Y-%m-%d')
                    collect_start = one_day_data[0]['block_number']
                    # write to csv
                    save_one_day(save_path, collect_dt, contract_config, one_day_data, chain)
                    downloaded_day.append(collect_dt)
                    print(f'\nsaved date: {collect_dt}, start height: {collect_start}, '
                          f'length: {len(one_day_data)}, time: {time.time() - start_tp} s')
                    start_tp = time.time()
        return downloaded_day


def save_one_day(save_path, collect_dt, contract_config, one_day_data, chain: ChainType):
    with open(get_file_name(save_path, chain.name, contract_config.address, collect_dt, True), 'w') as csvfile:
        writer = csv.DictWriter(csvfile,
                                fieldnames=['block_number', 'block_timestamp', 'transaction_hash',
                                            'transaction_index',
                                            'log_index', 'DATA', 'topics'])
        writer.writeheader()
        for item in one_day_data:
            writer.writerow(item)


def download_and_save_by_day(config: DownloadParam):
    chain_config = CHAINS[config.chain]
    height_cache_path = config.chain.name + height_cache_file_name
    if os.path.exists(height_cache_path):
        with open(height_cache_path, 'rb') as f:
            block_dict = pickle.load(f)
            print(f"Height cache has loaded, length: {len(block_dict)}")
    else:
        block_dict: dict[int:datetime.datetime] = {}

    client = EthRequestClient(config.rpc.end_point, config.rpc.proxy, config.rpc.auth_string)

    try:
        downloaded_day = query_event_log(client,
                                         ContractConfig(config.pool_address,
                                                        [Constant.SWAP_KECCAK,
                                                         Constant.BURN_KECCAK,
                                                         Constant.COLLECT_KECCAK,
                                                         Constant.MINT_KECCAK],
                                                        config.rpc.batch_size,
                                                        False),
                                         config.rpc.start_height,
                                         config.rpc.end_height,
                                         config.save_path,
                                         block_dict,
                                         config.chain)
    except Exception as e:
        print(e)
        import traceback
        print(traceback.format_exc())
    print(f"saving height cache, length {len(block_dict)}")
    save_block_dict(height_cache_path, block_dict)
    return downloaded_day if downloaded_day else []
