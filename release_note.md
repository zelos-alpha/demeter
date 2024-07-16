# Ver 0.5.4

* [breaking change]Update minimal python version to 3.11
* [breaking change]Update get_account_status_df function to account_status_df property. account_status_df is available after backtest finished.
* account_status_df has token price now
* Add comment for last action, you can record parameter or reason for this transaction, call actuator.comment_last_action in strategy

# Ver 0.5.3

* add print action switch
* add get_output_str for action types
* add pending time to PeriodTrigger, so you can trigger at specific time of a day
* fix bug: when daily minute file is empty, an error will be thrown
* Multiple improves in uniswap market.
  * add price range to position
  * fix bug: base token amount was actually value in add_liquidity_by_value
  

# Ver 0.5.2

Add function for uniswap market: add_liquidity_by_value, With function, you can define how much to add liquidity from your balance.
This function will calculate token amount needed, and do swap to ensure there are enough token. Swap fee is also taken into account.
If you want to add all your balance into liquidity, this function is very useful to help you maximize your liquidity.  


# Ver 0.5.1

* Fix issue: Precision setting not working in console output
* Fix issues in uniswap market:
  * in even_rebalance function, balance calculation did not count swap fee
  * [breaking change]Base and quote is reversed in older version. To accommodate this change, you need to:
    1. When creating a uniswap market instance, is_token0_base has changed to is_token0_quote, You don't have to change anything unless you init with keywords, e.g. You have to change is_token0_base here: UniLpMarket(is_token0_base=True)
    2. In add_liquidity and add_liquidity_by_tick function, order of quote_max_amount and base_max_amount is changed.
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