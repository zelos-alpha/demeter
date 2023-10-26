# Readme

## Introduction 
This repository is an uniswap v3 backtest framework for LP provider.It is
inspired by [gammaStrategy](https://github.com/l0c4t0r/active-strategy-framework) and **backtrader**.
with following features:
1. backtrader style
2. better abstraction and well-organised
3. high test coverage and sample code
4. replay input data and calc indicators
5. simulation liquidity operations and record related data
6. run custom strategy and output position info / net value data.
7. add custom indicators to evaluate strategy performance

Feel free to make an issue or pr to help this repository.


## Design rationale 
### event data

We need log event to simulate pool status instead of graphQL as evm's event is better than graphQL. 
Event approach is cheaper and easier to use than subgraph approach, and the data is more correct than subgraph data.
It found that the official subgraph apis had some bugs in some corner cases, and some api return wrong data which make you can not believe in it.

We provide an independent download tool, [demeter-fetch](https://github.com/zelos-alpha/demeter-fetch) to fetch event data. It can download chain's event log from **rpc** or **google bigquery**. Those logs will be resampled to minute to reduce calculation. 
**demeter-fetch** can abstract the data into human friendly csv format, which it widely used in our research. 



### abstraction
Strategy: quote/base price.

Broker: storage user asset and trade data.

pool: no state. just calculation. deal with tick, token0，decimal, total L.


### plot and strategy performance
User may have different choices about plot and metrics of strategy performance.
So we did not make such decisions for you. We provide some examples in strategy-example.Hope it can help you to write your own strategy.

We plan to improve metrics in recent.


## How to use

Install and update using [pip](https://pip.pypa.io/en/stable/getting-started/):  
```pip install -U zelos-demeter```

```python
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
```

You can get more sample and documents by try **quickstart** in our [docs](https://zelos-demeter.readthedocs.io/en/latest/quickstart.html)


## License
MIT

## Links

* Documentation: https://zelos-demeter.readthedocs.io/en/latest/quickstart.html
* Medium: https://medium.com/zelos-research
* Pypi: https://pypi.org/project/zelos-demeter
