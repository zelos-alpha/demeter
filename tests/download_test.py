import datetime
import unittest
from datetime import date, datetime
from download import downloader, ChainType, DataSource, source_bigquery, utils
import pandas
import numpy as np


class TestDict(unittest.TestCase):
    def test_download(self):
        downloader.download_by_day(ChainType.Polygon,
                                   "0x45dda9cb7c25131df268515131f647d726f50608",
                                   datetime.strptime("2022-7-24", "%Y-%m-%d").date(),
                                   datetime.strptime("2022-7-25", "%Y-%m-%d").date(),
                                   save_path="data"
                                   )

    def test_wrong_data(self):
        try:
            downloader.download_by_day(ChainType.Polygon,
                                       "0x45dda9cb7c25131df268515131f647d726f50608",
                                       date(2022, 9, 30),
                                       date(2022, 6, 30))
        except RuntimeError as e:
            self.assertTrue(e.args[0].find("should earlier than") != -1, "error message is wrong")

    def test_process_data(self):
        df = pandas.read_csv("data/0x45dda9cb7c25131df268515131f647d726f50608-2022-07-01.csv")
        newdf = source_bigquery.process_raw_data(df)
        newdf.to_csv("data/test_processed_result.csv", header=True, index=False)
