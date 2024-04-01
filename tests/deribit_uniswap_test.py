import unittest
from datetime import datetime, date

import pandas as pd

from demeter import Strategy, AtTimeTrigger, MarketInfo, Actuator, RowData, TokenInfo, ChainType
from demeter.deribit import DeribitOptionMarket
from demeter.uniswap import UniV3Pool, UniLpMarket

market_u = MarketInfo("uni")
market_d = MarketInfo("deribit")
usdc = TokenInfo(name="usdc", decimal=6)  # declare token usdc
eth = TokenInfo(name="eth", decimal=18)  # declare token eth
pd.options.display.max_columns = None
pd.set_option("display.width", 5000)


class EmptyStrategy(Strategy):
    pass


class OptionStrategyTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(OptionStrategyTest, self).__init__(*args, **kwargs)

    def test_empty(self):
        """
        ensure no exception thrown
        """
        market_deribit = DeribitOptionMarket(market_d, DeribitOptionMarket.ETH, data_path="data")
        market_deribit.load_data(date(2024, 2, 15), date(2024, 2, 16))

        pool = UniV3Pool(token0=usdc, token1=eth, fee=0.05, base_token=usdc)
        market_uni = UniLpMarket(market_u, pool)
        market_uni.data_path = "data"  # set data path
        market_uni.load_data(
            chain=ChainType.polygon.name,  # load data
            contract_addr="0x45dda9cb7c25131df268515131f647d726f50608",
            start_date=date(2024, 2, 15),
            end_date=date(2024, 2, 16),
        )

        actuator = Actuator()
        actuator.broker.add_market(market_deribit)
        actuator.broker.add_market(market_uni)

        actuator.broker.set_balance(eth, 10)
        actuator.broker.set_balance(usdc, 20000)
        actuator.strategy = EmptyStrategy()
        actuator.set_price(market_uni.get_price_from_data())
        actuator.run()
