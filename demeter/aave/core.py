from _decimal import Decimal
from typing import Dict

from demeter import DECIMAL_0, TokenInfo


class AaveV3CoreLib(object):
    pass

    SECONDS_IN_A_YEAR = 31536000

    @staticmethod
    def rate_to_apy(rate: Decimal) -> Decimal:
        return (1 + rate / AaveV3CoreLib.SECONDS_IN_A_YEAR) ** AaveV3CoreLib.SECONDS_IN_A_YEAR - 1

    @staticmethod
    def get_current_amount(net_value_in_pool: Decimal, current_liquidity_rate: Decimal) -> Decimal:
        return Decimal(net_value_in_pool) * Decimal(current_liquidity_rate)

    @staticmethod
    def get_base_amount(amount: Decimal, pool_liquidity_rate: Decimal) -> Decimal:
        return amount / pool_liquidity_rate

    @staticmethod
    def health_factor(supplies: Dict[TokenInfo, Decimal], borrows: Dict[TokenInfo, Decimal], risk_parameters):
        # (all supplies * liqThereshold) / all borrows
        a = sum([s * risk_parameters.loc[token_info.name].liqThereshold for token_info, s in supplies.items()])
        b = sum(borrows.values())
        return AaveV3CoreLib.safe_div(a, b)

    @staticmethod
    def total_apy():
        # (token_amount0 * apy0 + token_amount1 * apy1 + ...) / (token_amount0 + token_amount1)
        pass

    @staticmethod
    def current_ltv(supplies: Dict[TokenInfo, Decimal], borrows: Dict[TokenInfo, Decimal], risk_parameters):
        # (token_amount0 * ltv0 + token_amount1 * ltv1 + ...) / (token_amount0 + token_amount1)
        all_borrows = DECIMAL_0
        for t, b in borrows.items():
            all_borrows += b * risk_parameters.loc[t.name].LTV
        all_supplies = DECIMAL_0
        for t, s in supplies.items():
            all_supplies += s * risk_parameters.loc[t.name].LTV
        AaveV3CoreLib.safe_div(all_borrows, all_supplies)

    @staticmethod
    def total_liquidation_threshold(supplies: Dict[TokenInfo, Decimal], risk_parameters):
        # (token_amount0 * LT0 + token_amount1 * LT1 + ...) / (token_amount0 + token_amount1)

        sum_amount = DECIMAL_0
        rate = DECIMAL_0
        for t,s in supplies.items():
            sum_amount += s
            rate += s * risk_parameters.loc[t.name].liqThereshold

        return AaveV3CoreLib.safe_div(rate, sum_amount)

    @staticmethod
    def safe_div(a: Decimal, b: Decimal) -> Decimal:
        if b == 0:
            return Decimal("Infinity")
        else:
            return a / b

    @staticmethod
    def get_apy(amounts: Dict[TokenInfo, Decimal], rate_dict: Dict[TokenInfo, Decimal]):
        a = sum([amounts[token] * AaveV3CoreLib.rate_to_apy(rate_dict[token]) for token, amount in amounts.items()])
        b = sum(amounts.values())
        return AaveV3CoreLib.safe_div(a, b)
