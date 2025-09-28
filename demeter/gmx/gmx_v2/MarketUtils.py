import dataclasses
from typing import Tuple

from ._typing import PoolConfig, GmxV2PoolStatus, Market
from .Position import Position
from .._typing2 import GmxV2Pool


@dataclasses.dataclass
class Price:
    min: float
    max: float


@dataclasses.dataclass
class MarketPrices:
    indexTokenPrice: Price
    longTokenPrice: Price
    shortTokenPrice: Price


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

    @staticmethod
    def getOppositeToken(inputToken: str, market: Market) -> str:
        if inputToken == market.longToken.address:
            return market.shortToken
        if inputToken == market.shortToken.address:
            return market.longToken

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
            latestFundingAmountPerSize: float,
            positionFundingAmountPerSize: float,
            positionSizeInUsd: float
    ) -> float:
        fundingDiffFactor = latestFundingAmountPerSize - positionFundingAmountPerSize
        fundingAmount = positionSizeInUsd * fundingDiffFactor  # todo denominator
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
    def getCappedPositionImpactUsd(indexTokenPrice: float, priceImpactUsd: float, sizeDeltaUsd: float, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        if priceImpactUsd < 0:
            return priceImpactUsd
        impactPoolAmount = pool_status.positionImpactPoolAmount
        maxPriceImpactUsdBasedOnImpactPool = impactPoolAmount * indexTokenPrice
        if priceImpactUsd > maxPriceImpactUsdBasedOnImpactPool:
            priceImpactUsd = maxPriceImpactUsdBasedOnImpactPool
        maxPriceImpactFactor = MarketUtils.getMaxPositionImpactFactor(True, pool_status, pool_config)
        maxPriceImpactUsdBasedOnMaxPriceImpactFactor = sizeDeltaUsd * maxPriceImpactFactor
        if priceImpactUsd > maxPriceImpactUsdBasedOnMaxPriceImpactFactor:
            priceImpactUsd = maxPriceImpactUsdBasedOnMaxPriceImpactFactor
        return priceImpactUsd

    @staticmethod
    def getMaxPositionImpactFactor(isPositive: bool, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        maxPositiveImpactFactor = pool_config.maxPositiveImpactFactor
        maxNegativeImpactFactor = pool_config.maxNegativeImpactFactor
        if maxPositiveImpactFactor > maxNegativeImpactFactor:
            maxPositiveImpactFactor = maxNegativeImpactFactor
        return maxPositiveImpactFactor if isPositive else maxNegativeImpactFactor

    @staticmethod
    def getPoolAmount(market: Market, poolAmount: float):
        divisor = MarketUtils.getPoolDivisor(market.longToken, market.shortToken)
        return poolAmount / divisor

    @staticmethod
    def getPoolDivisor(longToken: str, shortToken: str) -> int:
        return 2 if longToken == shortToken else 1

    @staticmethod
    def getPnl(indexTokenPrice: Price, isLong: bool, pool_status: GmxV2PoolStatus):
        openInterest = pool_status.openInterestLong if isLong else pool_status.openInterestShort
        openInterestInTokens = pool_status.openInterestInTokensLong if isLong else pool_status.openInterestInTokensShort

        price = indexTokenPrice.max

        openInterestValue = openInterestInTokens * price
        pnl = openInterestValue - openInterest if isLong else openInterest - openInterestValue
        return pnl

    @staticmethod
    def getCappedPnl(isLong: bool, pnl: float, poolUsd: float, pool_config: PoolConfig):
        maxPnlFactor = pool_config.maxPnlFactorForTraderLong if isLong else pool_config.maxPnlFactorForTraderShort
        maxPnl = poolUsd * maxPnlFactor
        return maxPnl if pnl > maxPnl else pnl

    @staticmethod
    def getMinCollateralFactorForOpenInterest(isLong: bool, openInterestDelta: float, pool_status: GmxV2PoolStatus):
        openInterest = pool_status.openInterestLong if isLong else pool_status.openInterestShort
        openInterest = openInterest + openInterestDelta
        multiplierFactor = pool_status.minCollateralFactorForOpenInterestMultiplierLong if isLong else pool_status.minCollateralFactorForOpenInterestMultiplierShort
        return openInterest * multiplierFactor

    @staticmethod
    def getAdjustedPositionImpactFactor(isPositive: bool, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        positiveImpactFactor, negativeImpactFactor = MarketUtils.getAdjustedPositionImpactFactors(pool_status, pool_config)
        return positiveImpactFactor if isPositive else negativeImpactFactor

    @staticmethod
    def getAdjustedPositionImpactFactors(pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        positiveImpactFactor = pool_config.positionImpactFactorPositive
        negativeImpactFactor = pool_config.positionImpactFactorNegative
        if positiveImpactFactor > negativeImpactFactor:
            positiveImpactFactor = negativeImpactFactor
        return positiveImpactFactor, negativeImpactFactor

    @staticmethod
    def getFundingFeeAmountPerSize(collateralToken: str, isLong: bool, pool: GmxV2Pool, pool_status: GmxV2PoolStatus):
        if collateralToken == pool.long_token:
            if isLong:
                return pool_status.longTokenFundingFeeAmountPerSizeLong
            else:
                return pool_status.longTokenFundingFeeAmountPerSizeShort
        else:
            if isLong:
                return pool_status.shortTokenFundingFeeAmountPerSizeLong
            else:
                return pool_status.shortTokenFundingFeeAmountPerSizeShort

    @staticmethod
    def getClaimableFundingAmountPerSize(collateralToken, isLong: bool, pool: GmxV2Pool, pool_status: GmxV2PoolStatus):
        if collateralToken == pool.long_token:
            if isLong:
                return pool_status.longTokenClaimableFundingAmountPerSizeLong
            else:
                return pool_status.longTokenClaimableFundingAmountPerSizeShort
        else:
            if isLong:
                return pool_status.shortTokenClaimableFundingAmountPerSizeLong
            else:
                return pool_status.shortTokenClaimableFundingAmountPerSizeShort

    @staticmethod
    def getNextBorrowingFees(pending_borrowing_time, position: Position, market: Market, prices: MarketPrices, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        nextCumulativeBorrowingFactor, _ = MarketUtils.getNextCumulativeBorrowingFactor(pending_borrowing_time, market, prices, position.isLong, pool_status, pool_config)
        diffFactor = nextCumulativeBorrowingFactor - position.borrowingFactor
        return position.sizeInUsd * diffFactor

    @staticmethod
    def getNextCumulativeBorrowingFactor(pending_borrowing_time, market: Market, prices: MarketPrices, isLong: bool, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        durationInSeconds = pending_borrowing_time  # MarketUtils.getSecondsSinceCumulativeBorrowingFactorUpdated(isLong, pool_status)  # todo 传入数据
        borrowingFactorPerSecond = MarketUtils.getBorrowingFactorPerSecond(isLong, prices, market, pool_status, pool_config)
        cumulativeBorrowingFactor = MarketUtils.getCumulativeBorrowingFactor(isLong, pool_status)
        delta = durationInSeconds * borrowingFactorPerSecond
        nextCumulativeBorrowingFactor = cumulativeBorrowingFactor + delta
        return nextCumulativeBorrowingFactor, delta

    @staticmethod
    def getSecondsSinceCumulativeBorrowingFactorUpdated(isLong: bool, pool_status: GmxV2PoolStatus):
        updatedAt = MarketUtils.getCumulativeBorrowingFactorUpdatedAt(isLong)  # todo no need
        if updatedAt == 0:
            return 0
        seconds = pool_status.timestamp.timestamp() - updatedAt  # todo debug
        return seconds

    @staticmethod
    def getCumulativeBorrowingFactorUpdatedAt(isLong: bool):
        return 0  # todo

    @staticmethod
    def getBorrowingFactorPerSecond(isLong: bool, prices: MarketPrices, market: Market, pool_status: GmxV2PoolStatus, pool_config: PoolConfig):
        reservedUsd = MarketUtils.getReservedUsd(isLong, prices, market, pool_status)
        if reservedUsd == 0:
            return 0
        skipBorrowingFeeForSmallerSide = pool_config.skip_borrowing_fee_for_smaller_side  # todo SKIP_BORROWING_FEE_FOR_SMALLER_SIDE
        if skipBorrowingFeeForSmallerSide:
            longOpenInterest = MarketUtils.getOpenInterest(market, True, pool_status)
            shortOpenInterest = MarketUtils.getOpenInterest(market, False, pool_status)
            if isLong and longOpenInterest < shortOpenInterest:
                return 0
            if not isLong and shortOpenInterest < longOpenInterest:
                return 0
        poolUsd = MarketUtils.getPoolUsdWithoutPnl(market, prices, isLong, pool_status)  # done
        optimalUsageFactor = 0.75  # todo 最佳利用率 config
        if optimalUsageFactor != 0:
            return MarketUtils.getKinkBorrowingFactor(market, isLong, reservedUsd, poolUsd, pool_config, pool_status, optimalUsageFactor)  # todo
        borrowingExponentFactor = 0  # getBorrowingExponentFactor
        reservedUsdToPoolFactor = reservedUsd * borrowingExponentFactor
        borrowingFactor = 0  # todo
        return reservedUsdToPoolFactor * borrowingFactor

    @staticmethod
    def getPoolUsdWithoutPnl(market, prices, isLong, pool_status):
        token = market.longToken if isLong else market.shortToken
        _poolAmount = pool_status.longAmount if token == market.longToken else pool_status.shortAmount
        poolAmount = MarketUtils.getPoolAmount(market, _poolAmount)
        tokenPrice = prices.longTokenPrice.max if isLong else prices.shortTokenPrice.max
        return poolAmount * tokenPrice

    @staticmethod
    def getKinkBorrowingFactor(market, isLong, reservedUsd, poolUsd, pool_config: PoolConfig, pool_status: GmxV2PoolStatus, optimalUsageFactor=0.75):
        usageFactor = MarketUtils.getUsageFactor(market, isLong, reservedUsd, poolUsd, pool_config, pool_status)  # todo
        baseBorrowingFactor = pool_config.baseBorrowingFactorLong if isLong else pool_config.baseBorrowingFactorShort  # todo config
        borrowingFactorPerSecond = usageFactor * baseBorrowingFactor
        if usageFactor > optimalUsageFactor and 1 > optimalUsageFactor:  # 1 > 0.75
            diff = usageFactor - optimalUsageFactor
            aboveOptimalUsageBorrowingFactor = 0  # read from config
            additionalBorrowingFactorPerSecond = 0
            if aboveOptimalUsageBorrowingFactor > baseBorrowingFactor:
                additionalBorrowingFactorPerSecond = aboveOptimalUsageBorrowingFactor - baseBorrowingFactor
            divisor = 1 - optimalUsageFactor
            borrowingFactorPerSecond += additionalBorrowingFactorPerSecond * diff / divisor
        return borrowingFactorPerSecond

    @staticmethod
    def getUsageFactor(market, isLong, reservedUsd, poolUsd, pool_config: PoolConfig, pool_status: GmxV2PoolStatus):
        reserveFactor = MarketUtils.getOpenInterestReserveFactor(market.marketToken, isLong, pool_config)
        maxReservedUsd = poolUsd * reserveFactor
        reserveUsageFactor = reservedUsd / maxReservedUsd
        if pool_config.ignore_open_interest_for_usage_factor:  # todo True
            return reserveUsageFactor
        maxOpenInterest = MarketUtils.getMaxOpenInterest(market.marketToken, isLong)  # todo config
        openInterest = pool_status.openInterestLong if isLong else pool_status.openInterestShort
        openInterestUsageFactor = openInterest / maxOpenInterest
        return reserveUsageFactor if reserveUsageFactor > openInterestUsageFactor else openInterestUsageFactor

    @staticmethod
    def getOpenInterestReserveFactor(marketToken, isLong, pool_config: PoolConfig):
        # openInterestReserveFactorKey
        return pool_config.openInterestReserveFactorLong if isLong else pool_config.openInterestReserveFactorShort

    @staticmethod
    def getMaxOpenInterest(marketToken, isLong):
        # maxOpenInterestKey
        return 45769000000000000000000000000000000000

    @staticmethod
    def getReservedUsd(isLong: bool, prices: MarketPrices, market: Market, pool_status: GmxV2PoolStatus):
        if isLong:
            openInterestInTokens = MarketUtils.getOpenInterestInTokens(market, isLong, pool_status)
            reservedUsd = openInterestInTokens * prices.indexTokenPrice.max
        else:
            reservedUsd = MarketUtils.getOpenInterest(market, isLong, pool_status)
        return reservedUsd

    @staticmethod
    def getOpenInterestInTokens(market: Market, isLong: bool, pool_status: GmxV2PoolStatus):
        divisor = 2 if market.longToken == market.shortToken else 1
        if isLong:
            return pool_status.openInterestInTokensLong / divisor
        else:
            return pool_status.openInterestInTokensShort / divisor

    @staticmethod
    def getOpenInterest(market: Market, isLong: bool, pool_status: GmxV2PoolStatus):
        divisor = 2 if market.longToken == market.shortToken else 1
        if isLong:
            return pool_status.openInterestLong / divisor
        else:
            return pool_status.openInterestShort / divisor

    @staticmethod
    def getFundingAmountPerSizeDelta(fundingUsd, openInterest, tokenPrice):
        if fundingUsd == 0 or openInterest == 0:
            return 0
        fundingUsdPerSize = fundingUsd / openInterest
        return fundingUsdPerSize / tokenPrice
