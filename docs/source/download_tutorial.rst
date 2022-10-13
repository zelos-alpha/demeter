Download tutorial
====================================

Before use demeter, data should be prepared. Demeter do back test according to unswap v3 contract log events.
but raw data are too large. so we provide a tool to download and preprocess data.

Data used in demeter is sourced from chain. But get data from chain is not easy,
you might have to setup your own node to satisfy high rate query. So we recommend download data from BigQuery in Google cloud.

BigQuery have data source of popular chain. including block, transactions, and logs. and download cost is reasonable.
We provide a console tool to download data from bigQuery. Before download data, you should prepare account and environment.

1. To use bigQuery, You should sign up a google account. and access https://console.cloud.google.com to register google cloud platform.
2. Apply an api key, and install library. follow the tutorial here. https://cloud.google.com/bigquery/docs/reference/libraries
3. Chain data is public, no extra authority is needed. in BigQuery, you can query chain data with correct id and table name. the query interface is compatible sql, you can try here: https://console.cloud.google.com/bigquery

.. note:: If you have network issues on google, set proper proxy before download data.

Now you can download data.

1. run "python -m demeter.downloader", you will enter a prompt (demeter)
2. input command "config", then follow the wizard, input environment variable. including chain, datasource
3. then choose path you keep google authority file (.json),
4. choose the path to keep downloaded files. press enter to keep default setting (./data), then config finish.
5. run "download pool_contract_address start_date end_date" to start download. this may take a while. you can monitor the progress by process bar.
6. start next download, or input "exit"

After download, data will be resampled to 1 minute. and empty minute will be filled. after process, columns will be

* timestamp,
* netAmount0,
* netAmount1,
* closeTick,
* openTick,
* lowestTick,
* highestTick,
* inAmount0,
* inAmount1,
* currentLiquidity
