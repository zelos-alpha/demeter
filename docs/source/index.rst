Demeter
===================================

Introduction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This respiratory is an uniswap v3 backtest framework for LP provider.It is
inspired by GammaStrategies_ and backtrader.
with following features:

1. backtrader style
2. better abstraction and well-organised
3. high test coverage and sample code
4. replay input data and calc indicators
5. simulation liquidity operations and record related data
6. run custom strategy and output position info / net value data
7. add custom indicators to evaluate strategy performance

Feel free to make an issue or pr to help this respiratory.

.. _GammaStrategies: https://github.com/l0c4t0r/active-strategy-framework

Design rationale
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

event data
------------------------------------------------------
Evm's event is better than graphQL.
Event approach is cheaper and easier to use than subgraph approach.
It is found that official subgraph had some bugs in some corner cases.

We provide a bigquery downloader to produce daily pool csv files. Data downloading is an independent step for backtesting. You can download and clean it on you your ownself.
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

Install and update using pip:

.. code-block:: bash

    pip install -U zelos-demeter

Simple example to use demeter:

.. code-block:: python

    from datetime import date
    from demeter import TokenInfo, Actuator, MarketInfo, ChainType
    from demeter.uniswap import UniV3Pool, UniLpMarket
    eth = TokenInfo(name="eth", decimal=18)
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = UniV3Pool(token0=usdc, token1=eth, fee=0.05, base_token=usdc)
    market_key = MarketInfo("U2EthPool")
    market = UniLpMarket(market_key, pool)
    market.data_path = "../data"  # csv data path
    market.load_data(
            chain=ChainType.polygon.name,  # load data
            contract_addr="0x45dda9cb7c25131df268515131f647d726f50608",
            start_date=date(2023, 8, 15),
            end_date=date(2023, 8, 15),
        )
    actuator = Actuator()
    actuator.broker.add_market(market)
    actuator.broker.set_balance(usdc, 10000)
    actuator.broker.set_balance(eth, 10)
    actuator.run()
    actuator.output()

You can get more sample and documents by try quickstart in our :doc:`quickstart`

license
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
MIT

links
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* Documentation: https://zelos-demeter.readthedocs.io/en/latest/quickstart.html
* Medium: https://medium.com/zelos-research
* Pypi: https://pypi.org/project/zelos-demeter

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   quickstart
   download_tutorial
   refernce





