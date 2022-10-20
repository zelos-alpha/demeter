from datetime import datetime, timedelta

from ._typing import MarketData


class TextUtil(object):
    @staticmethod
    def cut_after(text: str, symbol: str) -> 'str':
        index = text.find(symbol)
        return text[0:index]


class TimeUtil(object):
    @staticmethod
    def get_minute(time: datetime) -> datetime:
        return datetime(time.year, time.month, time.day, time.hour, time.minute, 0)


class HexUtil(object):
    @staticmethod
    def to_signed_int(h):
        """
        Converts hex values to signed integers.
        """
        s = bytes.fromhex(h[2:])
        i = int.from_bytes(s, 'big', signed=True)
        return i


class DataUtil(object):

    @staticmethod
    def fill_missing(data_list: [MarketData]) -> list:
        if len(data_list) < 1:
            return data_list
        # take the first minute in data. instead of 0:00:00
        # so here will be a problem, if the first data is 0:03:00, the first 2 minutes will be blank
        # that's because there is no previous data to follow
        # those empty rows will be filled in loading stage
        index_minute = data_list[0].timestamp
        new_list = []
        data_list_index = 0

        start_day = data_list[0].timestamp.day
        while index_minute.day == start_day:
            if (data_list_index < len(data_list)) and (index_minute == data_list[data_list_index].timestamp):
                item = data_list[data_list_index]
                data_list_index += 1
            else:
                item = MarketData()
                item.timestamp = index_minute
            prev_data = new_list[len(new_list) - 1] if len(new_list) - 1 >= 0 else None
            # if no previous(this might happen in the first minutes) data, this row will be discarded
            if item.fill_missing_field(prev_data):
                new_list.append(item)
            index_minute = index_minute + timedelta(minutes=1)

        return new_list
