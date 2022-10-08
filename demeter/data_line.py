import pandas as pd
from pandas import _typing as pd_typing
from enum import Enum

from ._typing import ZelosError

DEFAULT_AGG_METHOD = "first"


class LineTypeEnum(Enum):
    timestamp = 1
    netAmount0 = 2
    netAmount1 = 3
    closeTick = 4
    openTick = 5
    lowestTick = 6
    highestTick = 7
    inAmount0 = 8
    inAmount1 = 9
    currentLiquidity = 10
    other = 100

    @staticmethod
    def safe_get(key):
        try:
            return LineTypeEnum[key]
        except KeyError:
            return None


def get_agg_by_type(line_type: LineTypeEnum) -> str:
    match line_type:
        case LineTypeEnum.openTick:
            return "first"
        case LineTypeEnum.closeTick:
            return "last"
        case LineTypeEnum.highestTick:
            return "max"
        case LineTypeEnum.lowestTick:
            return "min"
        case LineTypeEnum.netAmount0 | LineTypeEnum.netAmount1 | LineTypeEnum.inAmount0 | LineTypeEnum.inAmount1 | LineTypeEnum.currentLiquidity:
            return "sum"
        case _:
            return ""


def get_fillna_param(line_type: LineTypeEnum, method=None, value=0):
    match line_type:
        case LineTypeEnum.openTick | LineTypeEnum.closeTick | LineTypeEnum.highestTick | LineTypeEnum.lowestTick:
            method = "ffill"
            value = None
        case LineTypeEnum.netAmount0 | LineTypeEnum.netAmount1 | LineTypeEnum.inAmount0 | LineTypeEnum.inAmount1 | LineTypeEnum.currentLiquidity:
            method = None
            value = 0
    return {"method": method, "value": value}


class Cursorable(object):
    def __init__(self):
        self.cursor = 0

    def row_length(self):
        return self.index.size

    def get_cursor_range(self):
        """
        获取get_by_cursor中的参数i的合法范围
        :return: 最小值, 最大值
        """
        return -self.cursor, self.index.size - self.cursor - 1

    def move_cursor_to_next(self):
        """
        移动光标, 为了保证效率, 少调用iloc, 就不返回了.
        :return:void
        """
        self.cursor += 1

    def reset_cursor(self):
        self.cursor = 0


class Line(pd.Series, Cursorable):
    """
    一列数据, 继承于pandas.Series
    """

    def __init__(
            self,
            data=None,
            index=None,
            dtype: pd_typing.Dtype | None = None,
            name=None,
            copy: bool = False,
            fastpath: bool = False,
            line_type=LineTypeEnum.other
    ):
        """
        初始化一列数据, 参数和pandas.Series相同, 但是多了一个数据类型
        :param line_type: 指定数剧列的类型, 如开盘, 收盘. amount.
        """
        if not isinstance(index, pd.core.indexes.datetimes.DatetimeIndex):
            raise ZelosError("index must be datetime")
        super().__init__(data, index, dtype, name, copy, fastpath)
        self.line_type = line_type
        Cursorable.__init__(self)

    def resample_by_type(
            self,
            rule,
            axis=0,
            closed: str | None = None,
            label: str | None = None,
            convention: str = "start",
            kind: str | None = None,
            loffset=None,
            base: int | None = None,
            on=None,
            level=None,
            origin: str | pd_typing.TimestampConvertibleTypes = "start_day",
            offset: pd_typing.TimedeltaConvertibleTypes | None = None,
            agg=""
    ) -> pd.Series:
        """
        resample的时候用这个函数, 保证内置的类型会被正确的resample
        其他参数和标准的resample相同
        :param agg: 如果是自定义的数据, 需要指定resample的统计算法. 比如sum, mean等
        :return: 重新采样后的数据
        """
        resampler = super().resample(rule, axis, closed, label, convention, kind, loffset, base, on, level, origin,
                                     offset)
        agg_method = get_agg_by_type(self.line_type)
        if agg_method == "":
            agg_method = DEFAULT_AGG_METHOD
        if self.line_type == LineTypeEnum.other:
            if agg == "":
                agg_method = DEFAULT_AGG_METHOD
            else:
                agg_method = agg
        return resampler.agg(agg_method)

    def fillna(
            self,
            value: object | pd_typing.ArrayLike | None = None,
            method: pd_typing.FillnaOptions | None = None,
            axis=None,
            inplace=False,
            limit=None,
            downcast=None,
    ) -> pd.Series:
        """
        根据类型填充空白数据, 参数和fillna相同
        如果是内置类型, method和value参数会被忽略, 按照内置的方式来填充.
        :return:
        """
        param = get_fillna_param(self.line_type, method, value)
        method = param["method"]
        value = param["value"]
        return super().fillna(
            value=value,
            method=method,
            axis=axis,
            inplace=inplace,
            limit=limit,
            downcast=downcast,
        )

    @staticmethod
    def from_series(series: pd.Series, row_index: 0) -> "Line":
        line_type = LineTypeEnum.other
        try:
            line_type = LineTypeEnum[series.name]
        except:
            line_type = LineTypeEnum.other
        line = series.copy(deep=True)
        line.cursor = row_index
        setattr(line, "line_type", line_type)
        return line

    def get_by_cursor(self, i):
        real_index = self.cursor + i
        if real_index < 0 or real_index >= self.index.size:
            raise IndexError("index out of range")
        return self.iloc[real_index]


# =====================lines================

class Lines(pd.DataFrame, Cursorable):
    def __init__(
            self,
            data=None,
            index: pd_typing.Axes | None = None,
            columns: pd_typing.Axes | None = None,
            dtype: pd_typing.Dtype | None = None,
            copy: bool | None = None,
    ):
        if (index is not None) and (not isinstance(index, pd.core.indexes.datetimes.DatetimeIndex)):
            raise ZelosError("index must be datetime")
        # 根据line的类型, 添加列
        line_data = dict()
        if data is not None:
            if isinstance(data, list):
                for item in data:
                    Lines.__set_line_name_by_object(item, line_data)
            elif isinstance(data, dict):  # 自己通过dict指定名字
                line_data = data
            else:
                Lines.__set_line_name_by_object(data, line_data)
        super().__init__(line_data, index, columns, dtype, copy)
        Cursorable.__init__(self)

    @staticmethod
    def __set_line_name_by_object(item, line_data):
        if isinstance(item, Line) and item.line_type != LineTypeEnum.other:
            line_data[item.line_type.name] = item
        elif isinstance(item, pd.Series) and item.name:
            line_data[item.name] = item
        else:
            line_data["Column" + str(len(line_data.keys()))] = item

    def append_column(self, name: str, column: Line):
        '''
        给数据表添加一列
        :param name: 列名称
        :param column: 数据, 类型是pandas.Series, 同时, 索引必须是时间序列
        :return:
        '''
        if not isinstance(column.index, pd.core.indexes.datetimes.DatetimeIndex):
            raise ZelosError("index must be datetime")
        if self.data.columns.size == 0:
            self.data.index = column.index
        self.data[name] = column

    def fillna(
            self,
            value: object | pd_typing.ArrayLike | None = None,
            method: pd_typing.FillnaOptions | None = None,
            axis: pd_typing.Axis | None = None,
            inplace: bool = False,
            limit=None,
            downcast=None,
    ) -> pd.DataFrame | None:
        new_df = self.copy(False)

        # 先填补close的空缺
        if LineTypeEnum.closeTick.name in new_df.columns:
            new_df[LineTypeEnum.closeTick.name] = new_df[LineTypeEnum.closeTick.name].fillna(value=None, method="ffill",
                                                                                             axis=axis,
                                                                                             inplace=inplace,
                                                                                             limit=limit,
                                                                                             downcast=downcast)
        for column_name in new_df.columns:
            if column_name == LineTypeEnum.closeTick.name:
                continue
            line_type = LineTypeEnum.safe_get(column_name)
            if line_type == "":
                new_df[column_name] = new_df[column_name].fillna(value, method, axis, inplace, limit, downcast)
            else:
                param = get_fillna_param(line_type, method, value)
                current_method = param["method"]
                current_value = param["value"]
                # tick相关的, 填补空缺都用close tick, 如果没有close tick, 默认用之前的.
                if line_type in [LineTypeEnum.openTick, LineTypeEnum.highestTick,
                                 LineTypeEnum.lowestTick] and LineTypeEnum.closeTick.name in new_df.columns:
                    current_method = None
                    current_value = new_df[LineTypeEnum.closeTick.name]
                new_df[column_name] = new_df[column_name].fillna(value=current_value, method=current_method, axis=axis,
                                                                 inplace=inplace,
                                                                 limit=limit,
                                                                 downcast=downcast)
        new_lines = Lines.from_dataframe(new_df)
        new_lines.cursor = self.cursor
        return new_lines

    def resample_by_type(
            self,
            rule,
            axis=0,
            closed: str | None = None,
            label: str | None = None,
            convention: str = "start",
            kind: str | None = None,
            loffset=None,
            base: int | None = None,
            on=None,
            level=None,
            origin: str | pd_typing.TimestampConvertibleTypes = "start_day",
            offset: pd_typing.TimedeltaConvertibleTypes | None = None,
            agg=dict()
    ) -> "Lines":
        resampler = super().resample(rule, axis, closed, label, convention, kind, loffset, base, on, level, origin,
                                     offset)
        agg_dict = dict()
        for column_name in self.columns:
            column_type = LineTypeEnum.safe_get(column_name)
            agg_method = get_agg_by_type(column_type)
            if agg_method == "":
                if column_name in agg:
                    agg_method = agg[column_name]
                else:
                    agg_method = DEFAULT_AGG_METHOD
            agg_dict[column_name] = agg_method
        df = resampler.agg(agg_dict)
        new_lines = Lines.from_dataframe(df)
        new_lines.cursor = 0
        return new_lines

    def get_line(self, index: int = None, name: str = None) -> Line:
        if not index and not name:
            raise ZelosError("must use index or name")
        if index:
            return Line.from_series(self.iloc[:, index], self.cursor)
        elif name:
            return Line.from_series(self[name], self.cursor)

    def get_by_cursor(self, i):
        real_index = self.cursor + i
        if real_index < 0 or real_index >= self.index.size:
            raise IndexError("index out of range")
        return self.iloc[real_index]

    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> "Lines":
        new_lines = Lines(index=df.index)
        new_lines._mgr = df._mgr
        return new_lines

    @staticmethod
    def load_downloaded(path: str) -> "Lines":
        df = pd.read_csv(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        return Lines.from_dataframe(df)
