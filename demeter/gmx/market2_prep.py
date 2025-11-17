from datetime import date
from decimal import Decimal

import pandas as pd
from orjson import orjson

from ._typing2 import (
    GmxV2LpMarketStatus,
    GmxV2LpBalance,
    GmxV2PoolStatus,
    Gmx2IncreasePositionAction,
    Gmx2DecreasePositionAction,
    position_dict_to_dataframe,
    GmxV2PrepDescription,
    Gmx2SwapAction,
)
from .gmx_v2 import PoolConfig, GmxV2Pool
from .gmx_v2.order import SwapOrderUtils
from .gmx_v2.order.ExecuteOrderUtils import ExecuteOrderUtils
from .gmx_v2.market.MarketUtils import MarketUtils
from .gmx_v2.reader.ReaderPositionUtils import ReaderPositionUtils
from .gmx_v2._typing import OrderType, DecreasePositionSwapType, PoolStatus, Order, ExecuteOrderParams
from .gmx_v2.swap.SwapUtils import SwapResult
from .helper2 import load_gmx_v2_data, get_price_from_v2_data
from .. import TokenInfo, DECIMAL_0, ChainType, UnitDecimal, DemeterError
from .._typing import USD
from ..broker import MarketInfo
from ..broker.prep_market import PrepMarket
from ..utils import get_formatted_predefined, get_formatted_from_dict, STYLE, require


class GmxV2PerpMarket(PrepMarket):
    def __init__(
        self, market_info: MarketInfo, pool: GmxV2Pool, data: pd.DataFrame | None = None, data_path: str = "./data"
    ):
        super().__init__(market_info=market_info, data=data, data_path=data_path)
        self.pool: GmxV2Pool = pool

        self.cumulative_borrowing = {
            "cumulativeBorrowingFactorLong": {"value": 0, "time": None},
            "cumulativeBorrowingFactorShort": {"value": 0, "time": None},
        }
        self.pool_config = PoolConfig(pool.long_token.decimal, pool.short_token.decimal)

    # region prop

    def __str__(self):
        from demeter.utils import orjson_default

        # return repr(self.description().__dict__)
        return orjson.dumps(self.description, default=orjson_default).decode()

    @property
    def description(self) -> GmxV2PrepDescription:
        return GmxV2PrepDescription(
            type=type(self).__name__,
            name=self._market_info.name,
            Positions=self.positions,
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
        # 仓位	规模	净值	抵押品	入场价格	标记价格	清算价格

        pool_data: GmxV2PoolStatus = self._market_status.data
        if self.amount > 0:
            longAmount, shortAmount = MarketUtils.getTokenAmountsFromGM(pool_data, self.amount)
            share = Decimal(self.amount / pool_data.marketTokensSupply)
            long_amount = Decimal(longAmount)
            short_amount = Decimal(shortAmount)
            net_value = Decimal(pool_data.poolValue) * share
        else:
            net_value = long_amount = short_amount = Decimal(0)

        if (
            self.cumulative_borrowing["cumulativeBorrowingFactorLong"]["value"]
            != self._market_status.data.cumulativeBorrowingFactorLong
        ) or (
            self.cumulative_borrowing["cumulativeBorrowingFactorShort"]["value"]
            != self._market_status.data.cumulativeBorrowingFactorShort
        ):
            self.cumulative_borrowing["cumulativeBorrowingFactorLong"][
                "value"
            ] = self._market_status.data.cumulativeBorrowingFactorLong
            self.cumulative_borrowing["cumulativeBorrowingFactorLong"]["time"] = self._market_status.timestamp
            self.cumulative_borrowing["cumulativeBorrowingFactorShort"][
                "value"
            ] = self._market_status.data.cumulativeBorrowingFactorShort
            self.cumulative_borrowing["cumulativeBorrowingFactorShort"]["time"] = self._market_status.timestamp
        # print(self._market_status.timestamp, self.cumulative_borrowing['cumulativeBorrowingFactorShort']['time'])
        pending_borrowing_time = (
            pd.to_datetime(self._market_status.timestamp)
            - pd.to_datetime(self.cumulative_borrowing["cumulativeBorrowingFactorShort"]["time"])
        ).seconds

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

            positionInfo = ReaderPositionUtils.getPositionInfo(
                pending_borrowing_time, position, collateralPrice, self._market_status.data, self.pool_config, self.pool
            )
            # print('executionPrice', positionInfo.executionPriceResult.executionPrice, 'longPrice', pool_data.longPrice, 'shortPrice', pool_data.shortPrice, 'pnlAfterPriceImpactUsd', positionInfo.pnlAfterPriceImpactUsd, 'totalCostAmount', positionInfo.fees.totalCostAmount)
            net_value += Decimal(
                collateral_value + positionInfo.pnlAfterPriceImpactUsd - positionInfo.fees.totalCostAmount
            )

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

    def increase_position(
        self,
        initialCollateralToken,
        initialCollateralDeltaAmount,
        sizeDeltaUsd,
        isLong,
    ):

        pool_status = {self.pool: PoolStatus(self._market_status.data, self.pool_config)}
        order = Order(
            market=self.pool,
            initialCollateralToken=initialCollateralToken,
            swapPath=[],
            orderType=OrderType.MarketIncrease,
            sizeDeltaUsd=sizeDeltaUsd,
            initialCollateralDeltaAmount=initialCollateralDeltaAmount,
            triggerPrice=0,
            acceptablePrice=0,
            isLong=isLong,
            decreasePositionSwapType=DecreasePositionSwapType.NoSwap,
        )

        position_key, result = ExecuteOrderUtils.executeOrder(
            order=order,
            status=pool_status,
            positions=self.position_list,
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

        pool_status = {self.pool: PoolStatus(self._market_status.data, self.pool_config)}

        order = Order(
            market=self.pool,
            initialCollateralToken=initialCollateralToken,
            swapPath=[],
            orderType=OrderType.MarketDecrease,
            sizeDeltaUsd=sizeDeltaUsd,
            initialCollateralDeltaAmount=initialCollateralDeltaAmount,
            triggerPrice=0,
            acceptablePrice=0,
            isLong=isLong,
            decreasePositionSwapType=DecreasePositionSwapType.SwapPnlTokenToCollateralToken,
        )

        position_key, result, outputToken, outputAmount, secondaryOutputToken, secondaryOutputAmount = (
            ExecuteOrderUtils.executeOrder(
                order=order,
                status=pool_status,
                positions=self.position_list,
            )
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

    def _do_swap(self, from_token: TokenInfo, amount: float | Decimal) -> tuple[TokenInfo, Decimal, SwapResult]:
        if from_token not in [self.pool.long_token, self.pool.short_token]:
            raise DemeterError("Swap token must be long or short")
        amount = float(amount)
        pool_status = {self.pool: PoolStatus(self._market_status.data, self.pool_config)}

        order = Order(
            market=self.pool,
            initialCollateralToken=from_token,
            swapPath=[self.pool],
            orderType=OrderType.MarketSwap,
            sizeDeltaUsd=0,
            initialCollateralDeltaAmount=amount,
        )
        params = ExecuteOrderParams(order=order, swapPathMarkets=order.swapPath, market=order.market)
        out_token, out_amount, swap_result = SwapOrderUtils.processOrder(params, pool_status)
        if len(swap_result) != 1:
            raise DemeterError("Swap result should only contain 1 swap")
        swap_result0: SwapResult = swap_result[0]

        return out_token, Decimal(out_amount), swap_result0

    def swap(self, from_token: TokenInfo, amount: float | Decimal) -> tuple[TokenInfo, Decimal, SwapResult]:
        out_token, out_amount, swap_result = self._do_swap(from_token, amount)

        self.broker.subtract_from_balance(from_token, Decimal(amount))
        self.broker.add_to_balance(out_token, Decimal(out_amount))

        self._record_action(
            Gmx2SwapAction(
                market=self.market_info,
                inToken=from_token,
                inAmount=UnitDecimal(amount, from_token.name),
                outToken=out_token,
                outAmount=UnitDecimal(out_amount, out_token.name),
                feeToken=swap_result.feeToken,
                fee=UnitDecimal(swap_result.fee, swap_result.feeToken.name),
                priceImpactToken=swap_result.priceImpactToken,
                priceImpact=UnitDecimal(swap_result.priceImpact, swap_result.priceImpactToken.name),
                priceImpactUsd=UnitDecimal(swap_result.priceImpactUsd, "USD"),
            )
        )

        return out_token, Decimal(out_amount), swap_result
