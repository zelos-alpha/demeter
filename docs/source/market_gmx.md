# GMX market

GMX market can simulate common transaction in GMX v1 for glp operation:
* Buy GLP: deposit token into GLP pool and get glp and stake glp to get weth/wavax profit
* Sell GLP: sell out token and harvest glp profit from GLP pool.

GMX deployed on arbitrum and avalanche, the GLP pool contains several stable coins and shortable coins, and GLP price is calculated by coins in pool with coin's weight data.

So, you must provide data as follow:

* log data for coin's amounts(poolAmounts, UsdgAmounts, ReverseAmounts, GuaranteedAmounts)
* log data for coin's price, this data can collected from Vault contract's two price feed contract(FastPriceFeed and Chinlink PriceFeed.).
* log data for shortable coin's short size and short average price data from contract ShortTracker.
* transaction input data for coin's weight configuration, this can find from Vault Org Contract(Timelock->setTokenConfig)
* token award per block data from RewardDistributor contract.

Data of gmx market is dataframe, and sample weth data as follow(other coin data will also added.):

|                     | glp                        | weth_price                         | weth_size                         | weth_average                       | weth_guaranteed                     | weth_pool             | weth_reserved        | weth_usdg                 | weth_weight  | interval        | usdg                       | aum                                    | glp_price          |
|---------------------|----------------------------|------------------------------------|-----------------------------------|------------------------------------|-------------------------------------|-----------------------|----------------------|---------------------------|--------------|-----------------|----------------------------|----------------------------------------|--------------------|
| 2024-10-15 00:00:00 | 23218773871711187101247422 | 2629059000000000000000000000000000 | 420680884643992897053976776078343 | 3074682128793599999999999999999891 | 72526903600961706490633878585653070 | 926032532426752780967 | 42146721781505811846 | 2251390889544051105881610 | 20000        | 789480314626619 | 21590378240515822066988385 | 21919427709260225232262199250000000000 | 0.9440389845893614 |
| 2024-10-15 00:01:00 | 23218773871711187101247422 | 2629059000000000000000000000000000 | 420680884643992897053976776078343 | 3074682128793599999999999999999891 | 72526903600961706490633878585653070 | 926032532426752780967 | 42146721781505811846 | 2251390889544051105881610 | 20000        | 789480314626619 | 21590378240515822066988385 | 21919427709260225232262199250000000000 | 0.944038984589381  |

