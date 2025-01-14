import logging
import os
from datetime import datetime, timedelta, date
from typing import NamedTuple

import pandas as pd
import pickle
from dataclasses import dataclass

CACHE_PATH = os.path.join(os.path.expanduser("~"), ".demeter")
CACHE_CONFIG_PATH = os.path.join(CACHE_PATH, "config.pkl")
CACHE_KEEP_DAYS = 30


class CacheKey(NamedTuple):
    market: str
    start: str
    end: str
    chain: str = ""
    address: str = ""


@dataclass
class CacheItem:
    create_time: datetime
    last_visit: datetime
    file_name: str


class CacheManager:
    @staticmethod
    def get_cache_key(market: str, start: date, end: date, chain: str = "", address: str = ""):
        return CacheKey(market, start.strftime("%y%m%d"), end.strftime("%y%m%d"), chain, address)

    @staticmethod
    def prepare_cache():
        if not os.path.exists(CACHE_PATH):
            os.mkdir(CACHE_PATH)
        if os.path.exists(CACHE_CONFIG_PATH):

            with open(CACHE_CONFIG_PATH, "rb") as f:
                config = pickle.load(f)
            # remove old files
            key_to_remove = []
            for k, v in config.items():
                if v.last_visit + timedelta(days=CACHE_KEEP_DAYS) < datetime.now():
                    file_path  = os.path.join(CACHE_PATH, v.file_name)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    key_to_remove.append(k)
            for k in key_to_remove:
                del config[k]
            if len(key_to_remove) > 0:
                with open(CACHE_CONFIG_PATH, "wb") as f:
                    pickle.dump(config, f)
        else:
            config = {}
            with open(CACHE_CONFIG_PATH, "wb") as f:
                pickle.dump(config, f)

    @staticmethod
    def save(key: CacheKey, df: pd.DataFrame):

        CacheManager.prepare_cache()
        with open(CACHE_CONFIG_PATH, "rb") as f:
            config = pickle.load(f)
        if key in config:
            return

        file_name = f"{key.market}_{key.chain}_{key.start}_{key.end}_{key.address}.feather"
        config[key] = CacheItem(create_time=datetime.now(), last_visit=datetime.now(), file_name=file_name)
        df.to_feather(os.path.join(CACHE_PATH, file_name), compression="lz4")
        logging.info(f"Cache file was saved to {os.path.join(CACHE_PATH, file_name)}")
        with open(CACHE_CONFIG_PATH, "wb") as f:
            pickle.dump(config, f)

    @staticmethod
    def load(key: CacheKey) -> pd.DataFrame | None:
        if not os.path.exists(CACHE_CONFIG_PATH):
            return None
        with open(CACHE_CONFIG_PATH, "rb") as f:
            config = pickle.load(f)
        if key not in config:
            return None

        path = os.path.join(CACHE_PATH, config[key].file_name)
        if not os.path.exists(path):
            del config[key]
            with open(CACHE_CONFIG_PATH, "wb") as f:
                pickle.dump(config, f)
            return None
        else:
            config[key].last_visit = datetime.now()
            with open(CACHE_CONFIG_PATH, "wb") as f:
                pickle.dump(config, f)
            return pd.read_feather(path)
