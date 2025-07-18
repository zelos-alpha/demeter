# Ver 1.1.4

* fix issue in check aave repay amount
* add on_error function in Strategy which will be called on exceptions
* fix duplicate values in ActionTypeEnum values


# Ver 1.1.3

* Add openinterest in gmx v2 minute file.
* [Breaking change]remove complex statistic column in gmx v2 balance. including pending_pnl, realized_profit,
  realized_pnl, open_interest_in_tokens to speed up the calculation

# Ver 1.1.2

* [Breaking change] Rename realizedNetYield in GMX V2 minute file to realizedProfit, rename net_yield to realized_profit
* Add profit and pnl column for gmx v2 market.

# Ver 1.1.1

* Add pending pnl and net yield for GMX v2 market

# Ver 1.1.0

* Add gmx v2 market
* Add swap in broker, in case there is no swapble market in backtest
* Show net value in process bar during backtest
* AAVE market:
    * [Breaking change] Improve aave market, you can download risk parameter with demeter-fetch
    * Remove stable rate borrowing in aave v3
    * [Breaking change] remove supply and borrow key, just use token instead, because there are only one interest rate.
    * add ltv and max_ltv in market balance

# Ver 1.0.2

Improve performance in deribit market. You should clear cache in your first running to make it work.

# Ver 1.0.1

[Breaking change] Remove callback in BacktestManager, because if subprocess return actuator,
it will cause object copy between subprocess and main process, which will cost a lot of time.
You can do saving or calculating performance in Strategy.finialize().

# Ver 1.0.0

* Add `BacktestManager` who can start multiple backtest in one or multiple subprocesses.
* [Breaking change] RowData class in strategy was renamed to Snapshot
* Gmx market:
    * [Breaking change]market type was change to `gmx_v1`

# Ver 0.8.3

* fix errors in deribit market.
* _check_transaction function in deribit market was set to public
* [Breaking change] Delta and gamma in deribit option market was changed from average value to total value
* Add cash value in AccountStatus of broker

# Ver 0.8.2

* change order when saving backtest result
* data and price has updated. The value in the beginning of the minute will follow the value in the last minute(In old
  version it will be decided by
  the first transaction in this minute.)
* fix issues in data cache(when feather file is lost, a error will be raised)
* show market name when loading data
* add lp net value for uniswap market balance
* deribit: convert type of t when loading csv
* fix other bugs

# Ver 0.8.0

* add GMX Market

# Ver 0.7.7

* Uniswap V3:Add get position status, this will help to calculate amounts and values of a liqudity position
* [Breaking change] Uniswap V3: Update delta gamma calucation, add get_greeks in helper.
* Add start liquidity index for aave position
* Add net value for metrics
* Add cache to backtest data
* You can set account status file format in actuator.save_result()

# Ver 0.7.6

* For uniswap v3, when price is in and out of price range in this minute, fee will be calculated more accurately

# Ver 0.7.5

* Fix bugs in aave

# Ver 0.7.4

* [Breaking change]Value of ChainType enum has changed to chain id.
* Add base_token to UniV3Pool class

# Ver 0.7.3

* update dependency according to issue [here](https://github.com/zelos-alpha/demeter/issues/16)

# Ver 0.7.2

* Add comment to action.get_output_str()
* When exception was raised in backtesting, demeter will save actions and account status
* Deribit market add max_mark_price_multiple, to prevent buying options too expensive to mark price
* Update strategy.finalize(), so you can operate account_status_df in strategy.finalize().
* Fix issues that strategy.account_status_df is empty

# Ver 0.7.1

* add estimate_cost for deribit market, so you can estimate how much to deposit to deribit before trade.
* Add estimate_amount and estimate_liquidity for uniswap market
* fix bugs

# Ver 0.7.0

* Deribit market:
    * Deribit market accept missing data now
    * [Breaking change]Balance in Deribit market has updated, now equity is included, count of puts and calls are
      removed.
    * [Breaking change]Deribit market has its own account, if you want to trade in deribit, you have to deposit token to
      deribit market first.
    * Deribit market can load files with a process bar.
    * Deribit market allow load a single pkl data instead every csv data, because load csv data will cost a long time,
* Backtest result
    * Add result package, keep utils and typings for backtest result
    * mertics package are moved to result package, so test result generated by old version can not be loaded.
    * metrics add backtest period.
    * metrics add a helper function(round_results) because not all metric is decimal
* Add interval for actuator, so you can backtest with other freq.
* When save result, you can specify decimals in csv file.

# Ver 0.6.3

* Out of date triggers will be removed. so it's free to add triggers during backtesting
* Add logs in backtest result, if you call self.log in strategy, you can leave a log in backtest result file.
* [Breaking change]Add fee in return of buy and sell function in deribit market. So return has changed
  from ```List[Order]``` to ```Tuple[List[Order],Decimal]```

# Ver 0.6.2

* Fix error in volatility calculation
* Update backtesting description, add backtest time
* Update metrics

# Ver 0.6.1

* [breaking change]output result has updated, .action.json and action.pkl is removed. Instead, backtest description is
  added. It is a pkl file, and contains initial status and markets description and actions, etc.
* Add a new parameter "file_name" to actuator.save_result, so you can specific file name of backtest result
* broker and markets have quote token now, quote token can be different among markets. It can be set in
  actuator.set_price()
* external_price parameter in UniLpMarket.get_market_balance has removed, because net value returned by unilpmarket
  should be quoted by quote token of this pool
* [breaking change]When adding liquidity, tick should be trim according to tick spacing. Call nearest_usable_tick to get
  an available tick

# Ver 0.6.0

* [breaking change]Update minimal python version to 3.11
* [breaking change]Update get_account_status_df function to account_status_df property. account_status_df is available
  after backtest finished.
* account_status_df contains token price now
* Add "comment_last_action" function, you can add comment to last action, If you want to record parameters or reason of
  this transaction, call comment_last_action() in strategy
* [breaking change]Account status df use multiindex column now.
* [breaking change]Actuator.output() has renamed to "print_result", "Output" parameter in Actuator.run() has renamed
  to "print".
* [breaking change]evaluating_indicator has been move to an independent module: metrics, and it's easy to use now. Also,
  some new performance metrics is added. Including sharp raito, alpha, beta.

# Ver 0.5.3

* add "print action" setting in actuator
* add get_output_str for action types
* add pending time to PeriodTrigger, so you can trigger at specific time of a day
* fix bug: when daily minute file is empty, an error will be thrown
* Multiple improves in uniswap market.
    * add price range to position
    * fix bug: base token amount was actually value in add_liquidity_by_value

# Ver 0.5.2

Add function for uniswap market: add_liquidity_by_value, With function, you can define how much to add liquidity from
your balance.
This function will calculate token amount needed, and do swap to ensure there are enough token. Swap fee is also taken
into account.
If you want to add all your balance into liquidity, this function is very useful to help you maximize your liquidity.

# Ver 0.5.1

* Fix issue: Precision setting not working in console output
* Fix issues in uniswap market:
    * in even_rebalance function, balance calculation did not count swap fee
    * [breaking change]Base and quote is reversed in older version. To accommodate this change, you need to:
        1. When creating a uniswap market instance, is_token0_base has changed to is_token0_quote, You don't have to
           change anything unless you init with keywords, e.g. You have to change is_token0_base here: UniLpMarket(
           is_token0_base=True)
        2. In add_liquidity and add_liquidity_by_tick function, order of quote_max_amount and base_max_amount is
           changed.
* Update uniswap market:
    * Add swap function. Keep in line with the contract.
    * Decimal precision has raised from 28 to 36
    * [breaking change]Update function name in Uniswap.helper as the old names are confusing.
        * _x96_to_decimal -> _from_x96
        * decimal_to_x96 -> _to_x96
        * _x96_sqrt_to_decimal -> sqrt_price_x96_to_base_unit_price
        * sqrt_price_to_tick -> sqrt_price_x96_to_tick
        * pool_price_to_tick -> _sqrt_price_to_tick
        * tick_to_sqrtPriceX96 -> tick_to_sqrt_price_x96
        * tick_to_quote_price -> tick_to_base_unit_price
        * quote_price_to_tick -> base_unit_price_to_tick
        * quote_price_to_sqrt -> base_unit_price_to_sqrt_price_x96
        * from_wei -> from_atomic_unit
* Add console output for squeeth and deribit market

# Ver 0.5.0

* Add Squeeth market
* Change unit of sell fee in uniswap from quote token to base token
* add a parameter on collect fee of uniswap market, to decide transfer token to user or not
* fix issue: data head or tail may be blank in uniswap market

# Ver 0.4.0

* Add Deribit option market

# Ver 0.3.1

* Fix: When uniswap market load data, if the start time of the first day is not 00:00:00, row count of the first day
  will not be 1440.
* Fix: to json of aave market actions.
* Fix: action timestamp is nan when make transaction in strategy.initialize()
* Fix: json dump doesn't support decimal

# Ver 0.3.0

* Add aave market, support supply/withdraw/borrow/repay, and passive liquidate.
* Add PriceTrigger in strategy
* str() of markets will return json string.
* Trigger class doesn't support *args now, **kwargs is supported and tested
* [breaking change]type of row_data parameter in on_bar/after_bar/trigger has changed, price is included now
* [breaking change]before_bar in strategy has removed, as it's duplicate with trigger and on bar
* [breaking change]if declare a TokenInfo, name property will be instead with upper case. Because name is used for find
  token parameters.
* [breaking change]BrokerAsset in uniswap market is removed, asset balance is managed by broker
* [breaking change]PositionInfo class is moved to uniswap module
* [breaking change]Location of some class was reorganized
* [breaking change]elements in EvaluatorEnum was changed to lower case
* [breaking change]UniswapMarket.position() has changed to UniswapMarket.get_position(), clarify its function by
  renaming it.

# Ver older

* Support uniswap v3 market