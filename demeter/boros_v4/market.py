import pandas as pd
from ..broker import Market, MarketInfo


class BorosMarket(Market):

    def __init__(
            self,
            market_info: MarketInfo,
            data: pd.DataFrame | None = None,
            data_path: str = "./data",
    ):
        super().__init__(market_info=market_info, data=data, data_path=data_path)
        pass

    def __str__(self):
        pass

    def open_position(self):
        pass

    def close_position(self):
        pass

    def add_liquidity(self):
        pass

    def remove_liquidity(self):
        pass