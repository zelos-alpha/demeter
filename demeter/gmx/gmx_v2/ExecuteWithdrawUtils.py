from .MarketUtils import MarketUtils
from .SwapPricingUtils import SwapPriceUtils, SwapPricingType
from ._typing import PoolConfig, GmxV2PoolStatus, LPResult
from .utils import PricingUtils


class ExecuteWithdrawUtils:

    @staticmethod
    def getOutputAmount(pool_config: PoolConfig, pool_status: GmxV2PoolStatus, marketTokenAmount: float):
        longAmount, shortAmount = MarketUtils.getTokenAmountsFromGM(pool_status, marketTokenAmount)
        longFees = SwapPriceUtils.getSwapFees(pool_config, longAmount, False, SwapPricingType.Withdrawal)
        shortFees = SwapPriceUtils.getSwapFees(pool_config, shortAmount, False, SwapPricingType.Withdrawal)

        long_amount_decimal, long_usd = MarketUtils.get_values(
            longFees.amountAfterFees, pool_status.longPrice, pool_config.longDecimal
        )
        short_amount_decimal, short_usd = MarketUtils.get_values(
            shortFees.amountAfterFees, pool_status.shortPrice, pool_config.shortDecimal
        )

        long_fee_decimal, long_fee_usd = MarketUtils.get_values(
            longFees.totalFee, pool_status.longPrice, pool_config.longDecimal
        )
        short_fee_decimal, short_fee_usd = MarketUtils.get_values(
            shortFees.totalFee, pool_status.shortPrice, pool_config.shortDecimal
        )

        result = LPResult(
            long_amount=long_amount_decimal,
            short_amount=short_amount_decimal,
            total_usd=long_usd + short_usd,
            gm_amount=marketTokenAmount,
            gm_usd=marketTokenAmount * PricingUtils.get_gm_price(pool_status.poolValue, pool_status.marketTokensSupply),
            long_fee=long_fee_decimal,
            short_fee=short_fee_decimal,
            fee_usd=long_fee_usd + short_fee_usd,
            price_impact_usd=0,
        )
        return result
