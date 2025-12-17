from demeter import DemeterError
from demeter.gmx.gmx_v2 import OrderType

# move from order to here due to circular import
class BaseOrderUtils:
    @staticmethod
    def isLiquidationOrder(_orderType: "OrderType") -> bool:
        return _orderType == OrderType.Liquidation

    @staticmethod
    def getExecutionPriceForIncrease(sizeDeltaUsd, sizeDeltaInTokens, acceptablePrice, isLong) -> float:
        if sizeDeltaInTokens == 0:
            raise DemeterError("EmptySizeDeltaInTokens")
        executionPrice = sizeDeltaUsd / sizeDeltaInTokens

        # increase order:
        #     - long: executionPrice should be smaller than acceptablePrice
        #     - short: executionPrice should be larger than acceptablePrice
        if (isLong and executionPrice <= acceptablePrice) or (not isLong and executionPrice >= acceptablePrice):
            return executionPrice

        #  the validateOrderTriggerPrice function should have validated if the price fulfills
        #  the order's trigger price
        #
        #  for increase orders, the negative price impact is not capped
        #
        #  for both increase and decrease orders, if it is due to price impact that the
        #  order cannot be fulfilled then the order should be frozen
        #
        #  this is to prevent gaming by manipulation of the price impact value
        #
        #  usually it should be costly to game the price impact value
        #  however, for certain cases, e.g. a user already has a large position opened
        #  the user may create limit orders that would only trigger after they close
        #  their position, this gives the user the option to cancel the pending order if
        #  prices do not move in their favour or to close their position and let the order
        #  execute if prices move in their favour
        #
        #  it may also be possible for users to prevent the execution of orders from other users
        #  by manipulating the price impact, though this should be costly
        raise DemeterError(
            f"OrderNotFulfillableAtAcceptablePrice, executionPrice: {executionPrice}, acceptablePrice: {acceptablePrice}"
        )

    @staticmethod
    def getExecutionPriceForDecrease(
        indexTokenPrice: float,
        positionSizeInUsd: float,
        positionSizeInTokens: float,
        sizeDeltaUsd: float,
        priceImpactUsd: float,
        acceptablePrice: float,
        isLong: bool,
    ) -> float:
        # Only the maximum impact factor is applied to cap the resulting priceImpactUsd here.
        # This does NOT include capping based on the price impact pool balance, so the computed
        # executionPrice may not reflect the actual executionPrice experienced by the order.
        # Consumers of this function should be aware that the final execution price may differ
        # if further capping is applied elsewhere based on the impact pool.

        # decrease order:
        #     - long: use the smaller price
        #     - short: use the larger price
        price = indexTokenPrice
        executionPrice = price

        # using closing of long positions as an example
        # realized pnl is calculated as totalPositionPnl * sizeDeltaInTokens / position.sizeInTokens
        # totalPositionPnl: position.sizeInTokens * executionPrice - position.sizeInUsd
        # sizeDeltaInTokens: position.sizeInTokens * sizeDeltaUsd / position.sizeInUsd
        # realized pnl: (position.sizeInTokens * executionPrice - position.sizeInUsd) * (position.sizeInTokens * sizeDeltaUsd / position.sizeInUsd) / position.sizeInTokens
        # realized pnl: (position.sizeInTokens * executionPrice - position.sizeInUsd) * (sizeDeltaUsd / position.sizeInUsd)
        # priceImpactUsd should adjust the execution price such that:
        # [(position.sizeInTokens * executionPrice - position.sizeInUsd) * (sizeDeltaUsd / position.sizeInUsd)] -
        # [(position.sizeInTokens * price - position.sizeInUsd) * (sizeDeltaUsd / position.sizeInUsd)] = priceImpactUsd

        # (position.sizeInTokens * executionPrice - position.sizeInUsd) - (position.sizeInTokens * price - position.sizeInUsd)
        # = priceImpactUsd / (sizeDeltaUsd / position.sizeInUsd)
        # = priceImpactUsd * position.sizeInUsd / sizeDeltaUsd

        # position.sizeInTokens * executionPrice - position.sizeInTokens * price = priceImpactUsd * position.sizeInUsd / sizeDeltaUsd
        # position.sizeInTokens * (executionPrice - price) = priceImpactUsd * position.sizeInUsd / sizeDeltaUsd
        # executionPrice - price = (priceImpactUsd * position.sizeInUsd) / (sizeDeltaUsd * position.sizeInTokens)
        # executionPrice = price + (priceImpactUsd * position.sizeInUsd) / (sizeDeltaUsd * position.sizeInTokens)
        # executionPrice = price + (priceImpactUsd / sizeDeltaUsd) * (position.sizeInUsd / position.sizeInTokens)
        # executionPrice = price + (priceImpactUsd * position.sizeInUsd / position.sizeInTokens) / sizeDeltaUsd

        # e.g. if price is $2000, sizeDeltaUsd is $5000, priceImpactUsd is -$1000, position.sizeInUsd is $10,000, position.sizeInTokens is 5
        # executionPrice = 2000 + (-1000 * 10,000 / 5) / 5000 = 1600
        # realizedPnl based on price, without price impact: 0
        # realizedPnl based on executionPrice, with price impact: (5 * 1600 - 10,000) * (5 * 5000 / 10,000) / 5 => -1000

        # a positive adjustedPriceImpactUsd would decrease the executionPrice
        # a negative adjustedPriceImpactUsd would increase the executionPrice

        # for increase orders, the adjustedPriceImpactUsd is added to the divisor
        # a positive adjustedPriceImpactUsd would increase the divisor and decrease the executionPrice
        # increase long order:
        #      - if price impact is positive, adjustedPriceImpactUsd should be positive, to decrease the executionPrice
        #      - if price impact is negative, adjustedPriceImpactUsd should be negative, to increase the executionPrice
        # increase short order:
        #      - if price impact is positive, adjustedPriceImpactUsd should be negative, to increase the executionPrice
        #      - if price impact is negative, adjustedPriceImpactUsd should be positive, to decrease the executionPrice

        # for decrease orders, the adjustedPriceImpactUsd adjusts the numerator
        # a positive adjustedPriceImpactUsd would increase the divisor and increase the executionPrice
        # decrease long order:
        #      - if price impact is positive, adjustedPriceImpactUsd should be positive, to increase the executionPrice
        #      - if price impact is negative, adjustedPriceImpactUsd should be negative, to decrease the executionPrice
        # decrease short order:
        #      - if price impact is positive, adjustedPriceImpactUsd should be negative, to decrease the executionPrice
        #      - if price impact is negative, adjustedPriceImpactUsd should be positive, to increase the executionPrice
        # adjust price by price impact
        if sizeDeltaUsd > 0 and positionSizeInTokens > 0:
            adjustedPriceImpactUsd = priceImpactUsd if isLong else -priceImpactUsd

            if adjustedPriceImpactUsd < 0 and -adjustedPriceImpactUsd > sizeDeltaUsd:
                raise DemeterError(
                    f"PriceImpactLargerThanOrderSize(adjustedPriceImpactUsd: {adjustedPriceImpactUsd}, sizeDeltaUsd: {sizeDeltaUsd})"
                )

            adjustment = positionSizeInUsd * adjustedPriceImpactUsd / positionSizeInTokens / sizeDeltaUsd
            _executionPrice = price + adjustment

            if _executionPrice < 0:
                raise DemeterError(
                    f"NegativeExecutionPrice({_executionPrice}, {price}, {positionSizeInUsd}, {adjustedPriceImpactUsd}, {sizeDeltaUsd})"
                )

            executionPrice = _executionPrice

        # decrease order:
        #     - long: executionPrice should be larger than acceptablePrice
        #     - short: executionPrice should be smaller than acceptablePrice
        if (isLong and executionPrice >= acceptablePrice) or (not isLong and executionPrice <= acceptablePrice):
            return executionPrice

        # the validateOrderTriggerPrice function should have validated if the price fulfills
        # the order's trigger price

        # for decrease orders, the price impact should already be capped, so if the user
        # had set an acceptable price within the range of the capped price impact, then
        # the order should be fulfillable at the acceptable price

        # for increase orders, the negative price impact is not capped

        # for both increase and decrease orders, if it is due to price impact that the
        # order cannot be fulfilled then the order should be frozen

        # this is to prevent gaming by manipulation of the price impact value

        # usually it should be costly to game the price impact value
        # however, for certain cases, e.g. a user already has a large position opened
        # the user may create limit orders that would only trigger after they close
        # their position, this gives the user the option to cancel the pending order if
        # prices do not move in their favour or to close their position and let the order
        # execute if prices move in their favour

        # it may also be possible for users to prevent the execution of orders from other users
        # by manipulating the price impact, though this should be costly
        raise DemeterError(f"OrderNotFulfillableAtAcceptablePrice({executionPrice}, {acceptablePrice})")
