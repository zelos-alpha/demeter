import unittest
from demeter import Lines, Line, LineTypeEnum
from pandas import Series
import pandas as pd


class LinesTest(unittest.TestCase):
    # ==========lines=========================
    def test_new_object(self):
        index = pd.date_range('2022-9-6 8:5:0', periods=9, freq='T')
        series0 = Line(range(9), index=index)
        df = Lines(data={"s0": series0}, index=index)
        self.assertTrue(isinstance(df, pd.DataFrame))
        self.assertEqual(df.row_length(), 9)
        print(df)

    def test_column_name(self):
        index = pd.date_range('2022-9-6 8:5:0', periods=3, freq='T')
        # 原生方式: 字典
        series0 = Line(range(3), index=index, line_type=LineTypeEnum.inAmount0)
        df = Lines(data={"s0": series0}, index=index)
        self.assertEqual(df.iloc[:, 0].name, "s0")
        # 内置类型的数组
        series0 = Line(range(3), index=index, line_type=LineTypeEnum.inAmount0)  # 内置类型的数组
        series1 = Line(range(3), index=index, name="hello")  # 指定了名字
        series2 = Line(range(3), index=index)  # 没有指定名字
        df = Lines(data=[series0, series1, series2], index=index)
        self.assertEqual(df.iloc[:, 0].name, "inAmount0")
        self.assertEqual(df.iloc[:, 1].name, "hello")
        self.assertEqual(df.iloc[:, 2].name, "Column2")

        series0 = Line(range(3), index=index, line_type=LineTypeEnum.inAmount0)
        df = Lines(data=series0, index=index)
        self.assertEqual(df.iloc[:, 0].name, "inAmount0")

    # ==========lines index=========================

    def test_non_time_index(self):
        try:
            series0 = Line(range(9))
            df = Lines(data={"s0": series0})
            self.assertTrue(False, "ex should raise")
        except RuntimeError as e:
            self.assertTrue(str(e).__contains__("datetime"))

    def test_get(self):
        index = pd.date_range('2022-9-6 8:5:0', periods=9, freq='T')
        series0 = Line(range(9), index=index)
        df = Lines(data={"s0": series0}, index=index)
        df.move_cursor_to_next()
        df.move_cursor_to_next()
        df.move_cursor_to_next()

    def test_get_cursor(self):
        index = pd.date_range('2022-9-6 8:5:0', periods=9, freq='T')
        series0 = Line(range(9), index=index)
        df = Lines(data={"s0": series0}, index=index)
        df.move_cursor_to_next()
        i1 = df.get_by_cursor(0)
        df.move_cursor_to_next()
        i2 = df.get_by_cursor(0)
        df.move_cursor_to_next()
        i3 = df.get_by_cursor(0)

        self.assertEqual(i3["s0"], df.get_by_cursor(0)["s0"])
        self.assertEqual(i1["s0"], df.get_by_cursor(-2)["s0"])
        try:
            df.get_by_cursor(-4)
            self.assertTrue(False, "ex should raise")
        except IndexError as e:
            self.assertTrue(str(e).__contains__("out of range"))
        try:
            df.get_by_cursor(6)
            self.assertTrue(False, "ex should raise")
        except IndexError as e:
            self.assertTrue(str(e).__contains__("out of range"))

    # ===========line=========================

    def test_line_resample(self):
        index = pd.date_range('2022-9-6 8:0:0', periods=9, freq='T')
        series0 = Line(range(9), index=index, line_type=LineTypeEnum.highestTick)
        newSeries0 = series0.resample_by_type("3T")
        self.assertEqual(newSeries0[0], 2)
        self.assertEqual(newSeries0[1], 5)
        self.assertEqual(newSeries0[2], 8)
        index = pd.date_range('2022-9-6 8:0:0', periods=9, freq='T')
        series1 = Line(range(9), index=index, line_type=LineTypeEnum.lowestTick)
        newSeries1 = series1.resample_by_type("3T")
        self.assertEqual(newSeries1[0], 0)
        self.assertEqual(newSeries1[1], 3)
        self.assertEqual(newSeries1[2], 6)

    def test_line_fillna(self):
        index = pd.date_range('2022-9-6 8:0:0', periods=12, freq='T')
        series0 = Line([1, 2, 3, 4, float('nan'), 6, 7, 8, 9, 10, 11, 12], index=index,
                       line_type=LineTypeEnum.highestTick)
        self.assertEqual(series0.fillna()[4], 4)
        series0.line_type = LineTypeEnum.inAmount0
        self.assertEqual(series0.fillna()[4], 0)
        series0.line_type = LineTypeEnum.other
        self.assertEqual(series0.fillna(100)[4], 100)

    # ===========lines again=========================
    def test_lines_resample(self):
        index = pd.date_range('2022-9-6 8:0:0', periods=6, freq='T')
        series0 = Line(range(6), index=index, line_type=LineTypeEnum.highestTick)  # 内置类型
        series1 = Line(range(6), index=index, line_type=LineTypeEnum.inAmount0)  # 内置类型
        series2 = Line(range(6), index=index, name="s2", line_type=LineTypeEnum.other)  # 不是内置类型, 定义了重采样
        series3 = Line(range(6), index=index, name="s3", line_type=LineTypeEnum.other)  # 没有定义, 使用默认的重采样方式
        df = Lines(data=[series0, series1, series2, series3], index=index)
        df = df.resample_by_type("3T", agg={"s2": "sum"})
        print(df)
        self.assertEqual(df.iloc[0, 0], 2)
        self.assertEqual(df.iloc[1, 0], 5)
        self.assertEqual(df.iloc[0, 1], 3)
        self.assertEqual(df.iloc[1, 1], 12)
        self.assertEqual(df.iloc[0, 2], 3)
        self.assertEqual(df.iloc[1, 2], 12)
        self.assertEqual(df.iloc[0, 3], 0)
        self.assertEqual(df.iloc[1, 3], 3)

    def test_lines_resample_return(self):
        index = pd.date_range('2022-9-6 8:0:0', periods=6, freq='T')
        series0 = Line(range(6), index=index, line_type=LineTypeEnum.highestTick)  # 内置类型
        df = Lines(data=series0, index=index)
        df = df.resample_by_type("3T")
        print(df)
        # 返回值应该还是Lines类型
        df.move_cursor_to_next()

    def test_lines_fillna(self):
        index = pd.date_range('2022-9-6 8:0:0', periods=6, freq='T')
        array = [1, 2, float("nan"), 4, 5, 6]
        seriesC = Line([1, 8, float("nan"), 4, 5, 6], index=index, line_type=LineTypeEnum.closeTick)  # 内置类型
        series0 = Line(array, index=index, line_type=LineTypeEnum.highestTick)  # 内置类型
        series1 = Line(array, index=index, line_type=LineTypeEnum.inAmount0)  # 内置类型
        series2 = Line(array, index=index, name="s2")  # 不是内置类型, 定义了重采样
        series3 = Line(array, index=index, name="s3")  # 没有定义, 使用默认的重采样方式
        df = Lines(data=[series0, series1, series2, series3, seriesC], index=index)
        new_df = df.fillna(0)
        print(new_df)
        self.assertEqual(new_df.iloc[2, 0], 8)
        self.assertEqual(new_df.iloc[2, 1], 0)
        self.assertEqual(new_df.iloc[2, 2], 0)
        self.assertEqual(new_df.iloc[2, 3], 0)
        self.assertEqual(new_df.iloc[2, 4], 8)

    def test_lines_fillna_return(self):
        index = pd.date_range('2022-9-6 8:0:0', periods=6, freq='T')
        seriesC = Line([1, 8, float("nan"), 4, 5, 6], index=index, line_type=LineTypeEnum.closeTick)  # 内置类型
        df = Lines(data=[seriesC], index=index)
        new_df = df.fillna()
        print(type(new_df))


if __name__ == '__main__':
    unittest.main()
