import datetime
import sys
from datetime import timedelta
from decimal import Decimal
from typing import List

import pandas as pd
from tradingstrategy.chain import ChainId
from tradingstrategy.client import Client
from tradingstrategy.pair import PandasPairUniverse
from tradingstrategy.timebucket import TimeBucket

from demeter import ChainType
from demeter.uniswap import UniV3Pool


class TradingStrategyUtil:
    time_bucket = TimeBucket.m1
    market = "uniswap-v3"

    @staticmethod
    def to_pair_desc(chain: ChainType, pool: UniV3Pool):
        return (
            ChainId[chain.name],
            TradingStrategyUtil.market,
            pool.base_token.name,
            pool.quote_token.name,
            pool.fee_rate,
        )

    @staticmethod
    def set_pair_id(pools: List, metadatas: List):
        for pool in pools:
            for pair in metadatas:
                if (
                    pair.token0_symbol == pool.token0.name
                    and pair.token1_symbol == pool.token1.name
                    and Decimal(str(pair.fee_tier)) == pool.fee_rate
                ):
                    setattr(pool, "pair_id", pair.pair_id)
                    break


def load_from_trading_strategy(
    chain: ChainType, pools: List[UniV3Pool], start: datetime.datetime, end: datetime.datetime
) -> pd.DataFrame:
    # Load pairs in all exchange
    print("Loading markets")
    client = Client.create_jupyter_client()
    exchange_universe = client.fetch_exchange_universe()
    pairs_df = client.fetch_pair_universe().to_pandas()
    pair_universe = PandasPairUniverse(
        pairs_df[(pairs_df["dex_type"] == "uniswap_v3") & (pairs_df["chain_id"] == chain.value)],
        exchange_universe=exchange_universe,
    )
    pair_descriptions = [TradingStrategyUtil.to_pair_desc(chain, pool) for pool in pools]

    # Load metadata for the chosen trading pairs (pools)
    pair_metadata = [pair_universe.get_pair_by_human_description(desc) for desc in pair_descriptions]
    TradingStrategyUtil.set_pair_id(pools, pair_metadata)
    # Map to internal pair primary keys
    pair_ids = [pm.pair_id for pm in pair_metadata]

    # Load CLMM data for selected pairs
    clmm_df = client.fetch_clmm_liquidity_provision_candles_by_pair_ids(
        pair_ids,
        TradingStrategyUtil.time_bucket,
        start_time=start,
        end_time=end + timedelta(days=1),
    )
    return clmm_df
