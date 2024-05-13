# Ver 0.5.0

* Add Squeeth market
* Change unit of sell fee in uniswap from quote token to base token
* add a parameter on collect fee of uniswap market, to decide transfer token to user or not
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