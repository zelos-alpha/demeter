Download tutorial
====================================

Demeter run back testing based on event logs of uniswap v3 pool contract.
Specifically, when you provide liquidity during test process, demeter will calculate fee earned based on actual on chain data.
So before use demeter, status of specific pool have be prepared. A downloader is provided to collect and process those data.

But collect data from chain is not easy, you might have to setup you own node or spend a lot of money.
So we recommend download data from BigQuery of Google cloud since it is stable and cheap, sometimes even costless.
BigQuery have data source of popular chain, including Ethereum and Polygon.

Via the downloader, you can download raw chain data from BigQuery, and process them by some simple commends. After download, data will be kept in CSV format, and resampled to 1 minute.

Before download data, you should prepare account and environment.

1. Sign up a google account. and then access https://console.cloud.google.com to register google cloud platform.
2. Apply an api key, and install library. follow the tutorial on official-document-site_
3. Try query here: https://console.cloud.google.com/bigquery. Chain data is public, no extra authority is needed.

In BigQuery, you can query chain data with correct id and table name. the query interface is compatible sql. You can try with this sql

.. code-block:: sql

 select * from bigquery-public-data.crypto_ethereum.blocks where timestamp="2015-07-30 15:26:28"

.. _official-document-site: https://cloud.google.com/bigquery/docs/reference/libraries

.. note:: If you have network issues on google, set proper proxy before download data.

After account is prepared, you can start download process.

1. Prepare a config file, in toml format. here is an example:

.. code-block:: toml

    chain = "polygon"  # chain name, such as ethereum, polygon, default if Ethereum
    source = "BigQuery" # download from, we only support bigquery now,
    pool_address = "0x45dda9cb7c25131df268515131f647d726f50608" # pool contract address
    start = "2022-9-19" # download start date
    end = "2022-9-20" # download end date, this date will be included, default value is today
    auth_file = "../auth/airy-sight-361003-d14b5ce41c48.json" # BigQuery auth file. if source is BigQuery, this field must be set.
    save_path = "../data" # where to kept downloaded file. default value is "data"

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
