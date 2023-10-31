from _decimal import Decimal
from typing import Dict

from demeter import DECIMAL_0, TokenInfo
from demeter.aave._typing import SupplyKey, ActionKey, BorrowKey
import pandas as pd


class AaveV3CoreLib(object):
    """
    | The core calculation library for aave v3 market
    | Note: All functions are static
    """

    SECONDS_IN_A_YEAR = 31536000
    """how many seconds in a year"""

    HEALTH_FACTOR_LIQUIDATION_THRESHOLD = Decimal("1")
    """
    if CLOSE_FACTOR_HF_THRESHOLD < health factor <  DEFAULT_LIQUIDATION_CLOSE_FACTOR
    only DEFAULT_LIQUIDATION_CLOSE_FACTOR(50%) will be liquidated,
    otherwise HEALTH_FACTOR_LIQUIDATION_THRESHOLD(100%) will be liquidated
    """

    DEFAULT_LIQUIDATION_CLOSE_FACTOR = Decimal("0.5")

    MAX_LIQUIDATION_CLOSE_FACTOR = Decimal("1")

    CLOSE_FACTOR_HF_THRESHOLD = Decimal("0.95")


    @staticmethod
    def rate_to_apy(rate: Decimal) -> Decimal:
        """
        Convert supply/borrow interest rate(get from ReserveDataUpdated event) to apy(annual interest rate)

        :param rate: interest rate(time unit is second)
        :type rate: Decimal
        :return: apy (time unit is year)
        :rtype: Decimal
        """
        return (1 + rate / AaveV3CoreLib.SECONDS_IN_A_YEAR) ** AaveV3CoreLib.SECONDS_IN_A_YEAR - 1

    @staticmethod
    def get_amount(base_amount: Decimal, liquidity_index: Decimal) -> Decimal:
        """
        | Get amount from base amount.
        | Note: base amount is used in contract. Actual user token balance is base_amount * liquidity_index

        :param base_amount: base token amount
        :type base_amount: Decimal
        :param liquidity_index: token liquidity_index at this moment.
        :type liquidity_index: Decimal
        :return: Actually token amount.
        :rtype: Decimal
        """
        return Decimal(base_amount) * Decimal(liquidity_index)

    @staticmethod
    def get_base_amount(amount: Decimal, liquidity_index: Decimal) -> Decimal:
        """
        | Get base amount from amount
        | Note: base amount is used in contract. Actual user token balance is base_amount * liquidity_index

        :param amount: token amount
        :type amount: Decimal
        :param liquidity_index: token liquidity_index at this moment.
        :type liquidity_index: Decimal
        :return: token base amount.
        :rtype: Decimal
        """
        return amount / liquidity_index

    @staticmethod
    def get_max_borrow_value(
        collaterals: Dict[SupplyKey, Decimal],
        borrows: Dict[BorrowKey, Decimal],
        risk_parameters: pd.DataFrame,
    ) -> Decimal:
        """
        | Calculate the max amount to borrow.
        | Note: As aave web app will multiply 0.99 to result, we followed this practice

        :param collaterals: All collaterals. note: unit of dict value(Decimal) is usd
        :type collaterals: Dict[SupplyKey, Decimal]
        :param borrows: All borrows. note: unit of dict value(Decimal) is usd
        :type borrows: Dict[BorrowKey, Decimal]
        :param risk_parameters: risk_parameters of a chain.
        :type risk_parameters: pd.DataFrame
        :return: borrow amount (in usd)
        :rtype: Decimal
        """
        ltv = AaveV3CoreLib.current_ltv(collaterals, risk_parameters)
        total_borrow = Decimal(sum(borrows.values()))
        total_collateral = Decimal(sum(collaterals.values()))

        return (total_collateral * ltv - total_borrow) * Decimal("0.99")  # because dapp web ui will multiply 0.99

    @staticmethod
    def get_min_withdraw_kept_amount(
        token: TokenInfo,
        collaterals: Dict[SupplyKey, Decimal],
        borrows: Dict[BorrowKey, Decimal],
        risk_parameters: pd.DataFrame,
        price: Decimal,
    ) -> Decimal:
        """
        | Get min collateral token amount to keep health factor above 1

        :param token: which token to calculate
        :type token: TokenInfo
        :param collaterals: collateral values of each token, note: dict value(Decimal) is token value in usd
        :type collaterals: Dict[SupplyKey, Decimal]
        :param borrows: borrow values of each token, note: dict value(Decimal) is token value in usd
        :type borrows: Dict[BorrowKey, Decimal]
        :param risk_parameters: token risk parameters of this chain
        :type risk_parameters: DataFrame
        :param price: current token price
        :type price: Decimal
        :return: min token amount should kept to prevent liquidation
        :rtype: Decimal
        """
        # if token is not collateral token, doesn't need to keep any
        if token not in [k.token for k in collaterals.keys()]:
            return DECIMAL_0
        supplies_liq_threshold = Decimal(0)
        for s, v in collaterals.items():
            if s.token != token:
                supplies_liq_threshold += risk_parameters.loc[s.token.name].liqThereshold * v

        amount = (AaveV3CoreLib.HEALTH_FACTOR_LIQUIDATION_THRESHOLD * Decimal(sum(borrows.values())) - supplies_liq_threshold) / risk_parameters.loc[
            token.name
        ].liqThereshold

        return amount / price

    @staticmethod
    def health_factor(collaterals: Dict[SupplyKey, Decimal], borrows: Dict[BorrowKey, Decimal], risk_parameters) -> Decimal:
        """
        Get current health factor in decimal, e.g.0.8

        :param collaterals: collateral values of each token, note: dict value(Decimal) is token value in usd
        :type collaterals: Dict[SupplyKey, Decimal]
        :param borrows: borrow values of each token, note: dict value(Decimal) is token value in usd
        :type borrows: Dict[BorrowKey, Decimal]
        :param risk_parameters: token risk parameters of this chain
        :type risk_parameters: DataFrame
        :return: health factor
        :rtype: Decimal
        """
        # (all supplies * liqThereshold) / all borrows
        a = Decimal(sum([s * risk_parameters.loc[key.token.name].liqThereshold for key, s in collaterals.items()]))
        b = Decimal(sum(borrows.values()))
        return AaveV3CoreLib.safe_div(a, b)

    @staticmethod
    def current_ltv(collaterals: Dict[SupplyKey, Decimal], risk_parameters) -> Decimal:
        """
        Get max ltv of this user, calculated by token ltv and positions

        :param collaterals: collateral values, note: dict value(Decimal) is token value in usd
        :type collaterals: Dict[SupplyKey, Decimal]
        :param risk_parameters: token risk parameters of this chain
        :type risk_parameters: DataFrame
        :return: max ltv
        :rtype: Decimal
        """
        all_supplies = DECIMAL_0
        for t, s in collaterals.items():
            all_supplies += s * risk_parameters.loc[t.token.name].LTV

        amount = sum(collaterals.values())
        return AaveV3CoreLib.safe_div(all_supplies, Decimal(amount))

    @staticmethod
    def total_liquidation_threshold(collaterals: Dict[SupplyKey, Decimal], risk_parameters):
        """
        | Get total liquidation threshold of this user, value is in decimal, e.g.0.81, this value should be larger than ltv
        | value = (token_amount0 * LT0 + token_amount1 * LT1 + ...) / (token_amount0 + token_amount1)

        :param collaterals: collateral values of each token, note: dict value(Decimal) is token value in usd
        :type collaterals: Dict[SupplyKey, Decimal]
        :param risk_parameters: token risk parameters of this chain
        :type risk_parameters: DataFrame
        :return: total liquidation threshold
        :rtype: Decimal
        """
        sum_amount = DECIMAL_0
        rate = DECIMAL_0
        for t, s in collaterals.items():
            sum_amount += s
            rate += s * risk_parameters.loc[t.token.name].liqThereshold

        return AaveV3CoreLib.safe_div(rate, sum_amount)

    @staticmethod
    def safe_div(a: Decimal, b: Decimal) -> Decimal:
        """
        div two decimals, but will return inf if b==0
        """
        return a / b if b != 0 else Decimal("inf")

    @staticmethod
    def safe_rounding(a: Decimal, rounding: Decimal) -> Decimal:
        """
        Round decimal number, but when value is inf or nan, will not throw an exception
        """
        return a if a == Decimal("inf") or a == Decimal("nan") else a.quantize(rounding)

    @staticmethod
    def safe_div_zero(a: Decimal, b: Decimal) -> Decimal:
        """
        div two decimals, but will return 0 if b==0, only used to calculate apy
        """
        return a / b if b != 0 else Decimal(0)

    @staticmethod
    def get_apy(amounts: Dict[ActionKey, Decimal], rate_dict: Dict[TokenInfo, Decimal]) -> Decimal:
        """
        Calculate apy of all borrows or supplies

        :param amounts: supply or borrow values, note: dict value(Decimal) is token value in usd
        :type amounts: Dict[ActionKey, Decimal]
        :param rate_dict: apy of tokens
        :type rate_dict: Dict[TokenInfo, Decimal]
        :return: total apy
        :rtype: Decimal
        """
        if len(amounts) == 0:
            return DECIMAL_0
        a = Decimal(sum([amounts[key] * AaveV3CoreLib.rate_to_apy(rate_dict[key.token]) for key, amount in amounts.items()]))
        b = Decimal(sum(amounts.values()))
        return AaveV3CoreLib.safe_div_zero(a, b)  # if total amount is 0, apy should be 0
