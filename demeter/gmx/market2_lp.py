from datetime import date
from decimal import Decimal

import pandas as pd
from orjson import orjson

from ._typing2 import (
    GmxV2LpDescription,
    GmxV2LpMarketStatus,
    GmxV2LpBalance,
    GmxV2PoolStatus,
    Gmx2WithdrawAction,
    Gmx2DepositAction,
)
from .gmx_v2 import PoolConfig, LPResult, GmxV2Pool, PoolData
from .gmx_v2.deposit import ExecuteDepositUtils
from .gmx_v2.withdrawal import ExecuteWithdrawUtils
from .gmx_v2.market import MarketUtils
from .helper2 import load_gmx_v2_data, get_price_from_v2_data
from .. import TokenInfo, DECIMAL_0, ChainType, DemeterError, UnitDecimal
from .._typing import USD
from ..broker import Market, MarketInfo
from ..utils import get_formatted_predefined, get_formatted_from_dict, STYLE, require


class GmxV2LpMarket(Market):
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

    @property
    def description(self) -> GmxV2LpDescription:
        return GmxV2LpDescription(
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
    def market_status(self) -> GmxV2LpMarketStatus:
        return self._market_status

    # endregion

    def check_market(self):
        super().check_market()
        require(self.quote_token == USD, "Quote token of GMX v2 market must be USD")

        if self.long_token not in self.broker.assets:
            self.broker.set_balance(self.long_token, DECIMAL_0)
        if self.short_token not in self.broker.assets:
            self.broker.set_balance(self.short_token, DECIMAL_0)

    def update(self):
        pass

    def set_market_status(self, data: GmxV2LpMarketStatus | pd.Series, price: pd.Series):
        super().set_market_status(data, price)
        data.data = self.data.loc[data.timestamp]
        self._market_status = data

    def get_market_balance(self) -> GmxV2LpBalance:
        pool_data: GmxV2PoolStatus = self._market_status.data
        if self.amount > 0:
            longAmount, shortAmount = MarketUtils.getTokenAmountsFromGM(pool_data, self.amount)
            share = Decimal(self.amount / pool_data.marketTokensSupply)
            long_amount = Decimal(longAmount)
            short_amount = Decimal(shortAmount)
            net_value = Decimal(pool_data.poolValue) * share
        else:
            net_value = long_amount = short_amount = Decimal(0)

        return GmxV2LpBalance(
            net_value=net_value,
            gm_amount=Decimal(self.amount),
            long_amount=long_amount,
            short_amount=short_amount,
        )

    def formatted_str(self):
        value = get_formatted_predefined(f"{self.market_info.name}({type(self).__name__})", STYLE["header3"]) + "\n"
        value += (
            get_formatted_from_dict(
                {
                    "long token": self.pool.long_token.name,
                    "short token": self.pool.short_token.name,
                    "amount": self.amount,
                }
            )
            + "\n"
        )
        return value

    def load_data(self, chain: ChainType, pool_address: str, start_date: date, end_date: date):
        self._data = load_gmx_v2_data(chain, pool_address, start_date, end_date, self.data_path)

    def get_price_from_data(self):
        if self.data is None:
            raise RuntimeError("data is None")
        return get_price_from_v2_data(self.data, self.pool)

    def _resample(self, freq: str):
        self._data = self.data.resample(freq).first()

    def deposit(self, long_amount: Decimal | float, short_amount: Decimal | float) -> LPResult:
        assert long_amount >= 0 and short_amount >= 0
        long_amount = float(long_amount)
        short_amount = float(short_amount)
        pool_data = PoolData(self.pool, self._market_status.data, self.pool_config)

        result = ExecuteDepositUtils.get_mint_amount(
           long_amount, short_amount,pool_data
        )
        self.amount += result.gm_amount
        self.broker.subtract_from_balance(self.long_token, Decimal(result.long_amount))
        self.broker.subtract_from_balance(self.short_token, Decimal(result.short_amount))
        self._record_action(
            Gmx2DepositAction(
                market=self.market_info,
                gm_amount=UnitDecimal(result.gm_amount, "GM"),
                gm_usd=UnitDecimal(result.gm_usd, "USD"),
                long_amount=UnitDecimal(result.long_amount, self.long_token.name),
                short_amount=UnitDecimal(result.short_amount, self.short_token.name),
                deposit_usd=UnitDecimal(result.total_usd, "USD"),
                long_fee=UnitDecimal(result.long_fee, self.long_token.name),
                short_fee=UnitDecimal(result.short_fee, self.short_token.name),
                fee_usd=UnitDecimal(result.fee_usd, "USD"),
                price_impact_usd=UnitDecimal(result.price_impact_usd, "USD"),
            )
        )
        return result

    def withdraw(self, amount: float | None = None) -> LPResult:
        if amount is None:
            amount = self.amount
        assert amount >= 0
        amount = float(amount)
        pool_data = PoolData(self.pool, self._market_status.data, self.pool_config)

        result: LPResult = ExecuteWithdrawUtils.getOutputAmount(amount, pool_data)
        self.amount -= result.gm_amount
        self.broker.add_to_balance(self.long_token, Decimal(result.long_amount))
        self.broker.add_to_balance(self.short_token, Decimal(result.short_amount))
        if amount < 0:
            raise DemeterError("amount cannot be negative, value is {}".format(amount))

        self._record_action(
            Gmx2WithdrawAction(
                market=self.market_info,
                gm_amount=UnitDecimal(result.gm_amount, "GM"),
                gm_usd=UnitDecimal(result.gm_usd, "USD"),
                long_amount=UnitDecimal(result.long_amount, self.long_token.name),
                short_amount=UnitDecimal(result.short_amount, self.short_token.name),
                withdraw_usd=UnitDecimal(result.total_usd, "USD"),
                long_fee=UnitDecimal(result.long_fee, self.long_token.name),
                short_fee=UnitDecimal(result.short_fee, self.short_token.name),
                fee_usd=UnitDecimal(result.fee_usd, "USD"),
            )
        )
        return result
