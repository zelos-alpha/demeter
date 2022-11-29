Download tutorial
====================================

Demeter run back testing based on event logs of uniswap v3 pool contract.
Specifically, when you provide liquidity during test process, demeter will calculate fee earned based on actual on chain data.
So before use demeter, status of specific pool have be prepared. A downloader is provided to collect and process those data.

Downloader provide two ways to collect data:
1. Google BigQuery
2. via rpc of ethereum nodes.

Google BigQuery has stored all the chain data, and you can query them by SQL language. It's very easy and efficient. But it only support two chains, ethereum and polygon.
Eth node is more common, every eth like chain support the same json rpc interface. But query speed is limited by the interface itself. To get timestamp of the block, demeter will have to query relative blocks one by one.
Usually, query a pool logs of a day form bigquery will cost 10 seconds. while query from node will cause several minutes.

To use bigquery, you should prepare account and environment.

1. Sign up a google account. and then access https://console.cloud.google.com to register google cloud platform.
2. Apply an api key, and install library. follow the tutorial on official-document-site_
3. Try query here: https://console.cloud.google.com/bigquery. Chain data is public, no extra authority is needed.

In BigQuery, you can query chain data with correct id and table name. the query interface is compatible sql. You can try with this sql

.. code-block:: sql

 select * from bigquery-public-data.crypto_ethereum.blocks where timestamp="2015-07-30 15:26:28"

.. _official-document-site: https://cloud.google.com/bigquery/docs/reference/libraries

.. note:: If you have network issues on google, set proper proxy before download data.

To use node, you can get sign up a data provider account like infura, quicknode, alchemy. or setup your node to short the request delay. If you have trouble on connection, demeter also provide proxy configuration.

After download, data will be kept in CSV format, and resampled to 1 minute. raw data which before resample will also be kept. Their file name is started with "raw-", you can deleted them if they take too much disk.

1. To start download, first prepare a config file, in toml format. here is an example of download from bigquery

.. code-block:: toml

    chain = "polygon"  # chain name, such as ethereum, polygon
    source = "bigquery"
    pool_address = "0x9B08288C3Be4F62bbf8d1C20Ac9C5e6f9467d8B7" # pool contract address
    save_path = "./data" # where to kept downloaded file. default value is "data"

    [big_query]
    start = "2022-9-19"  # download start date
    end = "2022-9-20"  # download end date, this date will be included, default value is today
    auth_file = "../auth/airy-sight-361003-d14b5ce41c48.json"  # BigQuery auth file.

if you download from rpc, follow this example

.. code-block:: toml

    chain = "polygon"
    source = "rpc"
    pool_address = "0x9B08288C3Be4F62bbf8d1C20Ac9C5e6f9467d8B7"
    save_path = "./data"


    [rpc]
    end_point="https://localhost:8545"
    auth_string = "Basic Y3J0Yzo3NKY3TjY" # optional, used to add auth for some private node
    proxy = "http://localhost:8080" # optional
    start_height = 30194000 # start height
    end_height = 30232000 # end height
    batch_size = 500 # query 500 blocks each time, if the pool is busy,  decrease this number.

note, a significant diff from big query is, query from rpc needs to set height instead of date.
if you want backtest date from Jan 1st to Jan 3rd, you need to find a height before Jan 1st, and end height should later than Jan 3rd
so 5 files will be generated. which is Dec 31, Jan 1,2,3,4. Then first day and the last day will be omitted as they are not complete for a day, only left Jan 1,2,3.


2. start download by

.. code-block:: sh

  python -m zelos-demeter.downloader config.toml

.. note:: pool_contract_address: for example, to usdc and eth pool in polygon, the address is `0x45dDa9cb7c25131DF268515131f647d726f50608 <https://polygonscan.com/address/0x45dda9cb7c25131df268515131f647d726f50608>`_


Data will be kept in the folder you choose, one day for per file. with csv format. Data will be resampled, so each row is 1 minute. if current minute has no data. they will be auto filled according to previous minute.

columns including:

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

To speed up download process. demeter cached timestamp of block in a dict. and kept it in a pkl file, such as "Polygon_height_timestamp.pkl". if you download data again. this file will be loaded and lessen get_block query.
