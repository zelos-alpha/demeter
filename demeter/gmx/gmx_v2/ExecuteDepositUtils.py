from typing import Tuple

from .MarketUtils import MarketUtils
from .SwapPricingUtils import SwapPriceUtils, SwapPricingType, GetPriceImpactUsdParams, SwapFees
from ._typing import PoolConfig, GmxV2PoolStatus, LPResult
from .utils import PricingUtils


class ExecuteDepositUtils:
    @staticmethod
    def get_mint_amount(
        pool_config: PoolConfig, pool_status: GmxV2PoolStatus, long_amount: float, short_amount: float
    ) -> LPResult:
        long_value = long_amount * pool_status.longPrice
        short_value = short_amount * pool_status.shortPrice

        # long_value_in_base = Decimal(
        #     long_amount / 10**pool_config.longDecimal
        # ) * PricingUtils.get_price_in_base_unit(pool_status.longPrice, pool_config.longDecimal)
        #
        # short_value_in_base = Decimal(
        #     short_amount / 10**pool_config.shortDecimal
        # ) * PricingUtils.get_price_in_base_unit(pool_status.shortPrice, pool_config.shortDecimal)

        priceImpactUsd = SwapPriceUtils.getPriceImpactUsd(
            GetPriceImpactUsdParams(
                pool_config,
                pool_status.longPrice,
                pool_status.shortPrice,
                long_value,
                short_value,
                True,
                True,
            ),
            pool_status,
        )
        # =========================================================
        gm_amount = long_fee_amount = short_fee_amount = 0
        total_fee_value = 0
        if long_amount > 0:
            amount, long_fee = ExecuteDepositUtils.calc_token_amount(
                pool_config,
                pool_status,
                pool_status.longPrice,
                pool_status.shortPrice,
                long_amount,
                priceImpactUsd * long_value / (long_value + short_value),
            )
            gm_amount += amount
            total_fee_value += long_fee.totalFee * pool_status.longPrice
            long_fee_amount = long_fee.totalFee
        if short_amount > 0:
            amount, short_fee = ExecuteDepositUtils.calc_token_amount(
                pool_config,
                pool_status,
                pool_status.shortPrice,
                pool_status.longPrice,
                short_amount,
                priceImpactUsd * short_value / (long_value + short_value),
            )
            gm_amount += amount
            total_fee_value += short_fee.totalFee * pool_status.shortPrice
            short_fee_amount = short_fee.totalFee

        result = LPResult(
            long_amount=long_amount,
            short_amount=short_amount,
            total_usd=long_value + short_value,
            gm_amount=gm_amount,
            long_fee=long_fee_amount,
            short_fee=short_fee_amount,
            gm_usd=gm_amount * PricingUtils.get_gm_price(pool_status.poolValue, pool_status.marketTokensSupply),
            fee_usd=total_fee_value,
            price_impact_usd=priceImpactUsd,
        )
        return result

    @staticmethod
    def calc_token_amount(
        pool_config: PoolConfig,
        pool_status: GmxV2PoolStatus,
        tokenInPrice: float,
        tokenOutPrice: float,
        amount: float,
        priceImpactUsd: float,
    ) -> Tuple[float, SwapFees]:
        fees: SwapFees = SwapPriceUtils.getSwapFees(
            pool_config,
            amount,
            priceImpactUsd > 0,
            SwapPricingType.Deposit,
        )
        mintAmount = 0

        if priceImpactUsd > 0:
            positiveImpactAmount, _ = MarketUtils.getSwapImpactAmountWithCap(
                tokenOutPrice, priceImpactUsd, pool_status.impactPoolAmount
            )
            mintAmount += MarketUtils.usdToMarketTokenAmount(
                positiveImpactAmount * tokenOutPrice, pool_status.poolValue, pool_status.marketTokensSupply
            )
        if priceImpactUsd < 0:
            # when there is a negative price impact factor,
            # less of the deposit amount is used to mint market tokens
            # for example, if 10 ETH is deposited and there is a negative price impact
            # only 9.995 ETH may be used to mint market tokens
            # the remaining 0.005 ETH will be stored in the swap impact pool
            negativeImpactAmount, _ = MarketUtils.getSwapImpactAmountWithCap(
                tokenInPrice, priceImpactUsd, pool_status.impactPoolAmount
            )
            fees.amountAfterFees -= -negativeImpactAmount
        mintAmount += MarketUtils.usdToMarketTokenAmount(
            fees.amountAfterFees * tokenInPrice, pool_status.poolValue, pool_status.marketTokensSupply
        )
        return mintAmount, fees
