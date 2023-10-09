from _decimal import Decimal
from typing import Dict

from demeter import DECIMAL_0, TokenInfo
from demeter.aave._typing import SupplyKey, ActionKey, BorrowKey
import pandas as pd


class AaveV3CoreLib(object):
    SECONDS_IN_A_YEAR = 31536000
    """
    if CLOSE_FACTOR_HF_THRESHOLD < health factor <  DEFAULT_LIQUIDATION_CLOSE_FACTOR
    only DEFAULT_LIQUIDATION_CLOSE_FACTOR(50%) will be liquidated,
    otherwise HEALTH_FACTOR_LIQUIDATION_THRESHOLD(100%) will be liquidated
    """
    HEALTH_FACTOR_LIQUIDATION_THRESHOLD = Decimal(1)
    DEFAULT_LIQUIDATION_CLOSE_FACTOR = Decimal(0.5)
    MAX_LIQUIDATION_CLOSE_FACTOR = Decimal(1)
    CLOSE_FACTOR_HF_THRESHOLD = Decimal(0.95)

    @staticmethod
    def rate_to_apy(rate: Decimal) -> Decimal:
        return (1 + rate / AaveV3CoreLib.SECONDS_IN_A_YEAR) ** AaveV3CoreLib.SECONDS_IN_A_YEAR - 1

    @staticmethod
    def get_amount(base_amount: Decimal, liquidity_index: Decimal) -> Decimal:
        return Decimal(base_amount) * Decimal(liquidity_index)

    @staticmethod
    def get_base_amount(amount: Decimal, liquidity_index: Decimal) -> Decimal:
        return amount / liquidity_index

    @staticmethod
    def get_max_borrow_value(
        collaterals: Dict[SupplyKey, Decimal],
        borrows: Dict[BorrowKey, Decimal],
        risk_parameters: pd.DataFrame,
    ) -> Decimal:
        ltv = AaveV3CoreLib.current_ltv(collaterals, risk_parameters)
        total_borrow = Decimal(sum(borrows.values()))
        total_collateral = Decimal(sum(collaterals.values()))

        return (total_collateral * ltv - total_borrow) * Decimal("0.99")  # because dapp web ui will multiply 0.99

    @staticmethod
    def get_min_withdraw_kept_amount(
        token: TokenInfo,
        supplies: Dict[SupplyKey, Decimal],
        borrows: Dict[BorrowKey, Decimal],
        risk_parameters: pd.DataFrame,
        price: Decimal,
    ) -> Decimal:
        supplies_liq_threshold = Decimal(0)
        for s, v in supplies.items():
            if s.token != token:
                supplies_liq_threshold += risk_parameters.loc[s.token.name].liqThereshold * v

        amount = (AaveV3CoreLib.HEALTH_FACTOR_LIQUIDATION_THRESHOLD * Decimal(sum(borrows.values())) - supplies_liq_threshold) / risk_parameters.loc[
            token.name
        ].liqThereshold

        return amount / price

    @staticmethod
    def health_factor(supplies: Dict[SupplyKey, Decimal], borrows: Dict[BorrowKey, Decimal], risk_parameters):
        # (all supplies * liqThereshold) / all borrows
        a = Decimal(sum([s * risk_parameters.loc[key.token.name].liqThereshold for key, s in supplies.items()]))
        b = Decimal(sum(borrows.values()))
        return AaveV3CoreLib.safe_div(a, b)

    @staticmethod
    def current_ltv(collaterals: Dict[SupplyKey, Decimal], risk_parameters):
        all_supplies = DECIMAL_0
        for t, s in collaterals.items():
            all_supplies += s * risk_parameters.loc[t.token.name].LTV

        amount = sum(collaterals.values())
        return AaveV3CoreLib.safe_div(all_supplies, Decimal(amount))

    @staticmethod
    def total_liquidation_threshold(supplies: Dict[SupplyKey, Decimal], risk_parameters):
        # (token_amount0 * LT0 + token_amount1 * LT1 + ...) / (token_amount0 + token_amount1)

        sum_amount = DECIMAL_0
        rate = DECIMAL_0
        for t, s in supplies.items():
            sum_amount += s
            rate += s * risk_parameters.loc[t.token.name].liqThereshold

        return AaveV3CoreLib.safe_div(rate, sum_amount)

    @staticmethod
    def safe_div(a: Decimal, b: Decimal) -> Decimal:
        return a / b if b != 0 else Decimal("inf")

    @staticmethod
    def safe_div_zero(a: Decimal, b: Decimal) -> Decimal:
        return a / b if b != 0 else Decimal(0)

    @staticmethod
    def get_apy(amounts: Dict[ActionKey, Decimal], rate_dict: Dict[TokenInfo, Decimal]):
        a = Decimal(sum([amounts[key] * AaveV3CoreLib.rate_to_apy(rate_dict[key.token]) for key, amount in amounts.items()]))
        b = Decimal(sum(amounts.values()))
        return AaveV3CoreLib.safe_div_zero(a, b)  # if total amount is 0, apy should be 0
