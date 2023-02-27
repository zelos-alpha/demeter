from typing import List

import pandas as pd
from matplotlib.pylab import plt
import matplotlib.dates as mdates

from demeter import MarketInfo
from demeter.broker import AccountStatus


def plotter(account_status_list: List[AccountStatus]):
    net_value_ts = [status.net_value for status in account_status_list]
    time_ts = [status.timestamp for status in account_status_list]
    plt.plot(time_ts, net_value_ts)
    plt.show()


def plot_position_return_decomposition(account_status: pd.DataFrame, price: pd.Series, market: MarketInfo):
    fig, value_ax = plt.subplots()
    day = mdates.DayLocator(interval=2)

    price_ax = value_ax.twinx()
    price_ax.xaxis.set_major_locator(day)
    price_ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    value_ax.set_xlabel('time')
    value_ax.set_ylabel('value', color='g')
    price_ax.set_ylabel('price', color='b')

    net_value_ts = list(account_status.net_value)
    time_ts = list(account_status.index)
    price_ts = list(price)

    value_in_position = account_status[market.name + ".net_value"]
    value_in_account = account_status["usdc"] + account_status["eth"] * price

    value_ax.plot(time_ts[1:], net_value_ts[1:], 'g-', label="net value")
    value_ax.plot(time_ts, value_in_position, 'r-', label="value in position")
    value_ax.plot(time_ts, value_in_account, 'b-', label=" value in broker account")
    price_ax.plot(time_ts, price_ts, label="price")
    fig.legend()
    fig.show()
