from typing import List

from matplotlib.pylab import plt

from demeter import AccountStatus

def plotter(account_status_list:List[AccountStatus]):
    net_value_ts = [status.net_value for status in account_status_list]
    time_ts = [status.timestamp for status in account_status_list]
    plt.plot(time_ts, net_value_ts)
    plt.show()


def plot_position_return_decomposition(account_status_list:List[AccountStatus]):
    fig, value_ax = plt.subplots()

    price_ax = value_ax.twinx()

    value_ax.set_xlabel('time')
    value_ax.set_ylabel('value', color='g')
    price_ax.set_ylabel('price', color='b')

    net_value_ts = [status.net_value for status in account_status_list]
    time_ts = [status.timestamp for status in account_status_list]
    price_ts = [ status.price for status in account_status_list ]

    value_in_account = [status.net_value for status in account_status_list]
    value_in_position =  [ status.base_in_position+status.quote_in_position*status.price for status in account_status_list]

    value_ax.plot(time_ts,net_value_ts,'g-',labels="net value")
    value_ax.plot(time_ts,value_in_position,'r-',labels="value in position")
    value_ax.plot(time_ts,value_in_account,'b-',labels=" value_in broker account")
    price_ax.plot(time_ts,price_ts,labels="price")
    fig.legend()
    fig.show()
