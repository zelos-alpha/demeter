from datetime import date

import pandas as pd

from .. import MarketInfo, TokenInfo
from ..broker import Market
from ._typing import ETH_MAINNET
from ..uniswap import UniLpMarket


class SqueethMarket(Market):

    def __init__(
        self,
        market_info: MarketInfo,
        squeeth_uni_pool: UniLpMarket,
        data: pd.DataFrame = None,
        data_path: str = "./data",
    ):
        super().__init__(market_info=market_info, data_path=data_path, data=data)
        self.network = ETH_MAINNET
        self._squeeth_uni_pool = squeeth_uni_pool

    @property
    def squeeth_uni_pool(self) -> UniLpMarket:
        return self._squeeth_uni_pool

    def load_data(self, start_date: date, end_date: date):
        """
        | 1. check files exist(controller, osqth-weth pool, weth-usdc pool)
        | 2. merge to dataframe,use timestamp as index, and keep following columns:
        | 2.1 controller: new norm-factor, new timestamp
        | 2.2 osqth-weth pool: osqth price
        | 2.3 weth-usdc pool: weth price
        """
        pass

    def buy_squeeth(self, eth_amount=None, osqth_amount=None):
        pass

    def sell_squeeth(self, eth_amount=None, osqth_amount=None):
        pass

    def deposit(self):
        pass

    def mint(self):
        pass

    def withdraw(self):
        pass

    def burn(self):
        pass

    # -------------------------------------------------------

    def long_open(self):
        # buy
        pass

    def long_close(self):
        # sell
        pass

    def short_open(self):
        # deposit
        # mint
        # sell
        pass

    def short_close(self):
        # buy
        # withdraw
        pass
