import datetime
import unittest
from datetime import date, datetime

from demeter import EthError
from demeter.download import ChainType
from demeter.download import downloader, source_bigquery
import pandas

from demeter.download.eth_req import EthRequestClient, GetLogsParam


class TestBigQuery(unittest.TestCase):
    def test_download(self):
        downloader.download_from_bigquery(ChainType.Polygon,
                                          "0x45dda9cb7c25131df268515131f647d726f50608",
                                          date(2022,10,19),
                                          date(2022,10,20),
                                          save_path="data"
                                          )

    def test_wrong_data(self):
        try:
            downloader.download_from_bigquery(ChainType.Polygon,
                                              "0x45dda9cb7c25131df268515131f647d726f50608",
                                              date(2022, 9, 30),
                                              date(2022, 6, 30))
        except RuntimeError as e:
            self.assertTrue(e.args[0].find("should earlier than") != -1, "error message is wrong")

    def test_process_data(self):
        df = pandas.read_csv("data/0x45dda9cb7c25131df268515131f647d726f50608-2022-07-01.csv")
        newdf = source_bigquery.process_raw_data(df)
        newdf.to_csv("data/test_processed_result.csv", header=True, index=False)


class TestRpc(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestRpc, self).__init__(*args, **kwargs)
        self.tool = EthRequestClient("https://http-mainnet.hecochain.com", "http://localhost:7890", "")

    def test_eth_rpc_get_block(self):
        resp = self.tool.get_block(20930852)
        print(resp)
        self.assertEqual(resp["hash"], "0x72f4edcaf52888568aae8cbea268fe90970e0577305e13cf1d093a4767050880")

    def test_eth_rpc_get_timestamp(self):
        resp = self.tool.get_block_timestamp(20930852)
        print(resp)
        self.assertEqual(resp, datetime(2022, 11, 29, 1, 51, 53))

    def test_expection(self):
        try:
            resp = self.tool.get_block_timestamp(-1)
        except EthError as e:
            print(e)
            self.assertTrue(e.code == -32602)

    def test_get_logs(self):
        resp = self.tool.get_logs(GetLogsParam("0x5545153ccfca01fbd7dd11c0b23ba694d9509a6f", 20932554, 20932560, None))
        print(resp)
        self.assertEqual(resp[0]["transactionHash"],
                         "0x9935a294ed541b9946d4039e36720279440537c2587b475e405174dd57ed7bc0")
        self.assertEqual(resp[0]["topics"][0], "0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c")

    def test_get_logs_index(self):
        resp = self.tool.get_logs(GetLogsParam("0x5545153ccfca01fbd7dd11c0b23ba694d9509a6f", 20932554, 20932560,
                                               ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]))
        print(resp)
        self.assertEqual(resp[0]["transactionHash"],
                         "0x9935a294ed541b9946d4039e36720279440537c2587b475e405174dd57ed7bc0")
        self.assertEqual(resp[0]["topics"][0], "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")
