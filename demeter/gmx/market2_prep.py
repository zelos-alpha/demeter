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
    Gmx2DecreasePositionAction,
)
from .gmx_v2 import PoolConfig, GmxV2Pool
from .gmx_v2._typing import OrderType, DecreasePositionSwapType, PoolData, Order, ExecuteOrderParams
from .gmx_v2.market import MarketPrices
from .gmx_v2.order import SwapOrderUtils, IncreaseOrderUtils, DecreaseOrderUtils
from .gmx_v2.position import (
    Position,
    PositionKey,
    DecreasePositionResult,
    DecreasePositionCollateralValues,
    PositionUtils,
)
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
        self.pool_config = PoolConfig()
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
            long_token=self.pool.long_token.name,
            short_token=self.pool.short_token.name,
            index_token=self.pool.index_token.name,
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
        pool_data = PoolData(self.pool, self._market_status.data, self.pool_config)
        for pos_key in list(self.positions.keys()):
            if not self.out_of_danger_price(self.positions[pos_key]):
                continue
            if self.is_position_liquidatable(self.positions[pos_key], pool_data):
                self.liquidation(pos_key)

    def is_position_liquidatable(self, pos, pool_data: PoolData) -> bool:
        should_liquidate, msg, info = PositionUtils.isPositionLiquidatable(
            pos,
            MarketPrices(pool_data.status.indexPrice, pool_data.status.longPrice, pool_data.status.shortPrice),
            True,
            True,
            pool_data,
        )
        return should_liquidate

    def out_of_danger_price(self, pos_info: Position) -> bool:
        # pre-check the position is liquidatable. to avoid slow calculation.
        pool_status: GmxV2PoolStatus = self._market_status.data
        init_price = pos_info.sizeInUsd / pos_info.sizeInTokens
        collateral_price = (
            pool_status.longPrice if self.pool.long_token == pos_info.collateralToken else pool_status.shortPrice
        )
        collateral_usd = pos_info.collateralAmount * collateral_price
        if pos_info.isLong:
            liq_price = (pos_info.sizeInUsd - collateral_usd) / pos_info.sizeInTokens
        else:
            liq_price = (pos_info.sizeInUsd + collateral_usd) / pos_info.sizeInTokens

        price_diff = abs(liq_price - init_price) / 2
        if pos_info.isLong:
            return pool_status.indexPrice < (init_price - price_diff)
        else:
            return pool_status.indexPrice > (init_price + price_diff)

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
        )
        return balance

    def get_position_value(self, position_key: PositionKey) -> PositionValue:
        pool_status: GmxV2PoolStatus = self._market_status.data
        position_info = self.get_position_info(position_key)
        return self._get_position_value(position_info, pool_status)

    def get_market_balance(self) -> GmxV2PrepBalance:
        position_balances: list[PositionValue] = []
        net_value = total_pnl = collateral_long = collateral_short = collateral_usd = Decimal(0)
        pool_status: GmxV2PoolStatus = self._market_status.data
        for key, position in self.positions.items():
            position_info: PositionInfo = self.get_position_info(key)
            position_value: PositionValue = self._get_position_value(position_info, pool_status)
            total_pnl += position_value.pnl_after_fee_usd
            net_value += position_value.net_value
            collateral_usd += position_value.finial_collateral_usd
            position_balances.append(position_value)
            if position_info.position.collateralToken == self.pool.long_token:
                collateral_long += position_value.finial_collateral
            elif position_info.position.collateralToken == self.pool.short_token:
                collateral_short += position_value.finial_collateral

        return GmxV2PrepBalance(
            net_value=net_value,
            position_count=len(self.positions),
            total_pnl=total_pnl,
            collateral_long=collateral_long,
            collateral_short=collateral_short,
            collateral_usd=collateral_usd,
        )

    def formatted_str(self):
        value = get_formatted_predefined(f"{self.market_info.name}({type(self).__name__})", STYLE["header3"]) + "\n"
        value += (
            get_formatted_from_dict(
                {
                    "market": str(self.pool),
                }
            )
            + "\n"
        )
        value += get_formatted_predefined("positions", STYLE["key"]) + "\n"
        df = position_dict_to_dataframe(self.positions)
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
        self._data = self.data.resample(freq).first()

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
                collateralTokenPrice=UnitDecimal(fees.collateralTokenPrice, f"{collateral_token.name}/usd"),
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
        is_long: bool,
        size_in_usd: float | Decimal | None = None,
        collateral_amount: float | Decimal | None = None,
    ) -> tuple[DecreasePositionResult, DecreasePositionCollateralValues, PositionFees]:
        position_key: PositionKey = Position.getPositionKey(self.pool, collateral_token, is_long)

        if position_key not in self.positions:
            raise DemeterError("Position not found")

        if size_in_usd is None and collateral_amount is None:
            size_in_usd = self.positions[position_key].sizeInUsd
            collateral_amount = self.positions[position_key].collateralAmount
        if collateral_amount is None or size_in_usd is None:
            raise DemeterError("size_in_usd and collateral_amount not specified")

        order = Order(
            market=self.pool,
            initialCollateralToken=collateral_token,
            swapPath=[],
            orderType=OrderType.MarketDecrease,
            sizeDeltaUsd=size_in_usd,
            initialCollateralDeltaAmount=collateral_amount,
            isLong=is_long,
            decreasePositionSwapType=DecreasePositionSwapType.SwapPnlTokenToCollateralToken,
        )
        return self._execute_decrease_order(order, position_key, collateral_token)

    def _execute_decrease_order(
        self, order: Order, position_key: PositionKey, collateral_token: TokenInfo
    ) -> tuple[DecreasePositionResult, DecreasePositionCollateralValues, PositionFees]:
        params = ExecuteOrderParams(order=order, swapPathMarkets=order.swapPath, market=order.market)
        pool_status = {self.pool: PoolData(self.pool, self._market_status.data, self.pool_config)}

        decrease_result, values, fees = DecreaseOrderUtils.processOrder(
            params, pool_status, self.positions[position_key], self.claimableFundingAmount
        )

        if decrease_result.position is None:
            del self.positions[position_key]
        else:
            self.positions[position_key] = decrease_result.position

        self.broker.add_to_balance(decrease_result.outputToken, decrease_result.outputAmount)
        self.broker.add_to_balance(decrease_result.secondaryOutputToken, decrease_result.secondaryOutputAmount)

        self._record_action(
            Gmx2DecreasePositionAction(
                market=self.market_info,
                collateralToken=collateral_token.name,
                remainingCollateralAmount=UnitDecimal(
                    0 if decrease_result.position is None else decrease_result.position.collateralAmount,
                    collateral_token.name,
                ),
                isLong=order.isLong,
                outputAmount=UnitDecimal(decrease_result.outputAmount, decrease_result.outputToken.name),
                secondaryOutputAmount=UnitDecimal(
                    decrease_result.secondaryOutputAmount, decrease_result.secondaryOutputToken.name
                ),
                orderSizeDeltaUsd=UnitDecimal(decrease_result.orderSizeDeltaUsd, "USD"),
                orderInitialCollateralDeltaAmount=UnitDecimal(
                    decrease_result.orderInitialCollateralDeltaAmount, collateral_token.name
                ),
                basePnlUsd=UnitDecimal(values.basePnlUsd, "USD"),
                priceImpactUsd=UnitDecimal(values.priceImpactUsd, "USD"),
                fundingFeeAmount=UnitDecimal(fees.funding.fundingFeeAmount, self.pool.index_token.name),
                borrowingFeeUsd=UnitDecimal(fees.borrowing.borrowingFeeUsd, "USD"),
                liquidationFeeUsd=UnitDecimal(fees.liquidation.liquidationFeeUsd, "USD"),
                collateralTokenPrice=UnitDecimal(fees.collateralTokenPrice, f"{collateral_token.name}/usd"),
                positionFeeAmount=UnitDecimal(fees.positionFeeAmount, collateral_token.name),
                protocolFeeAmount=UnitDecimal(fees.protocolFeeAmount, collateral_token.name),
                totalCostAmountExcludingFunding=UnitDecimal(
                    fees.totalCostAmountExcludingFunding, collateral_token.name
                ),
                totalCostAmount=UnitDecimal(fees.totalCostAmount, collateral_token.name),
            )
        )
        return decrease_result, values, fees

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

    def liquidation(
        self, position_key
    ) -> tuple[DecreasePositionResult, DecreasePositionCollateralValues, PositionFees]:
        if position_key not in self.positions:
            raise DemeterError("Position not found")
        position = self.positions[position_key]

        order = Order(
            market=self.pool,
            initialCollateralToken=position.collateralToken,
            swapPath=[],
            orderType=OrderType.Liquidation,
            sizeDeltaUsd=position.sizeInUsd,
            initialCollateralDeltaAmount=0,
            isLong=position.isLong,
            decreasePositionSwapType=DecreasePositionSwapType.SwapPnlTokenToCollateralToken,
        )
        return self._execute_decrease_order(order, position_key, position.collateralToken)
