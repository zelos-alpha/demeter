from typing import List

from matplotlib.pylab import plt

from demeter import AccountStatus

def plotter(account_status_list:List[AccountStatus]):
    net_value_ts = [status.net_value.number for status in account_status_list]
    time_ts = [status.timestamp for status in account_status_list]
    plt.plot(time_ts, net_value_ts)
    plt.show()
