import unittest

import pandas as pd

from demeter.uniswap import LineTypeEnum, data


class UniLpDataTest(unittest.TestCase):
    # ==========lines=========================
    def test_new_object(self):
        index = pd.date_range("2022-9-6 8:5:0", periods=9, freq="1min")
        series0 = pd.Series(range(9), index=index)
        df = pd.DataFrame(data={"s0": series0}, index=index)
        self.assertTrue(isinstance(df, pd.DataFrame))
        self.assertEqual(len(df.index), 9)
        print(df)

    # ===========lines again=========================
    def test_lines_resample(self):
        index = pd.date_range("2022-9-6 8:0:0", periods=6, freq="1min")
        series0 = pd.Series(range(6), index=index)  # predefined type
        series1 = pd.Series(range(6), index=index)  # predefined type
        series2 = pd.Series(range(6), index=index)  # not predefined type, but defined resample
        series3 = pd.Series(range(6), index=index)  # not predefined type, use default resample
        df = pd.DataFrame(
            data={
                LineTypeEnum.highestTick.name: series0,
                LineTypeEnum.inAmount0.name: series1,
                "s2": series2,
                "s3": series3,
            },
            index=index,
        )
        df = data.resample(df, "3min", agg={"s2": "sum"})
        self.assertEqual(df.iloc[0, 0], 2)
        self.assertEqual(df.iloc[1, 0], 5)
        self.assertEqual(df.iloc[0, 1], 3)
        self.assertEqual(df.iloc[1, 1], 12)
        self.assertEqual(df.iloc[0, 2], 3)
        self.assertEqual(df.iloc[1, 2], 12)
        self.assertEqual(df.iloc[0, 3], 0)
        self.assertEqual(df.iloc[1, 3], 3)

    def test_lines_resample_return(self):
        index = pd.date_range("2022-9-6 8:0:0", periods=6, freq="1min")
        series0 = pd.Series(range(6), index=index, name=LineTypeEnum.highestTick.name)  # predefined type
        df = pd.DataFrame(data=series0, index=index)
        df = data.resample(df, "3min")
        print(df)

    def test_lines_fillna(self):
        index = pd.date_range("2022-9-6 8:0:0", periods=6, freq="1min")
        array = [1, 2, float("nan"), 4, 5, 6]
        seriesC = pd.Series([1, 8, float("nan"), 4, 5, 6], index=index)  # predefined type
        series0 = pd.Series(array, index=index)  # predefined type
        series1 = pd.Series(array, index=index)  # predefined type
        series2 = pd.Series(array, index=index)  # not predefined type, but defined resample
        series3 = pd.Series(array, index=index)  # not predefined type, use default resample
        df = pd.DataFrame(
            data={
                LineTypeEnum.highestTick.name: series0,
                LineTypeEnum.inAmount0.name: series1,
                "S2": series2,
                "S3": series3,
                LineTypeEnum.closeTick.name: seriesC,
            },
            index=index,
        )
        new_df = data.fillna(df, 0)
        print(new_df)
        self.assertEqual(new_df.iloc[2, 0], 8)
        self.assertEqual(new_df.iloc[2, 1], 0)
        self.assertEqual(new_df.iloc[2, 2], 0)
        self.assertEqual(new_df.iloc[2, 3], 0)
        self.assertEqual(new_df.iloc[2, 4], 8)
