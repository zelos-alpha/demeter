import math
from decimal import Decimal


class Calc:
    @staticmethod
    def sumReturnUint256(a: float, b: float) -> float:
        """
        Adds two numbers together and return a uint256 value, treating the second number as a signed integer.
        :param a: the first number
        :param b: the second number
        :return:the result of adding the two numbers together
        """
        # if b > 0:
        #     return a + abs(b)
        #
        # return a - abs(b)
        result = a + b
        if result < 0:
            raise RuntimeError(f"The result of adding {a} to {b} is negative")

        return result

    @staticmethod
    def diff(a: float, b: float) -> float:
        """
        Calculates the absolute difference between two numbers.

        :param a: the first number
        :param b: the second number
        :return :the absolute difference between the two numbers
        """
        return abs(a - b)

    @staticmethod
    def toSigned(a: float, isPositive: bool) -> float:
        return a if isPositive else -a

    @staticmethod
    def roundUpMagnitudeDivision(a: float, b: float) -> float:
        return math.ceil(a / b)


class PricingUtils:
    @staticmethod
    def getPriceImpactUsdForSameSideRebalance(
        initialDiffUsd: float,
        nextDiffUsd: float,
        impactFactor: float,
        impactExponentFactor: float,
    ) -> float:
        """
        @dev get the price impact USD if there is no crossover in balance
        a crossover in balance is for example if the long open interest is larger
        than the short open interest, and a short position is opened such that the
        short open interest becomes larger than the long open interest
        :param initialDiffUsd: the initial difference in USD
        :param nextDiffUsd: the next difference in USD
        :param impactFactor: the impact factor
        :param impactExponentFactor: the impact exponent factor
        """
        hasPositiveImpact: bool = nextDiffUsd < initialDiffUsd

        deltaDiffUsd: float = Calc.diff(
            PricingUtils.applyImpactFactor(initialDiffUsd, impactFactor, impactExponentFactor),
            PricingUtils.applyImpactFactor(nextDiffUsd, impactFactor, impactExponentFactor),
        )

        priceImpactUsd: float = Calc.toSigned(deltaDiffUsd, hasPositiveImpact)

        return priceImpactUsd

    @staticmethod
    def getPriceImpactUsdForCrossoverRebalance(
        initialDiffUsd: float,
        nextDiffUsd: float,
        positiveImpactFactor: float,
        negativeImpactFactor: float,
        impactExponentFactor: float,
    ) -> float:
        """
        @dev get the price impact USD if there is a crossover in balance
        a crossover in balance is for example if the long open interest is larger
        than the short open interest, and a short position is opened such that the
        short open interest becomes larger than the long open interest
        """
        positiveImpactUsd: float = PricingUtils.applyImpactFactor(
            initialDiffUsd, positiveImpactFactor, impactExponentFactor
        )
        negativeImpactUsd: float = PricingUtils.applyImpactFactor(
            nextDiffUsd, negativeImpactFactor, impactExponentFactor
        )
        deltaDiffUsd: float = Calc.diff(positiveImpactUsd, negativeImpactUsd)

        priceImpactUsd: float = Calc.toSigned(deltaDiffUsd, positiveImpactUsd > negativeImpactUsd)

        return priceImpactUsd

    # @staticmethod
    # def applyImpactFactor(diffUsd: int, impactFactor: int, impactExponentFactor: int) -> int:
    #     """
    #     @dev apply the impact factor calculation to a USD diff value
    #     :param diffUsd: the difference in USD
    #     :param impactFactor: the impact factor
    #     :param impactExponentFactor: the impact exponent factor
    #     """
    #     exponentValue: int = Precision.applyExponentFactor(diffUsd, impactExponentFactor)
    #     return Precision.applyFactor(exponentValue, impactFactor)

    @staticmethod
    def applyImpactFactor(diffUsd: float, impactFactor: float, impactExponentFactor: float) -> float:
        exponentValue = diffUsd**impactExponentFactor
        return exponentValue * impactFactor

    @staticmethod
    def get_gm_price(pool_value: float, supply_amount: float) -> float:
        # pool value contains 10**30 and decimal
        # it is pool_value / 10**30 / supply * 10**18
        # 18 is decimal of GM
        return pool_value / supply_amount




class Precision:
    FLOAT_PRECISION: int = 10**30
    FLOAT_PRECISION_SQRT: int = 10**15

    WEI_PRECISION: int = 10**18
    BASIS_POINTS_DIVISOR: int = 10000

    FLOAT_TO_WEI_DIVISOR: int = 10**12

    @staticmethod
    def applyExponentFactor(floatValue: int, exponentFactor: int) -> int:
        # `PRBMathUD60x18.pow` doesn't work for `x` less than one
        if floatValue < Precision.FLOAT_PRECISION:
            return 0

        if exponentFactor == Precision.FLOAT_PRECISION:
            return floatValue

        decimal_value = (floatValue / Precision.FLOAT_PRECISION) ** (exponentFactor / Precision.FLOAT_PRECISION)

        return int(decimal_value * Precision.FLOAT_PRECISION)

    @staticmethod
    def applyFactor(value: float, factor: float) -> float:
        return factor * value
