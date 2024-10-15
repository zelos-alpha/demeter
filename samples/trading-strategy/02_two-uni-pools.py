"""
Show how to backtest multiple pools with trading strategy data source.

Note that:
1. You can pull multiple pools from trading strategy at one time,
so you need to set the pair_id in the pool to distinguish which data belongs to which pool.
2. In backtest, price should be unified to one token, but each markets has its own quote token
"""

import datetime
from decimal import Decimal

import pandas as pd
from tradeexecutor.strategy.demeter.adapter import load_clmm_data_to_uni_lp_market

from demeter import Actuator, MarketInfo, TokenInfo, ChainType, MarketTypeEnum, AtTimeTrigger, RowData
from demeter import Strategy
from demeter.uniswap import UniLpMarket, UniV3Pool
from utils import load_from_trading_strategy

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class DemoStrategy(Strategy):
    def initialize(self):
        new_trigger = AtTimeTrigger(time=start, do=self.add_liq)
        self.triggers.append(new_trigger)

    def add_liq(self, row_data: RowData):
        lower = Decimal("0.95")
        upper = Decimal("1.05")

        eth_price_to_btc = row_data.market_status[key_wbtc_weth_03].price
        market_wbtc_weth_03.add_liquidity(eth_price_to_btc * lower, eth_price_to_btc * upper)

        eth_price_to_u = row_data.prices[weth.name]
        market_usdc_weth_005.add_liquidity(eth_price_to_u * lower, eth_price_to_u * upper)
        pass


if __name__ == "__main__":
    # Configure tokens and pools
    chain = ChainType.ethereum
    usdc = TokenInfo(name="usdc", decimal=6)
    weth = TokenInfo(name="weth", decimal=18)
    wbtc = TokenInfo(name="wbtc", decimal=8)
    pool_usdc_weth_005 = UniV3Pool(usdc, weth, 0.05, usdc)
    pool_wbtc_weth_03 = UniV3Pool(wbtc, weth, 0.3, wbtc)

    start = datetime.datetime(2024, 1, 1)
    end = datetime.datetime(2024, 1, 15)

    # Load data of two pools from tranding strategy
    pool_data = load_from_trading_strategy(chain, [pool_usdc_weth_005, pool_wbtc_weth_03], start, end)

    # Initial market, and set data
    key_usdc_weth_005 = MarketInfo("usdc_weth_005", MarketTypeEnum.uniswap_v3)
    market_usdc_weth_005 = UniLpMarket(key_usdc_weth_005, pool_usdc_weth_005)
    load_clmm_data_to_uni_lp_market(
        market_usdc_weth_005, pool_data[pool_data["pair_id"] == market_usdc_weth_005.pool_info.pair_id], start, end
    )

    key_wbtc_weth_03 = MarketInfo("wbtc_weth_03", MarketTypeEnum.uniswap_v3)
    market_wbtc_weth_03 = UniLpMarket(key_wbtc_weth_03, pool_wbtc_weth_03)
    load_clmm_data_to_uni_lp_market(
        market_wbtc_weth_03, pool_data[pool_data["pair_id"] == market_wbtc_weth_03.pool_info.pair_id], start, end
    )

    # Declare the Actuator, which controls the whole process
    actuator = Actuator()  # declare actuator, Demeter Actuator (broker:assets: ; markets: )
    # add market to broker
    actuator.broker.add_market(market_usdc_weth_005)
    actuator.broker.add_market(market_wbtc_weth_03)
    # Initial some fund to broker.
    actuator.broker.set_balance(usdc, 20000)
    actuator.broker.set_balance(weth, 25)
    actuator.broker.set_balance(wbtc, 1)

    actuator.strategy = DemoStrategy()  # set strategy to actuator

    # You can also get price from external data feed.
    price_weth_usdc, _ = market_usdc_weth_005.get_price_from_data()
    price_wbtc_weth, _ = market_wbtc_weth_03.get_price_from_data()

    # Add price of wbtc
    price_weth_usdc[wbtc.name] = price_weth_usdc[weth.name] / price_wbtc_weth[weth.name]
    # set price, and set USDC as quote token, so total net value will be quoted by USDC
    actuator.set_price(price_weth_usdc, usdc)

    actuator.print_action = True
    actuator.run()
