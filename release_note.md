# ver xx.xx.xx

* add aave market
* [breaking change]add price parameter for before_bar/on_bar/after_bar in strategy
* add trigger.do in strategy
* before bar in strategy is removed, as it's duplicate with trigger and on bar
* [breaking change]if declare a TokenInfo, name property will be converted to upper case now
* BrokerAsset in uniswap market is removed, asset balance is managed by broker
* PositionInfo class is moved to uniswap module
* some package reference has changed
