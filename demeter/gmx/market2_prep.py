from datetime import date
from decimal import Decimal

import pandas as pd
from orjson import orjson

from ._typing2 import (
    GmxV2LpMarketStatus,
    GmxV2PoolStatus,
    Gmx2IncreasePositionAction,
    position_dict_to_dataframe,
    GmxV2PrepDescription,
    Gmx2SwapAction,
    GmxV2PrepBalance,
    PositionValue,
)
from .gmx_v2 import PoolConfig, GmxV2Pool
from .gmx_v2._typing import OrderType, DecreasePositionSwapType, PoolData, Order, ExecuteOrderParams
from .gmx_v2.order import SwapOrderUtils, IncreaseOrderUtils, DecreaseOrderUtils
from .gmx_v2.position import Position, PositionKey
from .gmx_v2.pricing import PositionFees
from .gmx_v2.reader.ReaderPositionUtils import ReaderPositionUtils, PositionInfo
from .gmx_v2.swap.SwapUtils import SwapResult
from .helper2 import load_gmx_v2_data, get_price_from_v2_data
from .utils import load_pool_config
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
        self.positions: dict[PositionKey, Position] = {}
        self.claimableFundingAmount: dict[TokenInfo, float] = {
            self.pool.long_token: 0,
            self.pool.short_token: 0,
        }

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
    def load_config(self, path):
        self.pool_config = load_pool_config(path)

    def check_market(self):
        super().check_market()
        require(self.quote_token == USD, "Quote token of GMX v2 market must be USD")

        if self.long_token not in self.broker.assets:
            self.broker.set_balance(self.long_token, DECIMAL_0)
        if self.short_token not in self.broker.assets:
            self.broker.set_balance(self.short_token, DECIMAL_0)

    def update(self):
        # TODO 清算逻辑
        pass

    def set_market_status(self, data: GmxV2LpMarketStatus | pd.Series, price: pd.Series):
        super().set_market_status(data, price)
        data.data = self.data.loc[data.timestamp]
        self._market_status = data

    def get_position_info(self, position_key: PositionKey) -> PositionInfo:
        position = self.positions[position_key]
        return ReaderPositionUtils.getPositionInfo(
            position,
            0,
            True,
            PoolData(self.pool, self._market_status.data, self.pool_config),
        )

    def _get_position_value(self, position_info: PositionInfo, pool_status: GmxV2PoolStatus) -> PositionValue:
        collateral_price = (
            pool_status.longPrice
            if self.pool.long_token == position_info.position.collateralToken
            else pool_status.shortPrice
        )
        initial_collateral_usd = position_info.position.collateralAmount * collateral_price

        final_collateral_amount = (
            position_info.position.collateralAmount
            - position_info.fees.funding.fundingFeeAmount
            - position_info.fees.borrowing.borrowingFeeAmount
        )
        final_collateral_usd = final_collateral_amount * collateral_price

        funding_fee_usd = position_info.fees.funding.fundingFeeAmount * collateral_price
        claimable_funding = (
            position_info.fees.funding.claimableLongTokenAmount * pool_status.longPrice
            + position_info.fees.funding.claimableShortTokenAmount * pool_status.shortPrice
        )
        pnl_after_fee_usd = (
            position_info.basePnlUsd
            - position_info.fees.borrowing.borrowingFeeUsd
            - funding_fee_usd
            - position_info.executionPriceResult.totalImpactUsd
            - position_info.fees.positionFeeAmount * collateral_price
        )

        net_value = initial_collateral_usd + pnl_after_fee_usd

        balance = PositionValue(
            leverage=Decimal(position_info.position.sizeInUsd / final_collateral_usd),
            size=Decimal(position_info.position.sizeInUsd),
            net_value=Decimal(net_value),
            initial_collateral_usd=Decimal(initial_collateral_usd),
            initial_collateral=Decimal(position_info.position.collateralAmount),
            finial_collateral_usd=Decimal(final_collateral_usd),
            finial_collateral=Decimal(final_collateral_amount),
            borrow_fee_usd=Decimal(position_info.fees.borrowing.borrowingFeeUsd),
            negative_funding_fee_usd=Decimal(funding_fee_usd),
            positive_funding_fee_usd=Decimal(claimable_funding),
            net_price_impact_usd=Decimal(position_info.executionPriceResult.totalImpactUsd),
            close_fee_usd=Decimal(position_info.fees.positionFeeAmount * collateral_price),
            pnl=Decimal(position_info.basePnlUsd),
            pnl_after_fee_usd=Decimal(pnl_after_fee_usd),
            entry_price=Decimal(position_info.position.sizeInUsd / position_info.position.sizeInTokens),
            market_price=Decimal(pool_status.indexPrice),
            liq_price=Decimal(0),
        )
        return balance

    def get_position_value(self, position_key: PositionKey) -> PositionValue:
        pool_status: GmxV2PoolStatus = self._market_status.data
        position_info = self.get_position_info(position_key)
        return self._get_position_value(position_info, pool_status)

    def get_market_balance(self) -> GmxV2PrepBalance:
        position_balances: list[PositionValue] = []
        net_value = 0
        pool_status: GmxV2PoolStatus = self._market_status.data
        for key, position in self.positions.items():
            position_info = self.get_position_info(key)
            position_value = self._get_position_value(position_info, pool_status)
            net_value += position_value.net_value
            position_balances.append(position_value)

        return GmxV2PrepBalance(net_value=net_value, positions=position_balances)

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
        collateral_token: TokenInfo,
        collateral_amount: float | Decimal,
        is_long: bool,
        expect_size_in_token: float | Decimal | None = None,
        size_in_usd: float | Decimal | None = None,
    ) -> tuple[Position, PositionFees]:
        if size_in_usd is None and expect_size_in_token is None:
            raise DemeterError("size_in_usd or size_in_token is required")
        elif size_in_usd is not None and expect_size_in_token is not None:
            print("Warning, size_in_token and size_in_usd is filled, will use size_in_usd")
        if size_in_usd is None:
            size_in_usd = expect_size_in_token * self._market_status.data.longPrice
        order = Order(
            market=self.pool,
            initialCollateralToken=collateral_token,
            swapPath=[],  # do not allow collateral with other token, you can swap manually if needed.
            orderType=OrderType.MarketIncrease,
            sizeDeltaUsd=size_in_usd,
            initialCollateralDeltaAmount=collateral_amount,
            isLong=is_long,
            decreasePositionSwapType=DecreasePositionSwapType.NoSwap,
        )
        params = ExecuteOrderParams(order=order, swapPathMarkets=order.swapPath, market=order.market)
        pool_status = {self.pool: PoolData(self.pool, self._market_status.data, self.pool_config)}

        position_key: PositionKey = Position.getPositionKey(self.pool, collateral_token, is_long)

        updated_position, fees = IncreaseOrderUtils.processOrder(
            params, pool_status, self.positions.get(position_key), self.claimableFundingAmount
        )

        self.positions[position_key] = updated_position

        self.broker.subtract_from_balance(collateral_token, Decimal(collateral_amount))

        self._record_action(
            Gmx2IncreasePositionAction(
                market=self.market_info,
                collateralToken=collateral_token.name,
                collateralAmount=UnitDecimal(collateral_amount, collateral_token.name),
                sizeInUsd=UnitDecimal(size_in_usd, "USD"),
                borrowingFactor=UnitDecimal(updated_position.borrowingFactor),
                fundingFeeAmountPerSize=UnitDecimal(updated_position.fundingFeeAmountPerSize),
                longTokenClaimableFundingAmountPerSize=UnitDecimal(
                    updated_position.longTokenClaimableFundingAmountPerSize
                ),
                shortTokenClaimableFundingAmountPerSize=UnitDecimal(
                    updated_position.shortTokenClaimableFundingAmountPerSize
                ),
                isLong=updated_position.isLong,
                funding=UnitDecimal(fees.funding.fundingFeeAmount, collateral_token.name),
                borrowing=UnitDecimal(fees.borrowing.borrowingFeeAmount, collateral_token.name),
                liquidation=UnitDecimal(fees.liquidation.liquidationFeeAmount, collateral_token.name),
                collateralTokenPrice=UnitDecimal(fees.collateralTokenPrice, collateral_token.name),
                positionFeeAmount=UnitDecimal(fees.positionFeeAmount, collateral_token.name),
                protocolFeeAmount=UnitDecimal(fees.positionFeeAmount, collateral_token.name),
                totalCostAmountExcludingFunding=UnitDecimal(
                    fees.totalCostAmountExcludingFunding, collateral_token.name
                ),
                totalCostAmount=UnitDecimal(fees.totalCostAmount, collateral_token.name),
            )
        )
        return updated_position, fees

    def decrease_position(
        self,
        collateral_token: TokenInfo,
        collateral_amount: float | Decimal,
        size_usd: float | Decimal,
        is_long: bool,
    ) -> Position:
        order = Order(
            market=self.pool,
            initialCollateralToken=collateral_token,
            swapPath=[],
            orderType=OrderType.MarketDecrease,
            sizeDeltaUsd=size_usd,
            initialCollateralDeltaAmount=collateral_amount,
            isLong=is_long,
            decreasePositionSwapType=DecreasePositionSwapType.SwapPnlTokenToCollateralToken,
        )
        params = ExecuteOrderParams(order=order, swapPathMarkets=order.swapPath, market=order.market)
        pool_status = {self.pool: PoolData(self.pool, self._market_status.data, self.pool_config)}
        position_key: PositionKey = Position.getPositionKey(self.pool, collateral_token, is_long)

        decrease_result, fees = DecreaseOrderUtils.processOrder(
            params, pool_status, self.positions[position_key], self.claimableFundingAmount
        )

        if decrease_result.position is None:
            del self.positions[position_key]
        else:
            self.positions[position_key] = decrease_result.position

        self.broker.add_to_balance(decrease_result.outputToken, decrease_result.outputAmount)
        self.broker.add_to_balance(decrease_result.secondaryOutputToken, decrease_result.secondaryOutputAmount)

        # self._record_action(
        #     Gmx2DecreasePositionAction(
        #         market=self.market_info,
        #         collateralToken=result.collateralToken,
        #         collateralAmount=UnitDecimal(result.collateralAmount),
        #         sizeInUsd=UnitDecimal(result.sizeInUsd),
        #         sizeInTokens=UnitDecimal(result.sizeInTokens),
        #         borrowingFactor=UnitDecimal(result.borrowingFactor),
        #         fundingFeeAmountPerSize=UnitDecimal(result.fundingFeeAmountPerSize),
        #         longTokenClaimableFundingAmountPerSize=UnitDecimal(result.longTokenClaimableFundingAmountPerSize),
        #         shortTokenClaimableFundingAmountPerSize=UnitDecimal(result.shortTokenClaimableFundingAmountPerSize),
        #         isLong=result.isLong,
        #     )
        # )
        return decrease_result.position

    def _do_swap(self, from_token: TokenInfo, amount: float | Decimal) -> tuple[TokenInfo, Decimal, SwapResult]:
        if from_token not in [self.pool.long_token, self.pool.short_token]:
            raise DemeterError("Swap token must be long or short")
        amount = float(amount)
        pool_status = {self.pool: PoolData(self.pool, self._market_status.data, self.pool_config)}

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
