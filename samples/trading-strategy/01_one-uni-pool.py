"""
This example shows how to start a backtesting with datasource from trading strategy.
"""

import datetime

import pandas as pd
from tradeexecutor.strategy.demeter.adapter import load_clmm_data_to_uni_lp_market
from tradingstrategy.client import Client
from tradingstrategy.pair import PandasPairUniverse

from demeter import Actuator, MarketInfo, TokenInfo, ChainType, MarketTypeEnum
from demeter import Strategy
from demeter.uniswap import UniLpMarket, UniV3Pool
from utils import TradingStrategyUtil

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class EmptyStrategy(Strategy):
    pass


if __name__ == "__main__":
    # claim token and pool as usual
    chain = ChainType.ethereum
    usdc = TokenInfo(name="usdc", decimal=6)
    weth = TokenInfo(name="weth", decimal=18)
    pool = UniV3Pool(usdc, weth, 0.05, usdc)
    # specify backtest time range.
    start = datetime.datetime(2024, 1, 1)
    end = datetime.datetime(2024, 1, 31)

    # Declare a market key
    market_key = MarketInfo("UniPool", MarketTypeEnum.uniswap_v3)
    # Declare the market,
    market = UniLpMarket(market_key, pool)

    #============ Load data from trading strategy==============
    # create a client. you will need an api key to query data.
    client = Client.create_jupyter_client()
    # Load pairs in all exchange
    exchange_universe = client.fetch_exchange_universe()
    pairs_df = client.fetch_pair_universe().to_pandas()
    # Filter all pairs and generate pair cache.
    pair_universe = PandasPairUniverse(
        pairs_df[(pairs_df["dex_type"] == "uniswap_v3") & (pairs_df["chain_id"] == chain.value)],
        exchange_universe=exchange_universe,
    )
    # Get pair description of your pool
    pair_descriptions = [TradingStrategyUtil.to_pair_desc(chain, pool)]
    # Load metadata for the chosen trading pairs (pools)
    pair_metadata = [pair_universe.get_pair_by_human_description(desc) for desc in pair_descriptions]
    # Map to internal pair primary keys
    pair_ids = [pm.pair_id for pm in pair_metadata]
    print("Pool addresses are", [(pm.get_ticker(), pm.pair_id, pm.address) for pm in pair_metadata])

    # Load CLMM data for selected pairs
    # End time in demeter includes the last day while the client doesn't, so end data should add 1 when querying
    clmm_df = client.fetch_clmm_liquidity_provision_candles_by_pair_ids(
        pair_ids,
        TradingStrategyUtil.time_bucket,
        start_time=start,
        end_time=end + datetime.timedelta(days=1),
    )

    # Load trading strategy data to market
    load_clmm_data_to_uni_lp_market(market, clmm_df, start, end)
    # ============ Load data finished==============

    # Following is the same.
    # Declare the Actuator, which controls the whole process
    actuator = Actuator()  # declare actuator, Demeter Actuator (broker:assets: ; markets: )
    # add market to broker
    actuator.broker.add_market(market)
    # Initial some fund to broker.
    actuator.broker.set_balance(usdc, 1000)
    actuator.broker.set_balance(weth, 1)
    actuator.strategy = EmptyStrategy()  # set strategy to actuator
    price_data = market.get_price_from_data()
    actuator.set_price(price_data)
    actuator.run()
