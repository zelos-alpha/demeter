from enum import Enum
from typing import NamedTuple, Dict

import pandas as pd
from pandas import _typing as pd_typing

from ._typing import DemeterError

DEFAULT_AGG_METHOD = "first"


class Rule(NamedTuple):
    agg: str | None
    fillna_method: str | None
    fillna_value: int | None


EMPTY_RULE = Rule(None, None, None)


def get_line_rules_safe(key: str) -> Rule:
    if key in LINE_RULES:
        return LINE_RULES[key]
    else:
        return EMPTY_RULE


class LineTypeEnum(Enum):
    """
    predefined column, used to define fillna method.
    """
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


LINE_RULES = {
    LineTypeEnum.timestamp.name: EMPTY_RULE,
    LineTypeEnum.netAmount0.name: Rule("sum", None, 0),
    LineTypeEnum.netAmount1.netAmount0: Rule("sum", None, 0),
    LineTypeEnum.closeTick.name: Rule("last", "ffill", None),
    LineTypeEnum.openTick.name: Rule("first", "ffill", None),
    LineTypeEnum.lowestTick.name: Rule("min", "ffill", None),
    LineTypeEnum.highestTick.name: Rule("max", "ffill", None),
    LineTypeEnum.inAmount0.name: Rule("sum", None, 0),
    LineTypeEnum.inAmount1.name: Rule("sum", None, 0),
    LineTypeEnum.currentLiquidity.name: Rule("sum", "ffill", None),
}


class Cursorable(object):
    """
    give Lines or line a cursor. which help to access current row with index 0 in a loop.  eg:

    if data= [1,2,3,4,5], self.cursor=0

    * data.get_by_cursor[0]==1
    * data.get_by_cursor[2]==3
    * data.get_by_cursor[4]==5

    if self.cursor=2

    * data.get_by_cursor[-2]==1, access previse row with negative index,
    * data.get_by_cursor[0]==3, access current row with 0,
    * data.get_by_cursor[2]==5, access after row with positive index

    if self.cursor=4

    * data.get_by_cursor[-4]==1
    * data.get_by_cursor[-2]==3
    * data.get_by_cursor[0]==5
    """

    def __init__(self):
        self.cursor = 0

    def row_length(self):
        """
        get total length

        """
        return self.index.size

    def get_cursor_range(self):
        """
        get legal range for index
        :return: min, max
        """
        return -self.cursor, self.index.size - self.cursor - 1

    def move_cursor_to_next(self):
        """
        move cursor to on_bar index
        """
        self.cursor += 1

    def reset_cursor(self):
        """
        reset cursor to zero
        """
        self.cursor = 0

    def get_by_cursor(self, i):
        """
         access row by cursor

         :param i: index
         :type i: int
         :return: selected row, in form of pd.Series
         """
        real_index = self.cursor + i

        if real_index < 0 or real_index >= self.index.size:
            raise IndexError("index out of range")
        return self.iloc[real_index]


class Line(pd.Series, Cursorable):
    """
    a column of data, inherit from pandas.Series

    and it has two additional function:

    * it has a property of column type. if the column type is predefined, then fillna and resample method is not changeable
    * it provide cursor.

    note: index of this Series must be datetime
    """

    def __init__(
            self,
            data=None,
            index=None,
            dtype: pd_typing.Dtype | None = None,
            name=None,
            copy: bool = False,
            fastpath: bool = False
    ):

        if not isinstance(index, pd.core.indexes.datetimes.DatetimeIndex):
            raise DemeterError("index must be datetime")
        super().__init__(data, index, dtype, name, copy, fastpath)
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
            agg=DEFAULT_AGG_METHOD
    ) -> pd.Series:
        """
        with this method, predefined type will be resampled correctly, other param is the same to Series.resample()

        :param agg: if line_type is other, should define resample method, such as sum, mean
        :return: resampled data
        """
        resampler = super().resample(rule, axis, closed, label, convention, kind, loffset, base, on, level, origin,
                                     offset)
        rule = get_line_rules_safe(self.name)
        agg_method = rule.agg
        if agg_method is None:
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
        fill empty item. param is the same to pandas.Series.fillna

        if line type is predefined, method and value will be omitted, and data will be filled as predefined

        """
        param = get_line_rules_safe(self.name)
        if param.fillna_method:
            method = param.fillna_method
        if param.fillna_value:
            value = param.fillna_value
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
        """
        convert serise to line, line type will be defined by series.name

        :param series: series to process
        :type series: pd.Series
        :param row_index: new row index
        :type row_index: int
        :return: converted Line
        :rtype: Line
        """
        line = series.copy(deep=True)
        line.cursor = row_index
        return line


class Lines(pd.DataFrame, Cursorable):
    """
    a data table, inherit from pandas.DataFrame

    and it has two additional function:

    * it has a property of column type. if the column type is predefined, then fillna and resample method can not change
    * it provide cursor. assistant to access current row in a loop

    note: index of this DataFrame must be datetime
    """

    def __init__(
            self,
            data=None,
            index: pd_typing.Axes | None = None,
            columns: pd_typing.Axes | None = None,
            dtype: pd_typing.Dtype | None = None,
            copy: bool | None = None,
    ):
        if (index is not None) and (not isinstance(index, pd.core.indexes.datetimes.DatetimeIndex)):
            raise DemeterError("index must be datetime")
        # add line by type
        line_data = dict()
        if data is not None:
            if isinstance(data, list):
                for item in data:
                    Lines.__set_line_name_by_object(item, line_data)
            # after line is added, it's type will become series, so we identify its type by name
            elif isinstance(data, dict):
                line_data = data
            else:
                Lines.__set_line_name_by_object(data, line_data)
        super().__init__(line_data, index, columns, dtype, copy)
        Cursorable.__init__(self)

    @staticmethod
    def __set_line_name_by_object(item, line_data):
        """
        after line is added, it's type will become series, so we set their type to name.
        """
        if isinstance(item, pd.Series) and item.name:
            line_data[item.name] = item
        else:
            line_data["Column" + str(len(line_data.keys()))] = item

    def append_column(self, name: str, column: Line):
        """
        add a column to Lines

        :param name: column name
        :type name: str
        :param column: column to add, type must be line, or pandas.Series, but index of Series should be datetime
        :type: Line

        """
        if not isinstance(column.index, pd.core.indexes.datetimes.DatetimeIndex):
            raise DemeterError("index must be datetime")
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
        """
        fill empty item. param is the same to pandas.Series.fillna

        if column name is predefined, method and value will be omitted, and data will be filled as predefined

        """
        new_df = self.copy(False)

        # fill close tick first, it will be used later.
        if LineTypeEnum.closeTick.name in new_df.columns:
            new_df[LineTypeEnum.closeTick.name] = \
                new_df[LineTypeEnum.closeTick.name].fillna(value=None,
                                                           method=get_line_rules_safe(
                                                               LineTypeEnum.closeTick.name).fillna_method,
                                                           axis=axis,
                                                           inplace=inplace,
                                                           limit=limit,
                                                           downcast=downcast)
        for column_name in new_df.columns:
            if column_name == LineTypeEnum.closeTick.name:
                continue
            rule = get_line_rules_safe(column_name)
            if not rule.fillna_method and not rule.fillna_value:
                new_df[column_name] = new_df[column_name].fillna(value, method, axis, inplace, limit, downcast)
            else:
                current_method = rule.fillna_method if rule.fillna_method else method
                current_value = rule.fillna_value if rule.fillna_value else value
                # all tick related field will be filled with close_tick.
                if column_name in [LineTypeEnum.openTick.name,
                                   LineTypeEnum.highestTick.name,
                                   LineTypeEnum.lowestTick.name] and LineTypeEnum.closeTick.name in new_df.columns:
                    current_method = None
                    current_value = new_df[LineTypeEnum.closeTick.name]
                new_df[column_name] = new_df[column_name].fillna(value=current_value, method=current_method, axis=axis,
                                                                 inplace=inplace,
                                                                 limit=limit,
                                                                 downcast=downcast)
        new_lines = Lines.from_dataframe(new_df)
        new_lines.cursor = self.cursor
        return new_lines

    def get_line(self, index: int = None, name: str = None) -> Line:
        """
        get a column of Lines

        :param index: column index, if index is set, name param will be override
        :type index: int
        :param name: column name
        :type name: str
        :return: selected column
        :rtype: Line
        """
        if not index and not name:
            raise DemeterError("must use index or name")
        if index:
            return Line.from_series(self.iloc[:, index], self.cursor)
        elif name:
            return Line.from_series(self[name], self.cursor)

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
            agg: Dict[str, str] = {}
    ) -> "Lines":
        """
        with this method, predefined column will be resampled correctly, other param is the same to Series.resample()

        :param agg: if line name is not predefined, should define resample method, such as sum, mean
        :return: resampled data
        """
        resampler = super().resample(rule, axis, closed, label, convention, kind, loffset, base, on, level, origin,
                                     offset)
        agg_dict = {}
        for column_name in self.columns:
            rule = get_line_rules_safe(column_name)
            agg_method = rule.agg
            if agg_method is None:
                if column_name in agg:
                    agg_method = agg[column_name]
                else:
                    agg_method = DEFAULT_AGG_METHOD
            agg_dict[column_name] = agg_method
        df = resampler.agg(agg_dict)
        new_lines = Lines.from_dataframe(df)
        new_lines.cursor = 0
        return new_lines

    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> "Lines":
        """
        convert pandas.DataFrame to Lines. this method will copy inner variable to new Lines.

        :param df: dataframe to convert
        :type df: DataFrame
        :return: Lines
        :rtype: Lines
        """
        new_lines = Lines(index=df.index)
        new_lines._mgr = df._mgr
        return new_lines

    @staticmethod
    def load_downloaded(path: str) -> "Lines":
        """
        load data which saved by downloader as lines
        :param path: csv file path
        :type path: str
        :return: loaded data
        :rtype: Lines
        """
        df = pd.read_csv(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        return Lines.from_dataframe(df)
