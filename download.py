import cmd
from download import ChainType, DataSource, downloader
import os
from datetime import datetime

DEFAULT_SAVE_PATH = "./data"


class DownloadParam(object):
    def __init__(self):
        self.chain = ChainType.Ethereum
        self.source = DataSource.BigQuery
        self.pool_address = ""
        self.start = ""
        self.end = ""
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


class Downloader(cmd.Cmd):
    intro = 'Welcome to the demeter data downloader.  Type help or ? to list commands. or just start with "config"\n'
    prompt = '(demeter) '

    def __init__(self, *args, **kwargs):
        self.param = DownloadParam()
        self.has_config = False
        super().__init__(*args, **kwargs)

    def do_show_param(self, _):
        """show download parameter"""
        print(self.param.get_formatted())

    def do_config(self, _):
        """config your download"""
        print(f"Which chain you wanna choose: ")
        [print(f"({ct.value}){ct.name}") for ct in ChainType]
        chose_chain = int(input("input number: "))
        self.param.chain = ChainType(chose_chain)

        print("Which data_source you wanna choose: ")
        [print(f"({ds.value}){ds.name}") for ds in DataSource]
        chose_ds = int(input("input number: "))
        self.param.source = DataSource(chose_ds)

        if chose_ds == DataSource.BigQuery.value:
            print("GOOGLE_APPLICATION_CREDENTIALS file path")
            while True:
                auth_file = input("input google auth file path: ")
                if auth_file == "exit":
                    break
                if os.path.exists(auth_file):
                    self.param.auth_file = auth_file
                    break
                else:
                    print("file not found, try again, or input exit")

        print("where would you like to keep files: ")
        path = input(f"input path (Default path: {DEFAULT_SAVE_PATH}, press enter to keep default): ")
        if "" != path:
            self.param.save_path = path

        print("config compete. your config is:")
        print(self.param.get_formatted())
        print('Now use "download" to start. commend: download pool_contract_address start_date end_date')
        self.has_config = True

    def do_download(self, arg):
        """start download, usage: download pool_contract_address start_date end_date"""
        args = arg.split(" ")
        if len(args) < 3:
            print("usage: download pool_contract_address start_date end_date, try again")
            return
        pool_contract_address, start_date, end_date = args[0], args[1], args[2]
        if not self.has_config:
            print("run config commend first")
            return
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.param.auth_file
        downloader.download_by_day(self.param.chain,
                                   pool_contract_address,
                                   start_date,
                                   end_date,
                                   self.param.source,
                                   self.param.save_path)
        print("download complete, check your files in " + self.param.save_path)

    def do_exit(self, _):
        """退出"""
        exit(0)


if __name__ == '__main__':
    Downloader().cmdloop()
