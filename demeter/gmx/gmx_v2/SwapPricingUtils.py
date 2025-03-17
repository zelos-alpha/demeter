import enum
from dataclasses import dataclass

from ._typing import PoolConfig, PoolStatus
from .utils import Calc, PricingUtils, Precision
from .MarketUtils import MarketUtils

class SwapPricingType(enum.Enum):
    Swap = 1
    Shift = 2
    Atomic = 3
    Deposit = 4
    Withdrawal = 5


@dataclass
class GetPriceImpactUsdParams:
    """
    @dev GetPriceImpactUsdParams struct used in getPriceImpactUsd to
    avoid stack too deep errors
    :param pool_config:
    :param priceForTokenA: the price for tokenA
    :param priceForTokenB: the price for tokenB
    :param usdDeltaForTokenA: the USD change in amount of tokenA
    :param usdDeltaForTokenB: the USD change in amount of tokenB
    """

    pool_config: PoolConfig
    priceForTokenA: float
    priceForTokenB: float
    usdDeltaForTokenA: float
    usdDeltaForTokenB: float
    includeVirtualInventoryImpact: bool
    tokenA_is_long_token: bool


# @dev PoolParams struct to contain pool values


# @param poolUsdForTokenA the USD value of tokenA in the pool
# @param poolUsdForTokenB the USD value of tokenB in the pool
# @param nextPoolUsdForTokenA the next USD value of tokenA in the pool
# @param nextPoolUsdForTokenB the next USD value of tokenB in the pool
@dataclass
class PoolParams:
    poolUsdForTokenA: float
    poolUsdForTokenB: float
    nextPoolUsdForTokenA: float
    nextPoolUsdForTokenB: float


# @dev SwapFees struct to contain swap fee values
# @param feeReceiverAmount the fee amount for the fee receiver
# @param feeAmountForPool the fee amount for the pool
# @param amountAfterFees the output amount after fees


@dataclass
class SwapFees:
    amountAfterFees: float
    totalFee: float


@dataclass
class Amounts:
    long: float
    short: float


class SwapPriceUtils:
    @staticmethod
    def getPriceImpactUsd(params: GetPriceImpactUsdParams, pool_status: PoolStatus) -> float:
        """
        @dev get the price impact in USD

        note that there will be some difference between the pool amounts used for
        calculating the price impact and fees vs the actual pool amounts after the
        swap is done, since the pool amounts will be increased / decreased by an amount
        after factoring in the calculated price impact and fees

        since the calculations are based on the real-time prices values of the tokens
        if a token price increases, the pool will incentivise swapping out more of that token
        this is useful if prices are ranging, if prices are strongly directional, the pool may
        be selling tokens as the token price increases

        """

        pool_params: PoolParams = SwapPriceUtils.getNextPoolAmountsUsd(
            params, Amounts(pool_status.longAmount, pool_status.shortAmount)
        )

        priceImpactUsd: float = SwapPriceUtils._getPriceImpactUsd(params.pool_config, pool_params)

        # the virtual price impact calculation is skipped if the price impact
        # is positive since the action is helping to balance the pool
        #
        # in case two virtual pools are unbalanced in a different direction
        # e.g. pool0 has more WNT than USDC while pool1 has less WNT
        # than USDT
        # not skipping the virtual price impact calculation would lead to
        # a negative price impact for any trade on either pools and would
        # disincentivise the balancing of pools
        if priceImpactUsd >= 0:
            return priceImpactUsd

        if not params.includeVirtualInventoryImpact:
            return priceImpactUsd

        # note that the virtual pool for the long token / short token may be different across pools
        # e.g. ETH/USDC, ETH/USDT would have USDC and USDT as the short tokens
        # the short token amount is multiplied by the price of the token in the current pool, e.g. if the swap
        # is for the ETH/USDC pool, the combined USDC and USDT short token amounts is multiplied by the price of
        # USDC to calculate the price impact, this should be reasonable most of the time unless there is a
        # large depeg of one of the tokens, in which case it may be necessary to remove that market from being a virtual
        # market, removal of virtual markets may lead to incorrect virtual token accounting, the feature to correct for
        # this can be added if needed
        virtualPoolAmountForLongToken, virtualPoolAmountForShortToken = (
            pool_status.virtualSwapInventoryLong,
            pool_status.virtualSwapInventoryShort,
        )

        if virtualPoolAmountForLongToken is None or virtualPoolAmountForShortToken is None:
            return priceImpactUsd

        if params.tokenA_is_long_token:
            virtualPoolAmountForTokenA = virtualPoolAmountForLongToken
            virtualPoolAmountForTokenB = virtualPoolAmountForShortToken
        else:
            virtualPoolAmountForTokenA = virtualPoolAmountForShortToken
            virtualPoolAmountForTokenB = virtualPoolAmountForLongToken

        poolParamsForVirtualInventory: PoolParams = SwapPriceUtils.getNextPoolAmountsParams(
            params, virtualPoolAmountForTokenA, virtualPoolAmountForTokenB
        )

        priceImpactUsdForVirtualInventory: float = SwapPriceUtils._getPriceImpactUsd(
            params.pool_config, poolParamsForVirtualInventory
        )

        return (
            priceImpactUsdForVirtualInventory if priceImpactUsdForVirtualInventory < priceImpactUsd else priceImpactUsd
        )

    @staticmethod
    def _getPriceImpactUsd(pool_config: PoolConfig, pool_params: PoolParams) -> float:
        """
        get the price impact in USD
        :param pool_config: pool config
        :param pool_params: PoolParams
        :return: the price impact in USD
        """
        initialDiffUsd: float = Calc.diff(pool_params.poolUsdForTokenA, pool_params.poolUsdForTokenB)
        nextDiffUsd: float = Calc.diff(pool_params.nextPoolUsdForTokenA, pool_params.nextPoolUsdForTokenB)

        # check whether an improvement in balance comes from causing the balance to switch sides
        # for example, if there is $2000 of ETH and $1000 of USDC in the pool
        # adding $1999 USDC into the pool will reduce absolute balance from $1000 to $999, but it does not
        # help rebalance the pool much, the isSameSideRebalance value helps avoid gaming using this case
        isSameSideRebalance: bool = (pool_params.poolUsdForTokenA <= pool_params.poolUsdForTokenB) == (
            pool_params.nextPoolUsdForTokenA <= pool_params.nextPoolUsdForTokenB
        )
        impactExponentFactor: float = pool_config.swapImpactExponentFactor

        if isSameSideRebalance:
            hasPositiveImpact: bool = nextDiffUsd < initialDiffUsd
            impactFactor: int = MarketUtils.getAdjustedSwapImpactFactor(pool_config, hasPositiveImpact)

            return PricingUtils.getPriceImpactUsdForSameSideRebalance(
                initialDiffUsd, nextDiffUsd, impactFactor, impactExponentFactor
            )
        else:
            positiveImpactFactor, negativeImpactFactor = MarketUtils.getAdjustedSwapImpactFactors(pool_config)

            return PricingUtils.getPriceImpactUsdForCrossoverRebalance(
                initialDiffUsd,
                nextDiffUsd,
                positiveImpactFactor,
                negativeImpactFactor,
                impactExponentFactor,
            )

    @staticmethod
    def getNextPoolAmountsUsd(params: GetPriceImpactUsdParams, amounts: Amounts) -> PoolParams:
        """
        get the next pool amounts in USD
        :return: PoolParams
        """
        poolAmountForTokenA, poolAmountForTokenB = (
            (amounts.long, amounts.short) if params.tokenA_is_long_token else (amounts.short, amounts.long)
        )
        return SwapPriceUtils.getNextPoolAmountsParams(params, poolAmountForTokenA, poolAmountForTokenB)
        # poolAmountForTokenA, poolAmountForTokenB = (
        #     (amounts.long, amounts.short)
        #     if params.tokenA_is_long_token
        #     else (amounts.short, amounts.long)
        # )
        # poolUsdForTokenA: int = poolAmountForTokenA * params.priceForTokenA
        # poolUsdForTokenB: int = poolAmountForTokenB * params.priceForTokenB
        # return PoolParams(
        #     poolUsdForTokenA,
        #     poolUsdForTokenB,
        #     poolUsdForTokenA + params.usdDeltaForTokenA,
        #     poolUsdForTokenB + params.usdDeltaForTokenB,
        # )

    @staticmethod
    def getNextPoolAmountsParams(
        params: GetPriceImpactUsdParams,
        poolAmountForTokenA: float,
        poolAmountForTokenB: float,
    ) -> PoolParams:
        poolUsdForTokenA: float = poolAmountForTokenA * params.priceForTokenA
        poolUsdForTokenB: float = poolAmountForTokenB * params.priceForTokenB

        if params.usdDeltaForTokenA < 0 and (-params.usdDeltaForTokenA) > poolUsdForTokenA:
            raise RuntimeError(f"UsdDeltaExceedsPoolValue, {params.usdDeltaForTokenA}, {poolUsdForTokenA}")

        if params.usdDeltaForTokenB < 0 and (-params.usdDeltaForTokenB) > poolUsdForTokenB:
            raise RuntimeError(f"UsdDeltaExceedsPoolValue, {params.usdDeltaForTokenB}, {poolUsdForTokenB}")

        nextPoolUsdForTokenA: float = Calc.sumReturnUint256(poolUsdForTokenA, params.usdDeltaForTokenA)
        nextPoolUsdForTokenB: float = Calc.sumReturnUint256(poolUsdForTokenB, params.usdDeltaForTokenB)

        poolParams: PoolParams = PoolParams(
            poolUsdForTokenA,
            poolUsdForTokenB,
            nextPoolUsdForTokenA,
            nextPoolUsdForTokenB,
        )

        return poolParams

    @staticmethod
    def getSwapFees(
        pool_config: PoolConfig,
        amount: float,
        forPositiveImpact: bool,
        swapPricingType: SwapPricingType,
    ) -> SwapFees:
        fees = SwapFees(0, 0)

        # note that since it is possible to incur both positive and negative price impact values
        # and the negative price impact factor may be larger than the positive impact factor
        # it is possible for the balance to be improved overall but for the price impact to still be negative
        # in this case the fee factor for the negative price impact would be charged
        # a user could split the order into two, to incur a smaller fee, reducing the fee through this should not be a large issue
        feeFactor = 0
        if swapPricingType == SwapPricingType.Swap:
            feeFactor = 0
        elif swapPricingType == SwapPricingType.Shift:
            # empty branch as feeFactor is already zero
            feeFactor = 0
        elif swapPricingType == SwapPricingType.Atomic:
            feeFactor = 0
        elif swapPricingType == SwapPricingType.Deposit:
            feeFactor = (
                pool_config.depositFeeFactorForPositiveImpact
                if forPositiveImpact
                else pool_config.depositFeeFactorForNegativeImpact
            )
        elif swapPricingType == SwapPricingType.Withdrawal:
            feeFactor = (
                pool_config.withdrawFeeFactorForPositiveImpact
                if forPositiveImpact
                else pool_config.withdrawFeeFactorForNegativeImpact
            )

        # swapFeeReceiverFactor = 370000000000000000000000000000
        #
        feeAmount = Precision.applyFactor(amount, feeFactor)
        #
        # fees.feeReceiverAmount = Precision.applyFactor(feeAmount, swapFeeReceiverFactor)
        # fees.feeAmountForPool = feeAmount - fees.feeReceiverAmount

        fees.amountAfterFees = amount - feeAmount
        fees.totalFee = feeAmount
        return fees
