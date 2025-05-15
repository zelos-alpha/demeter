from typing import Tuple

from ._typing import PoolConfig, GmxV2PoolStatus


class MarketUtils:
    @staticmethod
    def getAdjustedSwapImpactFactor(pool_config: PoolConfig, isPositive: bool) -> int:
        positiveImpactFactor, negativeImpactFactor = MarketUtils.getAdjustedSwapImpactFactors(pool_config)
        return positiveImpactFactor if isPositive else negativeImpactFactor

    @staticmethod
    def getAdjustedSwapImpactFactors(pool_config: PoolConfig) -> (int, int):
        positiveImpactFactor = pool_config.swapImpactFactorPositive
        negativeImpactFactor = pool_config.swapImpactFactorNegative

        # if the positive impact factor is more than the negative impact factor, positions could be opened
        # and closed immediately for a profit if the difference is sufficient to cover the position fees
        if positiveImpactFactor > negativeImpactFactor:
            positiveImpactFactor = negativeImpactFactor

        return positiveImpactFactor, negativeImpactFactor

    @staticmethod
    def getSwapImpactAmountWithCap(
        tokenPrice: float, priceImpactUsd: float, impactPoolAmount: float
    ) -> Tuple[float, float]:
        cappedDiffUsd: float = 0

        if priceImpactUsd > 0:
            # positive impact: minimize impactAmount, use tokenPrice.max
            # round positive impactAmount down, this will be deducted from the swap impact pool for the user
            impactAmount = priceImpactUsd / tokenPrice

            maxImpactAmount = impactPoolAmount
            if impactAmount > maxImpactAmount:
                cappedDiffUsd = (impactAmount - maxImpactAmount) * tokenPrice
                impactAmount = maxImpactAmount
        else:
            # negative impact: maximize impactAmount, use tokenPrice.min
            # round negative impactAmount up, this will be deducted from the user
            impactAmount = priceImpactUsd / tokenPrice

        return impactAmount, cappedDiffUsd

    @staticmethod
    def usdToMarketTokenAmount(_usd_value: float, _pool_value: float, _supply: float) -> float:
        return _supply * _usd_value / _pool_value

    @staticmethod
    def marketTokenAmountToUsd(marketTokenAmount: float, poolValue: float, supply: float) -> float:
        return poolValue * marketTokenAmount / supply

    @staticmethod
    def getTokenAmountsFromGM(
        pool_status: GmxV2PoolStatus,
        marketTokenAmount: float,
    ) -> Tuple[float, float]:
        """
        the max pnl factor for withdrawals should be the lower of the max pnl factor values
        which means that pnl would be capped to a smaller amount and the pool
        value would be higher even if there is a large pnl
        this should be okay since MarketUtils.validateMaxPnl is called after the withdrawal
        which ensures that the max pnl factor for withdrawals was not exceeded
        """

        poolValue: float = pool_status.poolValue
        marketTokensSupply: float = pool_status.marketTokensSupply

        longTokenPoolUsd = pool_status.longAmount * pool_status.longPrice
        shortTokenPoolUsd = pool_status.shortAmount * pool_status.shortPrice

        totalPoolUsd = longTokenPoolUsd + shortTokenPoolUsd

        marketTokensUsd = MarketUtils.marketTokenAmountToUsd(marketTokenAmount, poolValue, marketTokensSupply)

        longTokenOutputUsd: float = marketTokensUsd * longTokenPoolUsd / totalPoolUsd
        shortTokenOutputUsd: float = marketTokensUsd * shortTokenPoolUsd / totalPoolUsd

        return (
            longTokenOutputUsd / pool_status.longPrice,
            shortTokenOutputUsd / pool_status.shortPrice,
        )

    @staticmethod
    def get_values(amount: float, price: float, decimal: float) -> Tuple[float, float]:
        return amount, amount * price

