# Modules

## Actuator

Actuator is the commander of backtesting. It controls the backtesting process. The most important function is run(), all
backtesting processes are managed by run().

The process of a backtesting is

* Reset actuator
* Initialize strategy (set a Strategy instance to actuator.strategy, then run strategy.initialize())
* Process each row in data
    * Prepare data in this iteration
    * Run trigger
    * Run strategy.on_bar()
    * Update market, e.g., calculate fee earned of uniswap position
    * Run strategy.after_bar()
    * Get latest account status(balance)
    * Notify actions
* Run evaluator indicator
* Run strategy.finalize()
* Output result if required

Actuator also manages affairs after backtesting, such as output (to console or to files), strategy evaluating
indicators.

## broker

A broker is the one who arranges transactions between user and market.
Which means users keep their assets with a broker and manage their positions through the broker.

Broker has two important attributes, asset and market.

### Broker.assets

It's the cash held by the user. Related functions include

* assets: Query all cash holds by user
* get_token_balance/get_token_balance_with_unit: Query asset of a token.
* add_to_balance/set_balance/subtract_from_balance: Manage asset amounts.

Another thing you need to notice is, balance of token can be negative if you set allow_negative_balance=True.

### Broker.markets

It's the place to invest positions. Related functions include

* markets: Query all available markets.
* add_market: set a new market to broker.

### Broker.get_account_status

Account status is the financial situation of user, includes:

* Amount and value of all tokens. that is, the cash held by user.
* Value of all positions in each market.
* Total net worth, that is the sum of previous items

## market

The Market is the place to invest in positions. Currently, demeter support two kinds of markets, Uniswap v3 and aave v3.

Markets must inherit form broker.Market class. It has the following important attributes/functions

* load_data/data_path/data: Data is used to simulate real market. Data are abstracted form event log, and kept in csv.
  Markets can load those csv as Dataframe.
* market_status/price_status: market data and price **at this iteration**
* get_market_balance: get net value in these markets, it's the sum of all positions.

The Market is stateless, it just keeps positions and calculates their value. The update of market is driven by
set_market_status. In each iteration, the actuator will set the market_status of this minute to market. Then call
market.update() to calculate fee income at this minute.

## Indicators

Indicators are some calculators to enhance the data. Demeter provides the following indicator.

* moving average: include simple_moving_average and exponential_moving_average, it's used to analyze data points by
  creating a series of averages of different selections of the full data set.
* volatility: Demeter only supports realized_volatility.

Those indicators can be used before backtesting starts. You can append a simple moving average column to data in
strategy.initialize(), and then use the column in Strategy.on_bar() or triggers

## Price

Price is an important indicator of value. To calculate the value of an asset, you need to set the price
attribute for the actuator. There are many ways to get prices, but there is no silver bullet.

* Data provider like coingecko: The api interface is chargeable, and usually only hourly pricing data is available. you
  will have to resample to minutely before backtesting.
* Oracle contract: Requires very complex code.
* Defi protocol like uniswap: You can get price from event log, and luckily, demeter-fetch can do this work, and save it
  in .minute.csv. But the problem is, you have to find a stable coin pool first, and you have to ensure the price of
  stable coin is not de-anchored

The type of price is dataframe, and have to look like this

|                     | WETH    | USDC |
|---------------------|---------|------|
| 2023-08-13 00:00:00 | 1848.12 | 1    |
| 2023-08-13 00:01:00 | 1848.12 | 1    |

Its index is timestamp with an interval of minute. And one column for each token, column is token name in the upper
case.

## Strategy

User's strategy must be inherited form demeter.Strategy class. For ease of use, strategy class preset a lot of
functions.

* initialize: Be called before iteration. Here you can add indicator to data, or set some class variables.
* finalize: Be called after iteration, at this time, backtesting has finished. so you can evaluate the strategy.
* on_bar: Be called in the iteration, but before markets are updated.
* after_bar: Be called in the iteration, but after markets are updated.

The type of those functions is RowData. It's the status of that moment. It has the following attributes:

* timestamp: Time of this iteration, for initialize(), it is 00:00:00 in the start date. for finalize(), it's 23:59:59
  at the end date.
* row_id: index of this iteration, start from 0
* prices: price of tokens at this minute
* market_status: status of markets at this minute

As the interval of market data is minute, so one iteration means one minute.

If you want to get notified when any transaction was made. You can override notify function. Its parameter is "action"
in BaseAction type. All actions thrown are subclass of BaseAction. You can check its by action_type
attribute to distinguish different actions, and check market attribute to know which market throws this action

## account status and market status

In demeter, status is stand for data at this moment.

AccountStatus is the values held by user, including cash (that is balance of broker), positions (managed by market), and
their sum(total net value).

Market status indicates status of market at this moment. For uniswap, it is the total liquidity of the pool, current
quote token price, etc. For aave, it is liquidation_index and apy of a token.

## Results

After backtesting, it's time to check the result.

The most intuitive way to learn the result is to print them in the console. Actuator.run() has an output parameter
whose default value is True.

If set to True, demeter will print the following results at the end of backtesting:

1. Account status (including balances and positions) at the end of the back test.
2. Balance change during back test.
3. If evaluating indicator is enabled, will print evaluating of strategy.

The decimals will be outputed with unit, such as 1234.56 usdc/weth(price), 1234 usdc(amount). This is thanks to
UnitDecimal class. It is an extend for Decimal. This design helps minimize confusion over amounts

After run() funtion finished, you can access the latest value of account with ```self.get_account_status```, and access
the history of account value by ```self.get_account_status_dataframe()```

If you want to save results to files, you cancall save_result() function. Actions (transactions) made in the backtesting
will be kept in pkl and json. Among them, json is used for human reading. And pkl is used to load by python in future
analysis. As actions have different attributes, they can't be saved as csv.

## evaluating indicator

Demeter also provide evaluating indicator for backtesting. Includes

* annualized_returns
* benchmark_returns
* max_draw_down
* net_value
* profit
* net_value_up_down_rate
* eth_up_down_rate
* position_fee_profit
* position_fee_annualized_returns
* position_market_time_rate