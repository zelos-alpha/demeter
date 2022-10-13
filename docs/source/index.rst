Demeter
===================================

Introduction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This respiratory is an uniswap v3 backtest framework for LP provider.It is
inspired by GammaStrategies_ and backtrader.
with following features:
1. backtrader style
2. better abstraction and well-organised
3. tested

Feel free to make an issue or pr to help this respiratory.

.. _GammaStrategies: https://github.com/GammaStrategies/active-strategy-framework

Design rationale
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

data
------------------------------------------------------
Evm's event is better than graphQL.
Event approach is cheaper and easier to use than subgraph approach.
It is found that official subgraph had some bugs in some corner cases.

We provide a bigquery downloader to produce daily pool csv files. Data downloading is an independent step for backtesting .You can download and clean it on you your ownself.
More info about download can be found in :doc:`download_tutorial`.


abstraction
------------------------------------------------------

Strategy: quote/base price.

Broker: storage user asset and trade data.

pool: no state. just calculation. deal with tick, token0，decimal, total L.


plot and strategy performance
------------------------------------------------------
User may have different choices about plot and metrics of strategy performance.
So we did not make such decisions for you. We provide some examples in strategy-example.Hope it can help you to write your own strategy.

We plan to improve metrics in recent.


how to use
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
try quickstart in our :doc:`quickstart`

license
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
MIT

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   quickstart
   download_tutorial
   refernce





