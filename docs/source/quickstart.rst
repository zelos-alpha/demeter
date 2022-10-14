Getting Started
====================================

System Requirements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Python >= 3.10
* Minimum 500MB disk space to keep pool status data.
* Minimum 8G Memory
* Operation system: Mac or Linux (Windows is not fully tested)

We recommend use virtual environment application like `conda <https://docs.conda.io/projects/conda/en/latest/>`_


Install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setup a new python project, and install

.. code-block:: bash

  pip install zelos-demeter

Download pool status
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Demeter can simulate actions on liquidity pool, such as add/remove liquidity, swap. and calculate the earnings or losses.
In order to realize the simulation, pool status need to be prepared. You can get data by following :doc:`download_tutorial`.

Core concept
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As we follow the style of backtrader. Demeter inherits some core concepts from backtrader.

.. _Lines:

Lines
----------------------------------------

Data Feeds, Indicators and Strategies are considered as :doc:`Line <references/data_line>`, which is inherit from pandas.Series,
and their collection is :doc:`Lines <references/data_line>`, which is inherit from pandas.DataFrame.



A line is a succession of points that when joined together form this line. Data collected by downloader will have the following set of points per minute:

* timestamp: time
* netAmount0: sum swap amount of token 0
* netAmount1: sum swap amount of token 1
* closeTick: last swap tick in this minute
* openTick: first swap tick in this minute
* lowestTick: lowest swap tick in this minute
* highestTick: highest swap tick in this minute
* inAmount0, sum for positive amount of token 0
* inAmount1: sum for positive amount of token 1
* currentLiquidity: last Liquidity in swap

When the test starts, the following set will be added,

* row_id: data index of this line, start with 0, can be used in dataframe.iloc()
* open: first price of this bar
* price: latest price of this bar
* low: lowest price
* high: highest price
* volume0: volume of token 0
* volume1: volume of token 1

The series of “price”s along time is a Line. And therefore a Data Feed has usually 17 lines.

Since Line and Lines are inherit from pandas. data can be accessed in pandas way.

Index 0 Approach
----------------------------------------

When accessing the values in a line, the current value is accessed with index: 0,

for example, if you want to access current value of price, you can call *get_by_cursor*, And the “last” output value is accessed with -1. Of course earlier output values can be accessed with -2, -3, …

.. code-block:: python

  self.data.get_by_cursor(0).closeTick # access current row
  self.data.get_by_cursor(-1).closeTick # access previous row

This will help access current row and rows around.


Basic sample
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's start with a simple example.

.. code-block:: python

    eth = TokenInfo(name="eth", decimal=18) # 1
    usdc = TokenInfo(name="usdc", decimal=6)
    pool = PoolBaseInfo(usdc, eth, 0.05, usdc) # 2
    runner = Runner(pool) # 3
    runner.set_assets([Asset(usdc, 1000), Asset(eth, 1)]) #4
    runner.data_path = "../data" # 5
    runner.load_data(ChainType.Polygon.name, # 6
                     "0x45dda9cb7c25131df268515131f647d726f50608",
                     date(2022, 8, 15),
                     date(2022, 8, 20))
    runner.run() #7
    runner.output() #8

1 First you should register tokens, We take pool 0x45dda9cb7c25131df268515131f647d726f50608 on polygon(usdc-weth) as example.
so we assign two variables *eth*, *usdc*.

2 Then setup tool, the parameter should be consistent with pool contract. note, the last parameter is base token.
That means which token will be considered as base token.
eg: to a token pair of USDT/BTC, if you want price unit to be like 10000 usdt/btc, you should set usdt as base token,
otherwise if price unit is 0.00001 btc/usdt, you should set btc as base token

3 Now create a runner, and set pool info as parameter

4 set up initial asset to runner. Now you have 1000usdc and 1eth to simulate.

5 set up data folder path, the path should have the chain status files formerly download

6 load data by data.

7 run test

8 print final status, including balance, positions

After run the test, The output is

.. code-block::

    2022-10-13 18:11:57,985 - INFO - init strategy...
    2022-10-13 18:11:57,990 - INFO - start main loop...
    100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 5/5 [00:00<00:00, 363.45it/s]
    2022-10-13 18:11:58,030 - INFO - main loop finished, start calculate evaluating indicator...
    2022-10-13 18:11:58,035 - INFO - run evaluating indicator
    2022-10-13 18:11:58,038 - INFO - back testing finish
    Final status
    total capital: 2000.0020usdc                  balance   : 1000usdc,1eth                  uncollect fee: 0usdc,0eth                     in position amount: 0usdc,0eth
    Evaluating indicator
    annualized_returns: 0                              benchmark_returns: 0


Add a strategy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Not write a strategy

.. code-block:: python

      class MyFirstStrategy(Strategy):
        def next(self, row_data: Union[RowData, pd.Series]):
            if row_data.price > 1500:
                self.buy(0.1, row_data.price)


      runner.strategy = MyFirstStrategy()

Write a strategy is simple. you just have to inherit from :doc:`strategy <references/strategy>` class, and set it to runner.
When back testing is running, if price is above 0.1 eth/usdc (Remember we have set usdc as base token, so price and buy/sell action is all based on eth),
broker will buy 0.1eth

In strategy, you can make trade action including add_liquidity, remove_liquidity, collect_fee, buy, sell. you can check :doc:`strategy <references/strategy>` api reference

Strategy also provide initialize and finalize function, which will run before and after the test.

If you chose notify (by setting runner.run(enable_notify=True)), all the trade action will be printed.

how to access data in strategy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

suppose we only have five rows of data, and in closeTick column, data is [0,1,2,3,4], you can access data in various ways.

.. code-block:: python

    class MyFirstStrategy(Strategy):
        def next(self, row_data: Union[RowData, pd.Series]): #
            # access current row
            print(row_data.closeTick)
            print(self.data.get_by_cursor(0).closeTick)
            print(self.data.loc[row_data.timestamp].closeTick)

            # access the row by data index
            print(self.data.closeTick[0])  # first row
            print(self.data["closeTick"].iloc[0])  # first row
            print(self.data.closeTick[row_data.row_id])  # current row

            # access previous or after row
            print(self.data.get_by_cursor(-2).closeTick)  # previous 2 rows
            print(self.data.get_by_cursor(2).closeTick)  # after 2 rows
            print(self.data.loc[row_data.timestamp - timedelta(hours=1)].closeTick)  # data of an hour ago
            print(self.data.loc[row_data.timestamp + timedelta(days=1)].closeTick)  # data of an day later

            print(self.broker.asset0.balance, self.broker.asset1.balance)  # show balance in asset 0,1
            print(self.broker.base_asset.balance, self.broker.quote_asset.balance)  # show balance in base quote
            print(self.broker.get_account_status())  # get current capital status,
            for position_info, position in self.broker.positions.items():
                print(position_info, position)  # show all position

row_data is row of in current loop. its type is pandas.Series, and its properity is listed in :ref:`Lines`


Add a indicator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Demeter has preset some indicator, to help analysis the data.

.. code-block:: python

   from demeter import simple_moving_average, TimeUnitEnum

   # before runner.run()
   runner.data["ma5"] = simple_moving_average(runner.data.price, 5, unit=TimeUnitEnum.hour)

this example shows how to add simple moving average indicator with 5 hour window. they can be access in strategy

.. code-block:: python

    class MyFirstStrategy(Strategy):
        def next(self, row_data: Union[RowData, pd.Series]):
            if row_data.ma5 > 1500: # access by row_data
                self.buy(100, row_data.price)
            if self.data.get_by_cursor(0).ma5 > 1500 # access by index
                self.buy(100, row_data.price)

