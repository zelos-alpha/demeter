Demeter
===================================

Introduction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Demeter is a backtesting framework for Defi of ethereum-like chain. It allows investors test their strategy and evaluate return rate with real market data. At present, demeter support backtest on uniswap v3 and aave v3

Demeter's style is borrowed from backtrader, allowing developers of traditional financial engineering to get started quickly.

Demeter has good testing accuracy, it can calculate income and net worth close to the real world. Demeter has also made some optimizations for backtesting speed.


Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **backtrader style:** Demeter's design style and operation process are modeled after Backtrader, making it easier for users to get started.
- **broker/market:** Demeter draws on the concepts of brokers and markets from real markets. Broker holds the asset and provide various market to invest. Demeter supports a variety of markets, including uniswap and aave, and more market is coming. Users can test strategies for investing in multiple markets.
- **Data feeding:** Backtesting requires real market data. Thanks to the transparency of blockchain, those data can be fetched from event logs of transaction. We provided demeter-fetch_ to do this work. It can download event logs from rpc or google big query and decode them to market data.
- **Uniswap market:** As a popular automated market maker, uniswap is famous for its complexity. To raise fund utilization rate, uniswap add tick range to position, which makes it difficult to estimate the return on investment. Demeter provides comprehensive calculation and evaluation tools to help users test the returns of various positions.
- **Aave market:** Aave is a popular liquidity protocol which allow user to deposit and borrow assets. Through supply asset to aave, user can earn interest, and borrowing allow user to earn extra profit or to hedging price changes. Demeter support supply/repay/borrow/repay/liquidation transactions on aave.
- **Deribit option market:** A market to trade option or hedge greeks.
- **Squeeth market:** Allow user to trade delta and gamma with ethereum price^2
- **Accuracy:** In the design of demeter, accuracy is an important consideration. In order to provide higher accuracy, the core calculations of uniswap and aave do not follow theoretical formulas, but draw on the code of the contract. This allows demeter to have higher calculations accuracy.
- **Rich output:** In order to allow users to evaluate strategies intuitively, demeter provides a wealth of output, including asset changes in accounts and position adjustment records. With the indicator calculation module, users can choose the best investment strategy.
- **Indicators:** Besides the simulation of defi market, demeter also provides various indicators. Those indicators will help user to decide how and when to make transactions, and evaluate their strategies.
- **Rich interface in strategy:** In strategy, demeter provide a lot of interface, which help user to write strategy freely. With triggers, user can make transactions a specified time or price. With on_bar and after_bar function, user can check and calculate on each iteration. Initialize and finalize function are also provided.
- **Price:** Price is the key to calculate token net value, since it will be used among markets. We separate price from market.data. Prices can be downloaded from coingecko and some centralized market.
- **Decimal places:** You can define decimal places to avoid long decimal.

.. _GammaStrategies: https://github.com/l0c4t0r/active-strategy-framework
.. _demeter-fetch: https://github.com/zelos-alpha/demeter-fetch

Conclusion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Our vision is to become the best Defi backtesting tool, you can check our release_note_ for the latest updates.

.. _release_note: https://github.com/zelos-alpha/demeter/blob/master/release_note.md

links
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Documentation: https://zelos-demeter.readthedocs.io/en/latest/index.html
* Medium: https://medium.com/zelos-research
* Pypi: https://pypi.org/project/zelos-demeter
* Antalpha labs: https://labs.antalpha.com/
* Uniswap: https://uniswap.org
* aave: https://aave.com


.. toctree::
   :maxdepth: 1
   :caption: Contents:

   install
   download_data
   quickstart
   modules
   market_uniswap
   market_aave
   market_deribit_option
   references





