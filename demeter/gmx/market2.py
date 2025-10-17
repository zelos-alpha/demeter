from datetime import date
from decimal import Decimal

import pandas as pd
from orjson import orjson

from .gmx_v2.MarketUtils import MarketUtils
from .helper2 import load_gmx_v2_data, get_price_from_v2_data
from .gmx_v2 import PoolConfig, LPResult, PositionResult
from .gmx_v2.ExecuteDepositUtils import ExecuteDepositUtils
from .gmx_v2.ExecuteWithdrawUtils import ExecuteWithdrawUtils
from .gmx_v2.ExecuteOrderUtils import ExecuteOrderUtils
from .gmx_v2.ReaderPositionUtils import ReaderPositionUtils
from .. import MarketStatus, TokenInfo, DECIMAL_0, ChainType, DemeterWarning, DemeterError, UnitDecimal
from ..broker import Market, MarketInfo, MarketBalance
from ._typing2 import (
    GmxV2Pool,
    GmxV2Description,
    GmxV2MarketStatus,
    GmxV2Balance,
    GmxV2PoolStatus,
    Gmx2WithdrawAction,
    Gmx2DepositAction,
    Gmx2IncreasePositionAction,
    Gmx2DecreasePositionAction,
    position_dict_to_dataframe
)
from .gmx_v2 import PoolConfig, LPResult, PositionResult
from .gmx_v2.ExecuteDepositUtils import ExecuteDepositUtils
from .gmx_v2.ExecuteWithdrawUtils import ExecuteWithdrawUtils
from .gmx_v2.ExecuteOrderUtils import ExecuteOrderUtils
from .gmx_v2.MarketUtils import MarketUtils
from .helper2 import load_gmx_v2_data, get_price_from_v2_data
from .. import TokenInfo, DECIMAL_0, ChainType, DemeterError, UnitDecimal
from .._typing import USD
from ..broker import Market, MarketInfo
from ..utils import get_formatted_predefined, get_formatted_from_dict, STYLE, require
from .gmx_v2._typing import OrderType, DecreasePositionSwapType


class GmxV2Market(Market):
    def __init__(self, market_info: MarketInfo, pool: GmxV2Pool, data: pd.DataFrame | None = None, data_path: str = "./data"):
        super().__init__(market_info=market_info, data=data, data_path=data_path)
        self.pool = pool
        self.amount: float = 0.0
        self.position_list = {}
        self.cumulative_borrowing = {
            'cumulativeBorrowingFactorLong': {'value': 0, 'time': None},
            'cumulativeBorrowingFactorShort': {'value': 0, 'time': None},
        }
        self.pool_config = PoolConfig(pool.long_token.decimal, pool.short_token.decimal)

    # region prop

    def __str__(self):
        from demeter.utils import orjson_default

        # return repr(self.description().__dict__)
        return orjson.dumps(self.description, default=orjson_default).decode()

    @property
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
        require(self.quote_token == USD, "Quote token of GMX v2 market must be USD")

        if self.long_token not in self.broker.assets:
            self.broker.set_balance(self.long_token, DECIMAL_0)
        if self.short_token not in self.broker.assets:
            self.broker.set_balance(self.short_token, DECIMAL_0)

    def update(self):
        pass

    def set_market_status(self, data: GmxV2MarketStatus | pd.Series, price: pd.Series):
        super().set_market_status(data, price)
        data.data = self.data.loc[data.timestamp]
        self._market_status = data

    def get_market_balance(self) -> GmxV2Balance:
        pool_data: GmxV2PoolStatus = self._market_status.data
        if self.amount > 0:
            longAmount, shortAmount = MarketUtils.getTokenAmountsFromGM(pool_data, self.amount)
            share = Decimal(self.amount / pool_data.marketTokensSupply)
            long_amount = Decimal(longAmount)
            short_amount = Decimal(shortAmount)
            net_value = Decimal(pool_data.poolValue) * share
        else:
            net_value = long_amount = short_amount = Decimal(0)

        if ((self.cumulative_borrowing['cumulativeBorrowingFactorLong']['value'] != self._market_status.data.cumulativeBorrowingFactorLong)
                or (self.cumulative_borrowing['cumulativeBorrowingFactorShort']['value'] != self._market_status.data.cumulativeBorrowingFactorShort)):
            self.cumulative_borrowing['cumulativeBorrowingFactorLong']['value'] = self._market_status.data.cumulativeBorrowingFactorLong
            self.cumulative_borrowing['cumulativeBorrowingFactorLong']['time'] = self._market_status.timestamp
            self.cumulative_borrowing['cumulativeBorrowingFactorShort']['value'] = self._market_status.data.cumulativeBorrowingFactorShort
            self.cumulative_borrowing['cumulativeBorrowingFactorShort']['time'] = self._market_status.timestamp
        # print(self._market_status.timestamp, self.cumulative_borrowing['cumulativeBorrowingFactorShort']['time'])
        pending_borrowing_time = (pd.to_datetime(self._market_status.timestamp) - pd.to_datetime(self.cumulative_borrowing['cumulativeBorrowingFactorShort']['time'])).seconds

        for key, position in self.position_list.items():
            if position.collateralToken == self.pool.short_token:
                collateralPrice = pool_data.shortPrice
            else:
                collateralPrice = pool_data.longPrice
            collateral_value = position.collateralAmount * collateralPrice
            # position_value = position.sizeInTokens * pool_data.indexPrice
            # pnl = position_value - position.sizeInUsd if position.isLong else position.sizeInUsd - position_value
            # net_value += Decimal(collateral_value + pnl)
            # print('net_value', net_value)

            positionInfo = ReaderPositionUtils.getPositionInfo(pending_borrowing_time, position, collateralPrice, self._market_status.data, self.pool_config, self.pool)
            # print('executionPrice', positionInfo.executionPriceResult.executionPrice, 'longPrice', pool_data.longPrice, 'shortPrice', pool_data.shortPrice, 'pnlAfterPriceImpactUsd', positionInfo.pnlAfterPriceImpactUsd, 'totalCostAmount', positionInfo.fees.totalCostAmount)
            net_value += Decimal(collateral_value + positionInfo.pnlAfterPriceImpactUsd - positionInfo.fees.totalCostAmount)

        return GmxV2Balance(
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
        value += get_formatted_predefined("positions", STYLE["key"]) + "\n"
        df = position_dict_to_dataframe(self.position_list)
        if len(df.index) > 0:
            value += df.to_string()
        else:
            value += "Empty DataFrame\n"
        return value

    def load_data(self, chain: ChainType, pool_address: str, start_date: date, end_date: date):
        self._data = load_gmx_v2_data(chain, pool_address, start_date, end_date, self.data_path)

    def get_price_from_data(self):
        if self.data is None:
            raise RuntimeError("data is None")
        return get_price_from_v2_data(self.data, self.pool)

    def _resample(self, freq: str):
        self._data.resample(freq=freq, inplace=True)

    def deposit(self, long_amount: Decimal | float, short_amount: Decimal | float) -> LPResult:
        assert long_amount >= 0 and short_amount >= 0
        long_amount = float(long_amount)
        short_amount = float(short_amount)
        result = ExecuteDepositUtils.get_mint_amount(self.pool_config, self._market_status.data, long_amount, short_amount)
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
        result: LPResult = ExecuteWithdrawUtils.getOutputAmount(self.pool_config, self._market_status.data, amount)
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

    def increase_position(
        self,
        initialCollateralToken,
        initialCollateralDeltaAmount,
        sizeDeltaUsd,
        isLong,
    ):
        position_key, result = ExecuteOrderUtils.executeOrder(
            market=self.pool.market_token.address,
            initialCollateralToken=initialCollateralToken,
            swapPath=[],
            orderType=OrderType.MarketIncrease,
            sizeDeltaUsd=sizeDeltaUsd,
            initialCollateralDeltaAmount=initialCollateralDeltaAmount,
            triggerPrice=0,
            acceptablePrice=0,
            isLong=isLong,
            decreasePositionSwapType=DecreasePositionSwapType.NoSwap,
            marketToken='',
            indexToken=self.pool.index_token,
            longToken=self.pool.long_token,
            shortToken=self.pool.short_token,
            pool_status=self._market_status.data,
            pool_config=self.pool_config,
            pool=self.pool,
            positions=self.position_list
        )
        self.position_list[position_key] = result
        if initialCollateralToken == self.short_token:
            self.broker.subtract_from_balance(self.short_token, Decimal(initialCollateralDeltaAmount))
        if initialCollateralToken == self.long_token:
            self.broker.subtract_from_balance(self.long_token, Decimal(initialCollateralDeltaAmount))

        self._record_action(
            Gmx2IncreasePositionAction(
                market=self.market_info,
                collateralToken=result.collateralToken,
                collateralAmount=UnitDecimal(result.collateralAmount),
                sizeInUsd=UnitDecimal(result.sizeInUsd),
                sizeInTokens=UnitDecimal(result.sizeInTokens),
                borrowingFactor=UnitDecimal(result.borrowingFactor),
                fundingFeeAmountPerSize=UnitDecimal(result.fundingFeeAmountPerSize),
                longTokenClaimableFundingAmountPerSize=UnitDecimal(result.longTokenClaimableFundingAmountPerSize),
                shortTokenClaimableFundingAmountPerSize=UnitDecimal(result.shortTokenClaimableFundingAmountPerSize),
                isLong=result.isLong,
            )
        )
        return result

    def decrease_position(
        self,
        initialCollateralToken,
        initialCollateralDeltaAmount,
        sizeDeltaUsd,
        isLong,
    ):
        position_key, result, outputToken, outputAmount, secondaryOutputToken, secondaryOutputAmount = ExecuteOrderUtils.executeOrder(
            market=self.pool.market_token.address,
            initialCollateralToken=initialCollateralToken,
            swapPath=[],
            orderType=OrderType.MarketDecrease,
            sizeDeltaUsd=sizeDeltaUsd,
            initialCollateralDeltaAmount=initialCollateralDeltaAmount,
            triggerPrice=0,
            acceptablePrice=0,
            isLong=isLong,
            decreasePositionSwapType=DecreasePositionSwapType.SwapPnlTokenToCollateralToken,
            marketToken=self.pool.market_token.address,
            indexToken=self.pool.index_token,
            longToken=self.pool.long_token,
            shortToken=self.pool.short_token,
            pool_status=self._market_status.data,
            pool_config=self.pool_config,
            pool=self.pool,
            positions=self.position_list
        )

        self.position_list[position_key] = result
        if result.sizeInUsd <= 0:
            self.position_list.pop(position_key, None)
        if outputToken == self.short_token.address:
            self.broker.add_to_balance(self.short_token, Decimal(outputAmount))
        if outputToken == self.long_token.address:
            self.broker.add_to_balance(self.long_token, Decimal(outputAmount))

        if secondaryOutputToken == self.short_token.address:
            self.broker.add_to_balance(self.short_token, Decimal(secondaryOutputAmount))
        if secondaryOutputToken == self.long_token.address:
            self.broker.add_to_balance(self.long_token, Decimal(secondaryOutputAmount))

        self._record_action(
            Gmx2DecreasePositionAction(
                market=self.market_info,
                collateralToken=result.collateralToken,
                collateralAmount=UnitDecimal(result.collateralAmount),
                sizeInUsd=UnitDecimal(result.sizeInUsd),
                sizeInTokens=UnitDecimal(result.sizeInTokens),
                borrowingFactor=UnitDecimal(result.borrowingFactor),
                fundingFeeAmountPerSize=UnitDecimal(result.fundingFeeAmountPerSize),
                longTokenClaimableFundingAmountPerSize=UnitDecimal(result.longTokenClaimableFundingAmountPerSize),
                shortTokenClaimableFundingAmountPerSize=UnitDecimal(result.shortTokenClaimableFundingAmountPerSize),
                isLong=result.isLong,
            )
        )
        return result
