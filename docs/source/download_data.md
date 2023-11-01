# Download data

Backtesting need data from real market. For DEFI protocol, market data can be restored from transaction event log on chain. 

We create demeter-fetch to do this job. Tutorial is [here](https://github.com/zelos-alpha/demeter-fetch)

In order to run the backtest, you need to download the data in minute type.

Market data files are organized by date, one file per day. In each file, there are 1440 rows(because a day has 1440 minutes) 
