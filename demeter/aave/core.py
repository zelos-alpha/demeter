from _decimal import Decimal


class AaveV3CoreLib(object):
    pass

    SECONDS_IN_A_YEAR = 31536000

    @staticmethod
    def rate_to_apy(rate: Decimal) -> Decimal:
        return (1 + rate / AaveV3CoreLib.SECONDS_IN_A_YEAR) ** AaveV3CoreLib.SECONDS_IN_A_YEAR - 1

    @staticmethod
    def net_value_current(
        net_value_in_pool: Decimal,
        current_liquidity_rate: Decimal,
    ) -> Decimal:
        return net_value_in_pool * current_liquidity_rate

    @staticmethod
    def net_value_in_pool(amount: Decimal, pool_initial_liquidity_rate: Decimal) -> Decimal:
        return amount / pool_initial_liquidity_rate

    @staticmethod
    def health_factor():
        pass
