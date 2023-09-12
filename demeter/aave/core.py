from _decimal import Decimal
from typing import Dict

from demeter import DECIMAL_0, TokenInfo
from demeter.aave._typing import Supply, Borrow


class AaveV3CoreLib(object):
    pass

    SECONDS_IN_A_YEAR = 31536000

    @staticmethod
    def rate_to_apy(rate: Decimal) -> Decimal:
        return (1 + rate / AaveV3CoreLib.SECONDS_IN_A_YEAR) ** AaveV3CoreLib.SECONDS_IN_A_YEAR - 1

    @staticmethod
    def net_value_current(net_value_in_pool: Decimal, current_liquidity_rate: Decimal) -> Decimal:
        return net_value_in_pool * current_liquidity_rate

    @staticmethod
    def net_value_in_pool(amount: Decimal, pool_liquidity_rate: Decimal) -> Decimal:
        return amount / pool_liquidity_rate

    @staticmethod
    def health_factor(total_supplies: Dict[TokenInfo, Decimal], total_borrows: Dict[TokenInfo, Decimal], risk_parameters):
        # (all supplies * liqThereshold) / all borrows
        a = sum([s * risk_parameters[token_info].liqThereshold for token_info, s in total_supplies.items()])
        b = sum(total_borrows.values())
        return AaveV3CoreLib.safe_div(a, b)

    @staticmethod
    def total_apy():
        # (token_amount0 * apy0 + token_amount1 * apy1 + ...) / (token_amount0 + token_amount1)
        pass

    @staticmethod
    def current_ltv(total_supplies: Dict[TokenInfo, Decimal], total_borrows: Dict[TokenInfo, Decimal], risk_parameters):
        # (token_amount0 * ltv0 + token_amount1 * ltv1 + ...) / (token_amount0 + token_amount1)
        all_borrows = DECIMAL_0
        for t, b in total_borrows.items():
            all_borrows += b * risk_parameters[t].LTV
        all_supplies = DECIMAL_0
        for t, s in total_supplies.items():
            all_supplies += s * risk_parameters[t].LTV
        AaveV3CoreLib.safe_div(all_borrows, all_supplies)

    @staticmethod
    def total_liquidation_threshold(total_supplies: Dict[TokenInfo, Decimal], risk_parameters):
        # (token_amount0 * LT0 + token_amount1 * LT1 + ...) / (token_amount0 + token_amount1)

        sum_amount = DECIMAL_0
        rate = DECIMAL_0
        for s in total_supplies.values():
            sum_amount += s
            rate += s * risk_parameters[s.token.name].liqThereshold

        return AaveV3CoreLib.safe_div(rate, sum_amount)

    @staticmethod
    def safe_div(a: Decimal, b: Decimal) -> Decimal:
        if b == 0:
            return Decimal("Infinity")
        else:
            return a / b

    @staticmethod
    def get_apy(amounts: Dict[TokenInfo, Decimal], rate_dict: Dict[TokenInfo, Decimal]):
        a = sum([amounts * AaveV3CoreLib.rate_to_apy(rate_dict[token]) for token, amount in amounts])
        b = sum(amounts.values())
        return AaveV3CoreLib.safe_div(a, b)
