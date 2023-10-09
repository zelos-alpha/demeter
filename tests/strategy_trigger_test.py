import unittest
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from demeter import TokenInfo, PriceTrigger, MarketDict, MarketInfo, AtTimeTrigger, PeriodTrigger, MarketStatus, RowData

eth = TokenInfo(name="weth", decimal=18, address="0x7ceb23fd6bc0add59e62ac25578270cff1b9f619")
usdc = TokenInfo(name="usdc", decimal=6)


class UniLpCoreTest(unittest.TestCase):
    @staticmethod
    def __get_moke_row_data(timestamp, prices) -> MarketDict[MarketStatus]:
        d = RowData(timestamp=timestamp, row_id=0, prices=prices)
        d.market_status[MarketInfo("m")] = pd.Series()
        return d

    @staticmethod
    def __get_price_df() -> pd.DataFrame:
        return pd.DataFrame(
            index=pd.date_range(datetime(2023, 5, 1), datetime(2023, 5, 1, 23, 59, 59), freq="1T"),
            data={"eth": np.arange(1700, 1700 + (1440 - 1) / 100, step=0.01)},
        )

    def __run(self, price_df, trigger):
        for time_index, price_row in price_df.iterrows():
            if trigger.when(UniLpCoreTest.__get_moke_row_data(time_index, price_row)):
                trigger.do(UniLpCoreTest.__get_moke_row_data(time_index, price_row))

    def test_price_trigger(self):
        match_price = []
        price_df = UniLpCoreTest.__get_price_df()
        pt = PriceTrigger(condition=lambda p: p["eth"] > 1714.35, do=lambda row_data: match_price.append(row_data.prices["eth"]))
        self.__run(price_df, pt)
        self.assertEqual(len(match_price), 4)

    def test_at_time_trigger(self):
        match_time = []
        price_df = UniLpCoreTest.__get_price_df()
        pt = AtTimeTrigger(time=datetime(2023, 5, 1, 23, 59, 0), do=lambda row_data: match_time.append(row_data.timestamp))
        self.__run(price_df, pt)
        self.assertEqual(len(match_time), 1)
        self.assertEqual(price_df.index[1440 - 1], datetime(2023, 5, 1, 23, 59, 0))

    def test_period_trigger(self):
        matched_time = []
        price_df = UniLpCoreTest.__get_price_df()
        pt = PeriodTrigger(time_delta=timedelta(hours=1), do=lambda row_data: matched_time.append(row_data.timestamp))
        self.__run(price_df, pt)
        self.assertEqual(len(matched_time), 23)
        self.assertIn(price_df.index[1 * 60], matched_time)
        self.assertIn(price_df.index[4 * 60], matched_time)
        self.assertIn(price_df.index[10 * 60], matched_time)
        self.assertIn(price_df.index[23 * 60], matched_time)
        self.assertNotIn(price_df.index[0], matched_time)

    def test_period_trigger_immdiately(self):
        matched_time = []
        price_df = UniLpCoreTest.__get_price_df()
        pt = PeriodTrigger(
            time_delta=timedelta(hours=1),
            trigger_immediately=True,
            do=lambda row_data: matched_time.append(row_data.timestamp),
        )
        self.__run(price_df, pt)
        self.assertEqual(len(matched_time), 24)
        self.assertIn(price_df.index[1 * 60], matched_time)
        self.assertIn(price_df.index[4 * 60], matched_time)
        self.assertIn(price_df.index[10 * 60], matched_time)
        self.assertIn(price_df.index[23 * 60], matched_time)
        self.assertIn(price_df.index[0], matched_time)
