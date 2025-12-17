import json

from .gmx_v2 import PoolConfig


def load_pool_config(path: str) -> PoolConfig:
    with open(path, "r") as f:
        config_json = json.load(f)
    pool_config = PoolConfig(**config_json)
    return pool_config
