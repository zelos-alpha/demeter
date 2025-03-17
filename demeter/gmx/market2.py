from datetime import date
from decimal import Decimal

import pandas as pd
from orjson import orjson

from .helper2 import load_gmx_v2_data, get_price_from_v2_data
from .gmx_v2 import PoolConfig, LPResult
from .gmx_v2.ExecuteDepositUtils import ExecuteDepositUtils
from .gmx_v2.ExecuteWithdrawUtils import ExecuteWithdrawUtils
from .. import MarketStatus, TokenInfo, DECIMAL_0, ChainType
from ..broker import Market, MarketInfo, MarketBalance
from ._typing2 import GmxV2Pool, GmxV2Description, GmxV2MarketStatus


class GmxV2Market(Market):
    def __init__(
        self, market_info: MarketInfo, pool: GmxV2Pool, data: pd.DataFrame | None = None, data_path: str = "./data"
    ):
        super().__init__(market_info=market_info, data=data, data_path=data_path)
        self.pool = pool
        self.amount: float = 0.0
        self.pool_config = PoolConfig(pool.long_token.decimal, pool.short_token.decimal)

    # region prop

    def __str__(self):
        from demeter.utils import orjson_default

        # return repr(self.description().__dict__)
        return orjson.dumps(self.description, default=orjson_default).decode()

    def description(self) -> GmxV2Description:
        return GmxV2Description(
            type=type(self).__name__,
            name=self._market_info.name,
            amount=self.amount,
        )

    @property
    def long_token(self) -> TokenInfo:
        return self.pool.long_token

    @property
    def short_token(self) -> TokenInfo:
        return self.pool.short_token

    @property
    def market_status(self) -> GmxV2MarketStatus:
        return self._market_status

    # endregion

    def check_market(self):
        super().check_market()

        if self.long_token not in self.broker.assets:
            self.broker.set_balance(self.long_token, DECIMAL_0)
        if self.short_token not in self.broker.assets:
            self.broker.set_balance(self.short_token, DECIMAL_0)

    def update(self):
        # calculate total value
        pass

    def set_market_status(self, data: MarketStatus, price: pd.Series):
        super().set_market_status(data, price)

    def get_market_balance(self) -> MarketBalance:
        pass

    def formatted_str(self):
        pass

    def load_data(self, chain: str, pool_address: str, start_date: date, end_date: date):
        self._data = load_gmx_v2_data(chain, pool_address, start_date, end_date, self.data_path)

    def get_price_from_data(self):
        if self.data is None:
            raise RuntimeError("data is None")
        return get_price_from_v2_data(self.data, self.pool)

    def _resample(self, freq: str):
        self._data.resample(freq=freq, inplace=True)

    def deposit(self, long_amount: float | None, short_amount: float | None) -> LPResult:
        result = ExecuteDepositUtils.get_mint_amount(
            self.pool_config, self._market_status.data, long_amount, short_amount
        )
        self.amount += result.gm_amount
        self.broker.subtract_from_balance(self.long_token, Decimal(result.long_amount))
        self.broker.subtract_from_balance(self.short_token, Decimal(result.short_amount))
        return result

    def withdraw(self, amount: float | None = None) -> LPResult:
        result = ExecuteWithdrawUtils.getOutputAmount(self.pool_config, self._market_status.data, amount)
        self.amount -= result.gm_amount
        self.broker.add_to_balance(self.long_token, Decimal(result.long_amount))
        self.broker.add_to_balance(self.short_token, Decimal(result.short_amount))
        return result
