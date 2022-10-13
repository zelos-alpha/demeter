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

