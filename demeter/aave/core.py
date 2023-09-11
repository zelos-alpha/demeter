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
    def net_value_in_pool(amount: Decimal, pool_liquidity_rate: Decimal) -> Decimal:
        return amount / pool_liquidity_rate

    @staticmethod
    def health_factor():
        # (所有token 抵押 * 清算门限)/总借款

        pass

    @staticmethod
    def user_current_ltv():
        # 借款总额/抵押总额
        # 和总tvl和清算门限比较
        pass

    @staticmethod
    def total_apy():
        # (token_amount0 * apy0 + token_amount1 * apy1 + ...) / (token_amount0 + token_amount1)
        pass

    @staticmethod
    def total_ltv():
        # (token_amount0 * ltv0 + token_amount1 * ltv1 + ...) / (token_amount0 + token_amount1)
        # ltv大于这个就不能借款
        pass

    @staticmethod
    def total_liquidation_threshold():
        # (token_amount0 * LT0 + token_amount1 * LT1 + ...) / (token_amount0 + token_amount1)
        # ltv大于这个被清算
        pass