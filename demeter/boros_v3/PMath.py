

class PMathOverflowError(Exception):
    """Raised when an overflow or invalid operation occurs."""
    pass


class PMath:
    """Math utility class with fixed-point arithmetic (WAD = 10^18)."""
    
    # Constants
    ONE = 10**18  # 18 decimal places
    IONE = 10**18  # 18 decimal places as int256
    ONE_YEAR = 365 * 24 * 60 * 60  # 365 days in seconds
    IONE_YEAR = 365 * 24 * 60 * 60  # 365 days as int256
    ONE_MUL_YEAR = 10**18 * 365 * 24 * 60 * 60
    IONE_MUL_YEAR = 10**18 * 365 * 24 * 60 * 60
    
    @staticmethod
    def inc(x: int) -> int:
        """Increment by 1."""
        return x + 1
    
    @staticmethod
    def dec(x: int) -> int:
        """Decrement by 1."""
        return x - 1
    
    @staticmethod
    def mul_up(x: int, y: int) -> int:
        """
        Multiply two uint256 values and round up.
        Uses WAD (10^18) scaling.
        """
        if y == 0:
            return 0
        z = x * y
        # Check for overflow: x <= type(uint256).max / y
        if x > (2**256 - 1) // y:
            raise PMathOverflowError("MulWadFailed: multiplication overflow")
        # Round up: z = floor(z / ONE) + (1 if z % ONE != 0 else 0)
        return z // PMath.ONE + (1 if z % PMath.ONE != 0 else 0)
    
    @staticmethod
    def mul_down(x: int, y: int) -> int:
        """
        Multiply two uint256 values and round down.
        Uses WAD (10^18) scaling.
        """
        if x == 0 or y == 0:
            return 0
        # Check for overflow: x <= type(uint256).max / y
        if x > (2**256 - 1) // y:
            raise PMathOverflowError("MulWadFailed: multiplication overflow")
        return (x * y) // PMath.ONE
    
    @staticmethod
    def mul_down_int(x: int, y: int) -> int:
        """
        Multiply two int256 values and round down.
        Uses WAD (10^18) scaling.
        """
        z = x * y
        # Check for overflow
        if x == 0:
            return 0
        if z // x != y:
            raise PMathOverflowError("SMulWadFailed: multiplication overflow")
        if x == -1 and y == -2**255:
            raise PMathOverflowError("SMulWadFailed: overflow when x=-1 and y=MIN_INT256")
        return z // PMath.IONE
    
    @staticmethod
    def div_down(x: int, y: int) -> int:
        """
        Divide two uint256 values and round down.
        Uses WAD (10^18) scaling.
        """
        if y == 0:
            raise PMathOverflowError("DivWadFailed: division by zero")
        # Check: x <= type(uint256).max / ONE
        if x > (2**256 - 1) // PMath.ONE:
            raise PMathOverflowError("DivWadFailed: division overflow")
        return (x * PMath.ONE) // y
    
    @staticmethod
    def div_down_int(x: int, y: int) -> int:
        """
        Divide two int256 values and round down.
        Uses WAD (10^18) scaling.
        """
        if y == 0:
            raise PMathOverflowError("SDivWadFailed: division by zero")
        z = x * PMath.IONE
        # Check: (x * ONE) / ONE == x
        if z // PMath.IONE != x:
            raise PMathOverflowError("SDivWadFailed: multiplication overflow")
        return z // y
    
    @staticmethod
    def raw_div_up(x: int, d: int) -> int:
        """
        Divide two uint256 values and round up.
        No WAD scaling, raw division with ceiling.
        """
        if d == 0:
            raise PMathOverflowError("DivFailed: division by zero")
        return x // d + (1 if x % d != 0 else 0)
    
    @staticmethod
    def raw_div_ceil(x: int, d: int) -> int:
        """
        Divide two int256 values and round up (towards positive infinity).
        No WAD scaling.
        """
        if d == 0:
            raise PMathOverflowError("DivFailed: division by zero")
        z = x // d
        # If x and d have the same sign and there's a remainder, add 1
        if (x >= 0 and d > 0) or (x < 0 and d < 0):
            if x % d != 0:
                z += 1
        return z
    
    @staticmethod
    def raw_div_floor(x: int, d: int) -> int:
        """
        Divide two int256 values and round down (towards negative infinity).
        No WAD scaling.
        """
        if d == 0:
            raise PMathOverflowError("DivFailed: division by zero")
        z = x // d
        # If x and d have opposite signs and there's a remainder, subtract 1
        if (x >= 0 and d < 0) or (x < 0 and d > 0):
            if x % d != 0:
                z -= 1
        return z
    
    @staticmethod
    def mul_ceil(x: int, y: int) -> int:
        """
        Multiply two int256 values and round up using WAD scaling.
        """
        return PMath.raw_div_ceil(x * y, PMath.IONE)
    
    @staticmethod
    def mul_floor(x: int, y: int) -> int:
        """
        Multiply two int256 values and round down using WAD scaling.
        """
        return PMath.raw_div_floor(x * y, PMath.IONE)
    
    @staticmethod
    def tweak_up(a: int, factor: int) -> int:
        """
        Multiply a by (1 + factor) with rounding up.
        """
        return PMath.mul_up(a, PMath.ONE + factor)
    
    @staticmethod
    def tweak_down(a: int, factor: int) -> int:
        """
        Multiply a by (1 - factor) with rounding down.
        """
        return PMath.mul_down(a, PMath.ONE - factor)
    
    @staticmethod
    def abs(x: int) -> int:
        """
        Get absolute value of int256.
        """
        if x >= 0:
            return x
        return -x
    
    @staticmethod
    def neg(x: int) -> int:
        """
        Negate uint256 value (convert to int256 and multiply by -1).
        """
        return -int(x)
    
    @staticmethod
    def max(x: int, y: int) -> int:
        """
        Return maximum of two uint256 values.
        """
        return x if x > y else y
    
    @staticmethod
    def max_int(x: int, y: int) -> int:
        """
        Return maximum of two int256 values.
        """
        return x if x > y else y
    
    @staticmethod
    def max_32(x: int, y: int) -> int:
        """
        Return maximum of two uint32 values.
        """
        return x if x > y else y
    
    @staticmethod
    def max_40(x: int, y: int) -> int:
        """
        Return maximum of two uint40 values.
        """
        return x if x > y else y
    
    @staticmethod
    def min(x: int, y: int) -> int:
        """
        Return minimum of two uint256 values.
        """
        return x if x < y else y
    
    @staticmethod
    def min_int(x: int, y: int) -> int:
        """
        Return minimum of two int256 values.
        """
        return x if x < y else y
    
    @staticmethod
    def sign(x: int) -> int:
        """
        Return sign of int256: 1 if positive, -1 if negative, 0 if zero.
        """
        if x > 0:
            return 1
        elif x < 0:
            return -1
        return 0
    
    @staticmethod
    def avg(x: int, y: int) -> int:
        """
        Return average of two uint256 values.
        Uses bitwise optimization: (x & y) + ((x ^ y) >> 1)
        """
        return (x & y) + ((x ^ y) >> 1)
    
    @staticmethod
    def avg_int(x: int, y: int) -> int:
        """
        Return average of two int256 values.
        Uses: (x >> 1) + (y >> 1) + (x & y & 1)
        """
        return (x >> 1) + (y >> 1) + ((x & y) & 1)
    
    # Cast functions
    
    @staticmethod
    def to_int(x: int) -> int:
        """
        Convert uint256 to int256 with overflow check.
        """
        if x > 2**255 - 1:
            raise PMathOverflowError("Overflow: uint256 exceeds int256 max")
        return int(x)
    
    @staticmethod
    def to_int128(x: int) -> int:
        """
        Convert uint256 to int128 with overflow check.
        """
        if x > 2**127 - 1:
            raise PMathOverflowError("Overflow: uint256 exceeds int128 max")
        return PMath._int128(x)
    
    @staticmethod
    def to_int112(x: int) -> int:
        """
        Convert int256 to int112 with overflow check.
        """
        if x < -(2**111) or x > 2**111 - 1:
            raise PMathOverflowError("Overflow: int256 exceeds int112 range")
        return int(x)
    
    @staticmethod
    def to_int128_int(x: int) -> int:
        """
        Convert int256 to int128 with overflow check.
        """
        if x < -(2**127) or x > 2**127 - 1:
            raise PMathOverflowError("Overflow: int256 exceeds int128 range")
        return int(x)
    
    @staticmethod
    def to_uint(x: int) -> int:
        """
        Convert int256 to uint256 with overflow check.
        """
        if x < 0:
            raise PMathOverflowError("Overflow: negative int256 cannot convert to uint256")
        return int(x)
    
    @staticmethod
    def to_uint128(x: int) -> int:
        """
        Convert int256 to uint128 with overflow check.
        """
        if x < 0 or x >= 2**128:
            raise PMathOverflowError("Overflow: int256 out of uint128 range")
        return int(x)
    
    @staticmethod
    def to_uint8_bool(x: bool) -> int:
        """
        Convert bool to uint8.
        """
        return 1 if x else 0
    
    @staticmethod
    def to_uint8(x: int) -> int:
        """
        Convert uint256 to uint8 with overflow check.
        """
        if x >= 2**8:
            raise PMathOverflowError("Overflow: value exceeds uint8 max")
        return int(x)
    
    @staticmethod
    def to_uint16(x: int) -> int:
        """
        Convert uint256 to uint16 with overflow check.
        """
        if x >= 2**16:
            raise PMathOverflowError("Overflow: value exceeds uint16 max")
        return int(x)
    
    @staticmethod
    def to_uint32(x: int) -> int:
        """
        Convert uint256 to uint32 with overflow check.
        """
        if x >= 2**32:
            raise PMathOverflowError("Overflow: value exceeds uint32 max")
        return int(x)
    
    @staticmethod
    def to_uint40(x: int) -> int:
        """
        Convert uint256 to uint40 with overflow check.
        """
        if x >= 2**40:
            raise PMathOverflowError("Overflow: value exceeds uint40 max")
        return int(x)
    
    @staticmethod
    def to_uint64(x: int) -> int:
        """
        Convert uint256 to uint64 with overflow check.
        """
        if x >= 2**64:
            raise PMathOverflowError("Overflow: value exceeds uint64 max")
        return int(x)
    
    @staticmethod
    def to_uint128_uint(x: int) -> int:
        """
        Convert uint256 to uint128 with overflow check.
        """
        if x >= 2**128:
            raise PMathOverflowError("Overflow: value exceeds uint128 max")
        return int(x)
    
    @staticmethod
    def to_uint224(x: int) -> int:
        """
        Convert uint256 to uint224 with overflow check.
        """
        if x >= 2**224:
            raise PMathOverflowError("Overflow: value exceeds uint224 max")
        return int(x)
    
    @staticmethod
    def _int128(x: int) -> int:
        """Convert to 128-bit signed integer representation."""
        return x & ((1 << 127) - 1)
    
    @staticmethod
    def sqrt(x: int) -> int:
        """
        Compute integer square root using Babylonian method.
        Returns floor(sqrt(x)).
        """
        if x == 0:
            return 0
        
        # Initial estimate
        z = 181  # floor(sqrt(2**15)) approximation
        
        # Calculate bit shift for initial estimate
        r = 0
        if x > 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
            r |= 128
        if x >> r > 0xFFFFFFFFFFFFFFFFFF:
            r |= 64
        if x >> r > 0xFFFFFFFFFF:
            r |= 32
        if x >> r > 0xFFFFFF:
            r |= 16
        
        z = (z << (r >> 1)) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        
        # Improved initial estimate
        z = ((z + (x >> r)) // 2) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        z = ((z + (x // z)) // 2) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        z = ((z + (x // z)) // 2) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        z = ((z + (x // z)) // 2) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        z = ((z + (x // z)) // 2) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        z = ((z + (x // z)) // 2) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        z = ((z + (x // z)) // 2) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        
        # Final adjustment
        if z > x // z:
            z -= 1
        
        return z
    
    @staticmethod
    def is_a_approx_b(a: int, b: int, eps: int) -> bool:
        """
        Check if a is approximately equal to b within epsilon tolerance.
        Returns True if |a - b| <= eps * b.
        """
        lower = PMath.mul_down(b, PMath.ONE - eps)
        upper = PMath.mul_down(b, PMath.ONE + eps)
        return lower <= a <= upper
    
    @staticmethod
    def is_a_greater_approx_b(a: int, b: int, eps: int) -> bool:
        """
        Check if a is greater than or approximately equal to b.
        Returns True if a >= b and a <= b * (1 + eps).
        """
        return a >= b and a <= PMath.mul_down(b, PMath.ONE + eps)
    
    @staticmethod
    def is_a_smaller_approx_b(a: int, b: int, eps: int) -> bool:
        """
        Check if a is smaller than or approximately equal to b.
        Returns True if a <= b and a >= b * (1 - eps).
        """
        return a <= b and a >= PMath.mul_down(b, PMath.ONE - eps)
