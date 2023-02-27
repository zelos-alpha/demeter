import datetime
import random
from dataclasses import dataclass
from typing import List

import requests

from .._typing import EthError


@dataclass
class GetLogsParam:
    address: str
    fromBlock: int
    toBlock: int
    topics: List[str] | None


class EthRequestClient:
    def __init__(self, endpoint: str, proxy="", auth=""):
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=20)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.headers = {}
        self.endpoint = endpoint
        if auth:
            self.headers["Authorization"] = auth
        self.proxies = {"http": proxy, "https": proxy, } if proxy else {}

    def __del__(self):
        self.session.close()

    @staticmethod
    def __encode_json_rpc(method: str, params: list):
        return {"jsonrpc": "2.0", "method": method, "params": params, "id": random.randint(1, 2147483648)}

    @staticmethod
    def __decode_json_rpc(response: requests.Response):
        content = response.json()
        if "error" in content:
            raise EthError(content["error"]["code"], content["error"]["message"])
        return content["result"]

    def do_post(self, param):
        return self.session.post(self.endpoint,
                                 json=param,
                                 proxies=self.proxies,
                                 headers=self.headers)

    def get_block(self, height):
        response = self.do_post(EthRequestClient.__encode_json_rpc("eth_getBlockByNumber", [hex(height), False]))
        return EthRequestClient.__decode_json_rpc(response)

    def get_block_timestamp(self, height):
        resp = self.get_block(height)
        if resp:
            timestamp = int(resp["timestamp"], 16)
            return datetime.datetime.utcfromtimestamp(timestamp)
        else:
            return None

    def get_logs(self, param: GetLogsParam):
        if param.toBlock:
            param.toBlock = hex(param.toBlock)
        if param.fromBlock:
            param.fromBlock = hex(param.fromBlock)
        response = self.do_post(EthRequestClient.__encode_json_rpc("eth_getLogs", [vars(param)]))
        return EthRequestClient.__decode_json_rpc(response)
