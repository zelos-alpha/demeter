# Trading strategy datasource.

[Trading Strategy](https://tradingstrategy.ai) is a company that specializes in providing automated trading strategies
and solutions.
Their goal is to offer a flexible and powerful trading platform that enables traders and developers to create and
execute their own trading strategies.

Currently, Zelos Alpha is working with Trading Strategy,
enabling Demeter to utilize Trading Strategy's data sources and download Uniswap's backtesting data.

Trading Strategy's data sources are not only free, but also offer rapid download speeds and extremely comprehensive
data. With Trading Strategy, you can load and backtest in one script instead of downloading data first. 

Here is a comparison of several data sources

|           | Trading strategy | Google BigQuery            | RPC       | Chifra               |
|-----------|------------------|----------------------------|-----------|----------------------|
| Speed     | very fast        | fast                       | slow      | medium               |
| Cost      | free             | expensive for large amount | low       | free but need a node |
| Storage   | low              | medium                     | medium    | high                 |
| Real-time | good             | low                        | very good | very good            |

To use trading strategy datasource, you should: 

1. Apply an api key: [https://tradingstrategy.ai/docs/programming/setting-up-development-environment/index.html#get-an-api-key](https://tradingstrategy.ai/docs/programming/setting-up-development-environment/index.html#get-an-api-key)
2. Install the environment: [https://tradingstrategy.ai/docs/programming/setting-up-development-environment/index.html](https://tradingstrategy.ai/docs/programming/setting-up-development-environment/index.html)
3. Follow the samples to create your strategy. 
