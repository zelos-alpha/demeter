from dataclasses import dataclass
from decimal import Decimal
from typing import Union, NamedTuple

import pandas as pd

from .gmx_v2._typing import GmxV2PoolStatus
from .gmx_v2.position.Position import PositionKey, Position
from .. import TokenInfo, MarketStatus, BaseAction, ActionTypeEnum
from .._typing import MarketDescription, UnitDecimal
from ..broker import MarketBalance
from ..utils.console_text import get_action_str, ForColorEnum


class PrepKeys(NamedTuple):
    collateral: TokenInfo
    is_long: bool


@dataclass
class GmxV2LpBalance(MarketBalance):
    gm_amount: Decimal
    long_amount: Decimal
    short_amount: Decimal


@dataclass
class PositionValue:
    leverage: Decimal
    size: Decimal
    net_value: Decimal
    initial_collateral: Decimal
    initial_collateral_usd: Decimal
    finial_collateral: Decimal
    finial_collateral_usd: Decimal
    borrow_fee_usd: Decimal
    negative_funding_fee_usd: Decimal
    positive_funding_fee_usd: Decimal
    net_price_impact_usd: Decimal
    close_fee_usd: Decimal
    pnl: Decimal
    pnl_after_fee_usd: Decimal
    entry_price: Decimal
    market_price: Decimal


@dataclass
class GmxV2PrepBalance(MarketBalance):
    position_count:int
    total_pnl: Decimal
    collateral_long: Decimal
    collateral_short: Decimal
    collateral_usd: Decimal


@dataclass
class GmxV2LpDescription(MarketDescription):
    amount: float


@dataclass
class GmxV2PrepDescription(MarketDescription):
    long_token: str
    short_token: str
    index_token: str

@dataclass
class GmxV2LpMarketStatus(MarketStatus):
    data: Union[pd.Series, GmxV2PoolStatus]


@dataclass
class Gmx2WithdrawAction(BaseAction):
    gm_amount: UnitDecimal
    gm_usd: UnitDecimal
    long_amount: UnitDecimal
    short_amount: UnitDecimal
    withdraw_usd: UnitDecimal
    long_fee: UnitDecimal
    short_fee: UnitDecimal
    fee_usd: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.gmx2_withdraw

    def get_output_str(self):
        return get_action_str(
            self,
            ForColorEnum.light_red,
            {
                "gm_amount": self.gm_amount.to_str(),
                "gm_usd": self.gm_usd.to_str(),
                "long_amount": self.long_amount.to_str(),
                "short_amount": self.short_amount.to_str(),
                "withdraw_usd": self.withdraw_usd.to_str(),
                "fee_usd": self.fee_usd.to_str(),
            },
        )


def position_dict_to_dataframe(positions: dict) -> pd.DataFrame:
    positions = list(positions.copy().values())
    for index, position in enumerate(positions):
        positions[index].market= str(position.market)
        positions[index].collateralToken= str(position.collateralToken)
    return pd.DataFrame(positions)


@dataclass
class Gmx2DepositAction(BaseAction):
    long_amount: UnitDecimal
    short_amount: UnitDecimal
    deposit_usd: UnitDecimal
    gm_amount: UnitDecimal
    gm_usd: UnitDecimal
    long_fee: UnitDecimal
    short_fee: UnitDecimal
    fee_usd: UnitDecimal
    price_impact_usd: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.gmx2_deposit

    def get_output_str(self):

        return get_action_str(
            self,
            ForColorEnum.light_green,
            {
                "long_amount": self.long_amount.to_str(),
                "short_amount": self.short_amount.to_str(),
                "deposit_usd": self.deposit_usd.to_str(),
                "gm_amount": self.gm_amount.to_str(),
                "gm_usd": self.gm_usd.to_str(),
                "fee_usd": self.fee_usd.to_str(),
                "price_impact_usd": self.price_impact_usd.to_str(),
            },
        )


@dataclass
class Gmx2IncreasePositionAction(BaseAction):
    collateralToken: str
    isLong: bool
    collateralAmount: UnitDecimal
    sizeInUsd: UnitDecimal
    borrowingFactor: UnitDecimal
    fundingFeeAmountPerSize: UnitDecimal
    longTokenClaimableFundingAmountPerSize: UnitDecimal
    shortTokenClaimableFundingAmountPerSize: UnitDecimal
    funding: UnitDecimal
    borrowing: UnitDecimal
    liquidation: UnitDecimal
    collateralTokenPrice: UnitDecimal
    positionFeeAmount: UnitDecimal
    protocolFeeAmount: UnitDecimal
    totalCostAmountExcludingFunding: UnitDecimal
    totalCostAmount: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.gmx2_increase_position

    def get_output_str(self):
        return get_action_str(
            self,
            ForColorEnum.light_green,
            {
                "collateralToken": self.collateralToken,
                "isLong": str(self.isLong),
                "collateralAmount": self.collateralAmount.to_str(),
                "sizeInUsd": self.sizeInUsd.to_str(),
                "borrowingFactor": self.borrowingFactor.to_str(),
                "fundingFeeAmountPerSize": self.fundingFeeAmountPerSize.to_str(),
                "longTokenClaimableFundingAmountPerSize": self.longTokenClaimableFundingAmountPerSize.to_str(),
                "shortTokenClaimableFundingAmountPerSize": self.shortTokenClaimableFundingAmountPerSize.to_str(),
                "funding": self.funding.to_str(),
                "borrowing": self.borrowing.to_str(),
                "liquidation": self.liquidation.to_str(),
                "collateralTokenPrice": self.collateralTokenPrice.to_str(),
                "positionFeeAmount": self.positionFeeAmount.to_str(),
                "protocolFeeAmount": self.protocolFeeAmount.to_str(),
                "totalCostAmountExcludingFunding": self.totalCostAmountExcludingFunding.to_str(),
                "totalCostAmount": self.totalCostAmount.to_str(),
            },
        )


@dataclass
class Gmx2DecreasePositionAction(BaseAction):
    collateralToken: str
    remainingCollateralAmount: UnitDecimal
    isLong: bool
    outputAmount: UnitDecimal
    secondaryOutputAmount: UnitDecimal
    orderSizeDeltaUsd: UnitDecimal
    orderInitialCollateralDeltaAmount: UnitDecimal
    basePnlUsd: UnitDecimal
    priceImpactUsd: UnitDecimal
    fundingFeeAmount: UnitDecimal
    borrowingFeeUsd: UnitDecimal
    liquidationFeeUsd: UnitDecimal
    collateralTokenPrice: UnitDecimal
    positionFeeAmount: UnitDecimal
    protocolFeeAmount: UnitDecimal
    totalCostAmountExcludingFunding: UnitDecimal
    totalCostAmount: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.gmx2_decrease_position

    def get_output_str(self):
        return get_action_str(
            self,
            ForColorEnum.light_green,
            {
                "collateralToken": self.collateralToken,
                "remainingCollateralAmount": self.remainingCollateralAmount.to_str(),
                "isLong": str(self.isLong),
                "outputAmount": self.outputAmount.to_str(),
                "secondaryOutputAmount": self.secondaryOutputAmount.to_str(),
                "orderSizeDeltaUsd": self.orderSizeDeltaUsd.to_str(),
                "orderInitialCollateralDeltaAmount": self.orderInitialCollateralDeltaAmount.to_str(),
                "basePnlUsd": self.basePnlUsd.to_str(),
                "priceImpactUsd": self.priceImpactUsd.to_str(),
                "fundingFeeAmount": self.fundingFeeAmount.to_str(),
                "borrowingFeeUsd": self.borrowingFeeUsd.to_str(),
                "liquidationFeeUsd": self.liquidationFeeUsd.to_str(),
                "collateralTokenPrice": self.collateralTokenPrice.to_str(),
                "positionFeeAmount": self.positionFeeAmount.to_str(),
                "protocolFeeAmount": self.protocolFeeAmount.to_str(),
                "totalCostAmountExcludingFunding": self.totalCostAmountExcludingFunding.to_str(),
                "totalCostAmount": self.totalCostAmount.to_str(),
            },
        )


@dataclass
class Gmx2SwapAction(BaseAction):
    inToken: TokenInfo
    inAmount: UnitDecimal
    outToken: TokenInfo
    outAmount: UnitDecimal
    feeToken: TokenInfo
    fee: UnitDecimal
    priceImpactToken: TokenInfo
    priceImpact: UnitDecimal
    priceImpactUsd: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.gmx2_swap

    def get_output_str(self):
        return get_action_str(
            self,
            ForColorEnum.light_green,
            {
                "inToken": self.inToken.name,
                "inAmount": self.inAmount.to_str(),
                "outToken": self.outToken.name,
                "outAmount": self.outAmount.to_str(),
                "feeToken": self.feeToken.name,
                "fee": self.fee.to_str(),
                "priceImpactToken": self.priceImpactToken.name,
                "priceImpact": self.priceImpact.to_str(),
                "priceImpactUsd": self.priceImpactUsd.to_str(),
            },
        )
