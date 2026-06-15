import math


class TickMath:
    """
    TickMath library - converts between tick values and interest rates.

    This is similar to Uniswap V3's TickMath but with a different base rate.
    While Uniswap uses 1.0001 (0.01%), Boros uses 1.00005 (0.005%).

    Key formula:
    - For tick >= 0: rate = 1.00005^tick - 1
    - For tick < 0:  rate = -(1.00005^(-tick) - 1)

    This creates a symmetric, exponential price curve where:
    - tick = 0  -> rate = 0%
    - tick = 100 -> rate ≈ 0.5%
    - tick = 1000 -> rate ≈ 5%
    - tick = 10000 -> rate ≈ 65%
    """

    # Base rate: 1.00005 = 1 + 0.005% per tick
    BASE_RATE = 1.00005

    # Precomputed constants for the binary exponentiation algorithm
    # These are powers of BASE_RATE at bit positions
    # Similar to Uniswap V3 but with BASE_RATE = 1.00005 instead of 1.0001
    RATE_CONSTANTS = {
        0: 0xfffcb92e5f40b9f2f86266c763702fb7,  # bit 0
        1: 0xfff972677b0287f20ca2232ae174ac61,  # bit 1
        2: 0xfff2e4f9e77ca923223ffc276878b031,  # bit 2
        3: 0xffe5ca9f907218edf3c20a9b87d8b905,  # bit 3
        4: 0xffcb97ee039bed3373e5b571bf3e4989,  # bit 4
        5: 0xff973a9678d50163584a32b3255afbbc,  # bit 5
        6: 0xff2ea00defa36b3de45cff7e3bc651f2,  # bit 6
        7: 0xfe5deb59ac7b1aae542822b60b658f66,  # bit 7
        8: 0xfcbe817ac9c95c76b6730ccf91e6d8de,  # bit 8
        9: 0xf9879cae3104ef30d992ea9a423d2979,  # bit 9
        10: 0xf33916a17af80ec5fc60d88f617d0b95,  # bit 10
        11: 0xe7156db1a55bd580fae8391a0ef5618b,  # bit 11
        12: 0xd097adc1c6919e761394d554da360e46,  # bit 12
        13: 0xa9f6d43953345a56a0df0cb1c591fb10,  # bit 13
        14: 0x70d7d2303df60688dcde5dbd2c3f8bb3,  # bit 14
        15: 0x31bd8ddcefd287b5a91fb8c4681a9810,  # bit 15
    }

    # High tick constants (for ticks > 2^16)
    HIGH_RATE_CONSTANTS = {
        16: 0xf06345295e343b7bc86046165c00aba,  # bit 16
        17: 0x57b4d53300bbb68ed922df63e3590,  # bit 17
        18: 0x34fa3662ba5cbd83623db239c427,  # bit 18
    }

    @staticmethod
    def get_rate_at_tick(tick: int, step: int = 1) -> float:
        """
        Calculate rate at given tick with step multiplier.

        Args:
            tick: Tick value (can be negative)
            step: Step multiplier (must be < 16)

        Returns:
            Rate as a decimal (e.g., 0.05 for 5%)

        Formula:
            effective_tick = tick * step
            rate = BASE_RATE^effective_tick - 1
        """
        effective_tick = tick * step
        return TickMath._get_rate_at_tick(effective_tick)

    @staticmethod
    def _get_rate_at_tick(tick: int) -> float:
        """
        Internal rate calculation using binary exponentiation.

        Algorithm (lines 31-68 in TickMath.sol):
        1. Handle tick = 0 case
        2. Work with absolute value for calculation
        3. Use binary decomposition to compute BASE_RATE^abs(tick)
        4. For negative ticks, negate the result

        The binary exponentiation works by:
        - Decomposing abs(tick) into sum of powers of 2
        - Multiplying precomputed constants for each set bit
        - Using fixed-point arithmetic for precision
        """
        if tick == 0:
            return 0.0

        abs_tick = abs(tick)

        # Use Python's floating point for demonstration
        # In Solidity, this uses fixed-point arithmetic with 128-bit precision
        rate = (TickMath.BASE_RATE ** abs_tick) - 1

        # Apply sign
        if tick < 0:
            rate = -rate

        return rate

    @staticmethod
    def get_tick_at_rate(rate: float, step: int = 1) -> int:
        """
        Inverse function: calculate tick for given rate.

        Args:
            rate: Rate as decimal (e.g., 0.05 for 5%)
            step: Step multiplier

        Returns:
            Tick value

        Formula:
            tick = log(rate + 1) / log(BASE_RATE) / step
        """
        if rate == 0:
            return 0

        abs_rate = abs(rate)
        abs_tick = round(math.log(abs_rate + 1) / math.log(TickMath.BASE_RATE))

        if rate < 0:
            abs_tick = -abs_tick

        return abs_tick // step
