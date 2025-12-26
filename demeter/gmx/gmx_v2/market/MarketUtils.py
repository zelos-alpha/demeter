import dataclasses
from typing import Tuple

from demeter import TokenInfo, DemeterError
from .. import PoolData
from .._typing import GmxV2Pool
from .._typing import PoolConfig, GmxV2PoolStatus
from ..position.Position import Position


@dataclasses.dataclass
class MarketPrices:
    indexTokenPrice: float
    longTokenPrice: float
    shortTokenPrice: float


class MarketUtils:
    @staticmethod
    def getAdjustedSwapImpactFactor(pool_config: PoolConfig, isPositive: bool) -> float:
        positiveImpactFactor, negativeImpactFactor = MarketUtils.getAdjustedSwapImpactFactors(pool_config)
        return positiveImpactFactor if isPositive else negativeImpactFactor

    @staticmethod
    def getAdjustedSwapImpactFactors(pool_config: PoolConfig) -> tuple[float, float]:
        positiveImpactFactor = pool_config.swapImpactFactor_Positive
        negativeImpactFactor = pool_config.swapImpactFactor_Negative

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
    def get_values(amount: float, price: float) -> Tuple[float, float]:
        return amount, amount * price

    @staticmethod
    def getOppositeToken(inputToken: TokenInfo, market: GmxV2Pool) -> TokenInfo:
        if inputToken == market.long_token:
            return market.short_token
        elif inputToken == market.short_token:
            return market.long_token
        else:
            raise DemeterError("input token should be long or short")

    @staticmethod
    def applySwapImpactWithCap(
        tokenPrice: float, priceImpactUsd: float, impactPoolAmount: float
    ) -> Tuple[float, float]:
        impactAmount, cappedDiffUsd = MarketUtils.getSwapImpactAmountWithCap(
            tokenPrice, priceImpactUsd, impactPoolAmount
        )
        return impactAmount, cappedDiffUsd

    @staticmethod
    def getFundingAmount(
        latestFundingAmountPerSize: float, positionFundingAmountPerSize: float, positionSizeInUsd: float
    ) -> float:
        fundingDiffFactor = latestFundingAmountPerSize - positionFundingAmountPerSize
        # a user could avoid paying funding fees by continually updating the position
        # before the funding fee becomes large enough to be chargeable
        # to avoid this, funding fee amounts should be rounded up
        #
        # this could lead to large additional charges if the token has a low number of decimals
        # or if the token's value is very high, so care should be taken to inform users of this
        #
        # if the calculation is for the claimable amount, the amount should be rounded down instead

        # divide the result by Precision.FLOAT_PRECISION * Precision.FLOAT_PRECISION_SQRT as the fundingAmountPerSize values
        # are stored based on FLOAT_PRECISION_SQRT values
        fundingAmount = positionSizeInUsd * fundingDiffFactor
        return fundingAmount

    @staticmethod
    def getBorrowingFees(position: Position, pool_status: GmxV2PoolStatus):
        cumulativeBorrowingFactor = MarketUtils.getCumulativeBorrowingFactor(position.isLong, pool_status)
        diffFactor = cumulativeBorrowingFactor - position.borrowingFactor
        return position.sizeInUsd * diffFactor

    @staticmethod
    def getCumulativeBorrowingFactor(isLong: bool, pool_status: GmxV2PoolStatus):
        return pool_status.cumulativeBorrowingFactorLong if isLong else pool_status.cumulativeBorrowingFactorShort

    @staticmethod
    def capPositiveImpactUsdByMaxPositionImpact(
        priceImpactUsd: float,
        sizeDeltaUsd: float,
        pool_data: PoolData,
    ) -> float:
        if priceImpactUsd < 0:
            return priceImpactUsd

        maxPriceImpactFactor = MarketUtils.getMaxPositionImpactFactor(True, pool_data)
        maxPriceImpactUsdBasedOnMaxPriceImpactFactor = sizeDeltaUsd * maxPriceImpactFactor

        if priceImpactUsd > maxPriceImpactUsdBasedOnMaxPriceImpactFactor:
            priceImpactUsd = maxPriceImpactUsdBasedOnMaxPriceImpactFactor

        return priceImpactUsd

    @staticmethod
    def capPositiveImpactUsdByPositionImpactPool(
        prices: MarketPrices,
        priceImpactUsd: float,
        pool_data: PoolData,
    ) -> float:
        """
        Not implemented, because we don't have lentPositionImpactPoolAmount, and this function rarely used.
        """
        return priceImpactUsd


    @staticmethod
    def getMaxPositionImpactFactor(isPositive: bool, pool_data: PoolData) -> float:
        maxPositiveImpactFactor = pool_data.config.maxPositionImpactFactor_Positive
        maxNegativeImpactFactor = pool_data.config.maxPositiveImpactFactor_Negative
        if maxPositiveImpactFactor > maxNegativeImpactFactor:
            maxPositiveImpactFactor = maxNegativeImpactFactor
        return maxPositiveImpactFactor if isPositive else maxNegativeImpactFactor

    @staticmethod
    def getPoolAmount(market: GmxV2Pool, poolAmount: float):
        divisor = MarketUtils.getPoolDivisor(market.long_token, market.short_token)
        return poolAmount / divisor

    @staticmethod
    def getPoolDivisor(longToken: TokenInfo, shortToken: TokenInfo) -> int:
        return 2 if longToken == shortToken else 1

    @staticmethod
    def getPnl(indexTokenPrice: float, isLong: bool, pool_status: GmxV2PoolStatus):
        openInterest = pool_status.openInterestLong if isLong else pool_status.openInterestShort
        openInterestInTokens = pool_status.openInterestInTokensLong if isLong else pool_status.openInterestInTokensShort

        price = indexTokenPrice

        openInterestValue = openInterestInTokens * price
        pnl = openInterestValue - openInterest if isLong else openInterest - openInterestValue
        return pnl

    @staticmethod
    def getCappedPnl(isLong: bool, pnl: float, poolUsd: float, pool_config: PoolConfig):
        if pnl < 0:
            return pnl
        maxPnlFactor = pool_config.maxPnlFactor_ForTrader_Long if isLong else pool_config.maxPnlFactor_ForTrader_Short
        maxPnl = poolUsd * maxPnlFactor
        return maxPnl if pnl > maxPnl else pnl

    @staticmethod
    def getMinCollateralFactorForOpenInterest(isLong: bool, openInterestDelta: float, pool_data: PoolData) -> float:
        openInterest = pool_data.status.openInterestLong if isLong else pool_data.status.openInterestShort
        openInterest = openInterest + openInterestDelta
        multiplierFactor = (
            pool_data.config.minCollateralFactorForOpenInterestMultiplier_Long
            if isLong
            else pool_data.config.minCollateralFactorForOpenInterestMultiplier_Short
        )
        return openInterest * multiplierFactor

    @staticmethod
    def getAdjustedPositionImpactFactor(isPositive: bool, config: PoolConfig):
        positiveImpactFactor, negativeImpactFactor = MarketUtils.getAdjustedPositionImpactFactors(config)
        return positiveImpactFactor if isPositive else negativeImpactFactor

    @staticmethod
    def getAdjustedPositionImpactFactors(config: PoolConfig):
        positiveImpactFactor = config.positionImpactFactor_Positive
        negativeImpactFactor = config.positionImpactFactor_Negative
        if positiveImpactFactor > negativeImpactFactor:
            positiveImpactFactor = negativeImpactFactor
        return positiveImpactFactor, negativeImpactFactor

    @staticmethod
    def getAdjustedPositionImpactExponentFactor(isPositive: bool, config: PoolConfig):
        positiveExponentFactor, negativeExponentFactor = MarketUtils.getAdjustedPositionImpactExponentFactors(config)
        return positiveExponentFactor if isPositive else negativeExponentFactor

    @staticmethod
    def getAdjustedPositionImpactExponentFactors(config: PoolConfig):
        positiveExponentFactor = config.positionImpactExponentFactor_Positive
        negativeExponentFactor = config.positionImpactExponentFactor_Negative
        if positiveExponentFactor > negativeExponentFactor:
            positiveExponentFactor = negativeExponentFactor
        return positiveExponentFactor, negativeExponentFactor

    @staticmethod
    def getFundingFeeAmountPerSize(collateralToken: TokenInfo, isLong: bool, pool_data: PoolData):
        if collateralToken == pool_data.market.long_token:
            if isLong:
                return pool_data.status.longTokenFundingFeeAmountPerSizeLong
            else:
                return pool_data.status.longTokenFundingFeeAmountPerSizeShort
        else:
            if isLong:
                return pool_data.status.shortTokenFundingFeeAmountPerSizeLong
            else:
                return pool_data.status.shortTokenFundingFeeAmountPerSizeShort

    @staticmethod
    def getClaimableFundingAmountPerSize(collateralToken: TokenInfo, isLong: bool, pool_data: PoolData):
        if collateralToken == pool_data.market.long_token:
            if isLong:
                return pool_data.status.longTokenClaimableFundingAmountPerSizeLong
            else:
                return pool_data.status.longTokenClaimableFundingAmountPerSizeShort
        else:
            if isLong:
                return pool_data.status.shortTokenClaimableFundingAmountPerSizeLong
            else:
                return pool_data.status.shortTokenClaimableFundingAmountPerSizeShort

    @staticmethod
    def getNextBorrowingFees(position: Position, pool_status: GmxV2PoolStatus):
        nextCumulativeBorrowingFactor = MarketUtils.getCumulativeBorrowingFactor(position.isLong, pool_status)
        diffFactor = nextCumulativeBorrowingFactor - position.borrowingFactor
        return position.sizeInUsd * diffFactor

    @staticmethod
    def getVirtualInventoryForPositions(token: TokenInfo, pool_data: PoolData) -> tuple[bool, float]:
        """
        @dev get the virtual inventory for positions
        @param token the token to check
        """
        value = pool_data.status.virtualPositionInventory
        has_virtual_inventory = True if value > 0 else False

        return has_virtual_inventory, value

    @staticmethod
    def getCachedTokenPrice(token: TokenInfo, pool: GmxV2Pool, prices: MarketPrices) -> float:
        if token == pool.long_token:
            return prices.longTokenPrice
        if token == pool.short_token:
            return prices.shortTokenPrice
        if token == pool.index_token:
            return prices.indexTokenPrice

        raise DemeterError(f"UnableToGetCachedTokenPrice, {token})")
