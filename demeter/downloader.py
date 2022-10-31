import os
import sys
from datetime import datetime

import toml

from .download import ChainType, DataSource, downloader

DEFAULT_SAVE_PATH = "data"


class DownloadParam(object):
    def __init__(self):
        self.chain = ChainType.Ethereum
        self.source = DataSource.BigQuery
        self.pool_address = ""
        self.start = ""
        self.end = datetime.now().strftime("%Y-%m-%d")
        self.auth_file = ""
        self.save_path = DEFAULT_SAVE_PATH

    def get_formatted(self):
        return f"chain={self.chain.name}\n" \
               f"source={self.source.name}\n" \
               f"auth_file={self.auth_file}\n" \
               f"save_path={self.save_path}"

    def __str__(self):
        return f"chain={self.chain}," \
               f"source={self.source}," \
               f"pool_address={self.pool_address}," \
               f"start={self.start}," \
               f"end={self.end}," \
               f"auth_file={self.auth_file}," \
               f"save_path={self.save_path}"


def get_enum_by_name(me, name):
    for e in me:
        if e.name.lower() == name.lower():
            return e
    raise RuntimeError(f"cannot found {name} in {me}, allow value is " + str([x.name for x in me]))


class Downloader:

    def __init__(self, config):
        self.config: DownloadParam = self.convert_config(config)

    @staticmethod
    def convert_config(config: dict):
        param = DownloadParam()
        if "chain" in config and config["chain"] != "":
            param.chain = get_enum_by_name(ChainType, config["chain"])
        if "source" in config and config["source"] != "":
            param.source = get_enum_by_name(DataSource, config["source"])
        if param.source == DataSource.BigQuery:
            if "auth_file" in config:
                param.auth_file = config["auth_file"]
                if not os.path.exists(param.auth_file):
                    raise RuntimeError("google auth file not found")

            else:
                raise RuntimeError("you must set google auth file")
        if "save_path" in config and config["save_path"] != "":
            param.save_path = config["save_path"]
        if not os.path.exists(param.save_path):
            raise RuntimeError(f"path {param.save_path} not exist")
        if "pool_address" in config:
            param.pool_address = config["pool_address"]
        else:
            raise RuntimeError("you must set pool contract address")
        if "start" in config:
            param.start = config["start"]
        else:
            raise RuntimeError("you must set start date, eg: 2022-10-1")
        if "end" in config and config["end"] != "":
            param.end = config["end"]

        return param

    def do_download(self):
        start_date = datetime.strptime(self.config.start, "%Y-%m-%d").date()
        end_date = datetime.strptime(self.config.end, "%Y-%m-%d").date()
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config.auth_file
        downloader.download_by_day(self.config.chain,
                                   self.config.pool_address,
                                   start_date,
                                   end_date,
                                   self.config.source,
                                   self.config.save_path)
        print("download complete, check your files in " + self.config.save_path)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print(
            "please set a config file. in toml format. 'python -m demeter.downloader config.toml'. config file demo: ")
        print("======================")
        print("""
        chain = "polygon"
        source = "BigQuery"
        pool_address = "0x45dda9cb7c25131df268515131f647d726f50608"
        start = "2022-9-19"
        end = "2022-9-20"
        auth_file = "../auth/airy-sight-000000-dddb5ce41c48.json"
        save_path = "../data"
        """)
        print("======================")
        exit(1)
    if not os.path.exists(sys.argv[1]):
        print("config file not found, use")
        exit(1)
    config_file = toml.load(sys.argv[1])
    try:
        downloaderCls = Downloader(config_file)
    except RuntimeError as e:
        print(e)
        exit(1)
    print(downloaderCls.config)
    downloaderCls.do_download()
