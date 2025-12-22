from .._typing import PoolConfig, GmxV2PoolStatus, LPResult, PoolData
from ..market.MarketUtils import MarketUtils
from ..pricing.SwapPricingUtils import SwapPriceUtils, SwapPricingType
from ..utils import PricingUtils


class ExecuteWithdrawUtils:

    @staticmethod
    def getOutputAmount(marketTokenAmount: float, pool_data: PoolData):
        longAmount, shortAmount = MarketUtils.getTokenAmountsFromGM(pool_data.status, marketTokenAmount)
        longFees = SwapPriceUtils.getSwapFees(pool_data.config, longAmount, False, SwapPricingType.Withdrawal)
        shortFees = SwapPriceUtils.getSwapFees(pool_data.config, shortAmount, False, SwapPricingType.Withdrawal)

        long_amount_decimal, long_usd = MarketUtils.get_values(longFees.amountAfterFees, pool_data.status.longPrice)
        short_amount_decimal, short_usd = MarketUtils.get_values(shortFees.amountAfterFees, pool_data.status.shortPrice)

        long_fee_decimal, long_fee_usd = MarketUtils.get_values(longFees.totalFee, pool_data.status.longPrice)
        short_fee_decimal, short_fee_usd = MarketUtils.get_values(shortFees.totalFee, pool_data.status.shortPrice)

        gm_price = PricingUtils.get_gm_price(pool_data.status.poolValue, pool_data.status.marketTokensSupply)
        result = LPResult(
            long_amount=long_amount_decimal,
            short_amount=short_amount_decimal,
            total_usd=long_usd + short_usd,
            gm_amount=marketTokenAmount,
            gm_usd=marketTokenAmount * gm_price,
            long_fee=long_fee_decimal,
            short_fee=short_fee_decimal,
            fee_usd=long_fee_usd + short_fee_usd,
            price_impact_usd=0,
        )
        return result
