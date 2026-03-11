# Uniswap market

Actually, uniswap here stands for uniswap v3 for short. Uniswap V3 is a major update, and tick range is introduced. It
improves capital utilization, but also brings complexity. Demeter is designed to evaluate uniswap positions.

Uniswap market is the first market supported by demeter, and it's the most important market. The core lib of this market
is widely used in our analysis reports.

In uniswap market, you can simulate transactions like add liquidity, swap etc. Demeter can accurately calculate fee
income.

One uniswap market instance corresponds to an uniswap pool. So you have to set UniV3Pool parameter to uniswap market
instance. In this class, you need to specify the tokens and fee rate. Base token means which token is used to indicate
the price. E.g., if token0 is usdc, token1 is weth, then token0 should be set as base token, so you can get the price
unit in usdc/eth.

Uniswap market supports the following functions:

* add_liquidity: Create a new liquidity position, or add funds to existing position.
* add_liquidity_by_tick: the same to add_liquidity, but the parameter is more underlying.
* remove_liquidity: remove liquidity from pool. This function provides many parameters. You can remove part of the
  liquidity, or decide to execute collect or not. Note: After burn, assets will be sent to pending_fee in position, you
  have to invoke collect to transfer assets and fee earned to your account.
* collect_fee: Transfer assets from "pending fee" in position.
* buy/sell: swap tokens with this pool.

