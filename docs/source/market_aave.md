# Aave market.

Aave market can simulate common transactions in Aave V3, including:

* Supply: Deposition tokens to aave pool, you have to specify collateral or not
* Withdraw: Withdraw the token deposited.
* Borrow: Borrow assets, you can choose interest rate mode.
* Repay: repay delt.

Meanwhile, the Health factor will be calculated in iterations of backtesting. If the health factor is below 1, demeter
will liquidate the debt.

Liquidate debts of other users is not supported yet.

Flash debt is also not supported.

An Aave market instance corresponds to an aave v3 pool. In the real world, one pool for each chain, and a pool has many
tokens. When you do backtesting on aave, you can choose tokens you need, and only download data of used tokens.

Aave data can also be downloaded by demeter-fetch, one file for a token and one day. Data is also resampled minutely.

Aave data is extracted from ReserveDataUpdated event of AAVE pool. it contains

* liquidityRate
* stableBorrowRate
* variableBorrowRate
* liquidityIndex
* variableBorrowIndex

Because you need to set up multiple tokens, aave market data use multiple column index. This makes accessing the data a
bit
complicated

Data of aave market is dataframe, too, and columns are organized by token, like this:

|                     | WETH           |                    |                      |                 |                       |
|---------------------|----------------|--------------------|----------------------|-----------------|-----------------------|
| block_timestamp     | liquidity_rate | stable_borrow_rate | variable_borrow_rate | liquidity_index | variable_borrow_index |
| 2023-08-15 00:00:00 | 0              | 0                  | 0                    | 1               | 1                     |
| 2023-08-15 00:01:00 | 0              | 0                  | 0                    | 1.001           | 1.001                 |
| 2023-08-15 00:02:00 | 0              | 0                  | 0                    | 1.002           | 1.002                 |
| 2023-08-15 00:03:00 | 0              | 0                  | 0                    | 1.003           | 1.003                 |
| 2023-08-15 00:04:00 | 0              | 0                  | 0                    | 1.004           | 1.004                 |

So if you want to read an element in this dataframe, such as liquidity_rate of weth, you should
do: ```data.iloc[0]["WETH"]["liquidity_rate"]```,
and if you access a column, you can do ```data["WETH"]["liquidity_rate"]```

If you append a new column to data, the dataframe will be

|                     | WETH           |                    |                      |                 |                       | new_column |
|---------------------|----------------|--------------------|----------------------|-----------------|-----------------------|------------|
| block_timestamp     | liquidity_rate | stable_borrow_rate | variable_borrow_rate | liquidity_index | variable_borrow_index |            |
| 2023-08-15 00:00:00 | 0              | 0                  | 0                    | 1               | 1                     | 1          |
| 2023-08-15 00:01:00 | 0              | 0                  | 0                    | 1.001           | 1.001                 | 2          |
| 2023-08-15 00:02:00 | 0              | 0                  | 0                    | 1.002           | 1.002                 | 3          |
| 2023-08-15 00:03:00 | 0              | 0                  | 0                    | 1.003           | 1.003                 | 4          |
| 2023-08-15 00:04:00 | 0              | 0                  | 0                    | 1.004           | 1.004                 | 5          |

This brings a little trouble.

If you access an element in new_column by access row first. ```data.iloc[0]["new_column"]``` will return a series
instead of an item, so ```data.iloc[0]["new_column"][0]``` will work. A

nd if you access by column first, ```data["new_column"]``` will return a series, so ```data["new_column"].iloc[0]```
will work, no need to write extra [0]

It would be a trouble if you read market data of all tokens. It is preferred to set data with set_token_data() and
load_data()

Another important thing is, you have to set risk parameter when create a market instance. Risk parameter defines the liquidation threshold and ltv of all tokens. Risk parameter files can be downloaded form https://www.config.fyi, format is csv. One csv file for each chain.