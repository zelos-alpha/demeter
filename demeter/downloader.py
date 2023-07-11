import os
import sys
import warnings
from datetime import datetime

import toml

from .download import ChainType, DataSource, downloader, DownloadParam
from .utils.application import get_enum_by_name, dict_to_object


class Downloader:

    def __init__(self, config):
        self.config: DownloadParam = self.convert_config(config)

    @staticmethod
    def convert_config(config: dict):
        param = DownloadParam()
        if hasattr(config, "chain"):
            param.chain = get_enum_by_name(ChainType, config.chain)
        if hasattr(config, "source"):
            param.source = get_enum_by_name(DataSource, config.source)
        if hasattr(config, "save_path"):
            param.save_path = config.save_path
        if not param.save_path.endswith("/"):
            param.save_path += "/"
        if not os.path.exists(param.save_path):
            os.makedirs(param.save_path)
        if hasattr(config, "pool_address"):
            param.pool_address = config.pool_address
        else:
            raise RuntimeError("you must set pool contract address")
        if param.source == DataSource.BigQuery:
            if not hasattr(config, "big_query"):
                raise RuntimeError("must set big_query parameters")
            if hasattr(config.big_query, "auth_file"):
                param.big_query.auth_file = config.big_query.auth_file
                if not os.path.exists(param.big_query.auth_file):
                    raise RuntimeError("google auth file not found")
            else:
                raise RuntimeError("you must set google auth file")
            if hasattr(config.big_query, "start"):
                param.big_query.start = config.big_query.start
            else:
                raise RuntimeError("you must set start date, eg: 2022-10-1")
            if hasattr(config.big_query, "end"):
                param.big_query.end = config.big_query.end
        elif param.source == DataSource.RPC:
            if not hasattr(config, "rpc"):
                raise RuntimeError("must set rpc parameters")
            if hasattr(config.rpc, "end_point"):
                param.rpc.end_point = config.rpc.end_point
            else:
                raise RuntimeError("you must set end_point")
            if hasattr(config.rpc, "start_height"):
                param.rpc.start_height = config.rpc.start_height
            else:
                raise RuntimeError("you must set start_height")
            if hasattr(config.rpc, "end_height"):
                param.rpc.end_height = config.rpc.end_height
            else:
                raise RuntimeError("you must set end_height")
            if hasattr(config.rpc, "auth_string"):
                param.rpc.auth_string = config.rpc.auth_string
            if hasattr(config.rpc, "proxy"):
                param.rpc.proxy = config.rpc.proxy
            if hasattr(config.rpc, "batch_size"):
                param.rpc.batch_size = config.rpc.batch_size
        return param

    def do_download(self):
        if self.config.source == DataSource.BigQuery:
            start_date = datetime.strptime(self.config.big_query.start, "%Y-%m-%d").date()
            end_date = datetime.strptime(self.config.big_query.end, "%Y-%m-%d").date()
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config.big_query.auth_file
            downloader.download_from_bigquery(self.config.chain,
                                              self.config.pool_address,
                                              start_date,
                                              end_date,
                                              self.config.save_path,
                                              save_raw_file=True)
        elif self.config.source == DataSource.RPC:
            downloader.download_from_rpc(self.config)
        print("download complete, check your files in " + self.config.save_path)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("please set a config file. in toml format. eg: 'python -m demeter.downloader config.toml'.")
        exit(1)
    if not os.path.exists(sys.argv[1]):
        print("config file not found,")
        exit(1)
    config_file = toml.load(sys.argv[1])
    warnings.warn("This module is deprecated, please use demeter-fetch instead, visit https://github.com/zelos-alpha/demeter-fetch",
                  DeprecationWarning,
                  stacklevel=2)
    try:
        download_entity = Downloader(dict_to_object(config_file))
    except RuntimeError as e:
        print(e)
        exit(1)
    print(download_entity.config)
    download_entity.do_download()
