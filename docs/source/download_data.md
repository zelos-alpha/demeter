# Download data

Backtesting need data from real market. For DEFI protocol, market data can be restored from transaction event log on
chain.

We create demeter-fetch to do this job. Tutorial is [here](https://github.com/zelos-alpha/demeter-fetch)

To run the backtest, you need to download the data in minute type.

Market data files are organized by date, one file per day.
In each file, timestamp index starts at 00:00:00, and ends at 23:59:00. So there are 1440 rows in each csv file (because
a day has 1440 minutes) 
