# Squeeth market

Squeeth is a financial product by the Opyn team. 
Squeeth is a type of power perpetual whose return is equal to the square of the price of ETH (squeeth = square-eth). 
This means that the value of a squeeth is S² if the price of ETH is S.
 
Thus, the Delta of squeeth is 2*S and the Gamma is a constant 2. 
The squeeth payoff will look like a quadratic function with a linear Delta and a flat Gamma.

We support long and short trade in this market. As for long, It supports:

* Buy squeeth in uniswap osqth-eth pool
* Sell squeeth

As for short, you can:

* Deposit/withdraw eth in squeeth.
* mint and burn osqth.
* Deposit/withdraw uniswap liquidity token of osqth-eth pool in squeeth
* Be liquidated if eth price goes up, and liquidation is blow 150%

Like other perpetual futures, usually, long positions will have to pay funding to short positions, 
squeeth achieves this via normalization factor. 
You can extract normalization factor from event log of squeeth contract via demeter-fetch, and used them in backtesting.
As squeeth value is related to eth price and osqth price, demeter-fetch will also download them from relative uniswap pools.


