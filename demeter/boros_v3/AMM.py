from dataclasses import dataclass
from ._typing import MarketAcc, AMMState, AMMSeedParams, Tuple


class Errors:
    """Error messages matching Solidity contract"""

    class MarketMatured(Exception):
        """Raised when trying to operate on a matured market"""
        pass

    class AMMInsufficientCashIn(Exception):
        """Raised when not enough cash provided for operation"""
        pass

    class AMMSignMismatch(Exception):
        """Raised when liquidity direction doesn't match position direction"""
        pass

    class AMMInsufficientLiquidity(Exception):
        """Raised when AMM doesn't have enough liquidity"""
        pass

    class AMMCutOffReached(Exception):
        """Raised when AMM has reached cutoff time"""
        pass

    class AMMWithdrawOnly(Exception):
        """Raised when AMM is in withdraw-only mode"""
        pass

    class AMMTotalSupplyCapExceeded(Exception):
        """Raised when total supply exceeds cap"""
        pass


@dataclass
class MintResult:
    """
    Result of adding liquidity to the AMM

    Attributes:
        net_cash_in: Amount of cash deposited
        net_lp_out: Amount of LP tokens received
    """
    net_cash_in: int
    net_lp_out: int


@dataclass
class BurnResult:
    """
    Result of removing liquidity from the AMM

    Attributes:
        net_cash_out: Amount of cash received
        net_size_out: Position size removed
        is_matured: Whether the market has matured
    """
    net_cash_out: int
    net_size_out: int
    is_matured: bool


@dataclass
class SwapResult:
    """
    Result of a swap in the AMM

    Attributes:
        cost_out: Fixed tokens required to receive float tokens
    """
    cost_out: int

class AMM:
    """Simulates an AMM"""

    def __init__(self, amm_id: int, market_id: int):
        self.amm_id = amm_id
        self.market_id = market_id
        self.fee_rate = 500000000000000  # 0.05%

    def _get_mark_rate(self) -> int:
        pass  # todo read from csv

    def _get_state(self) -> AMMState:
        pass  # todo read from csv

    def _swap(self, swap_size_out: int) -> int:
        pass

    def swap_by_router(self, size_out: int) -> int:
        """Execute swap and return cost"""
        cost_out = self._swap(size_out)
        cost_out, fee = self._applyFee(size_out, cost_out)
        return cost_out

    def _applyFee(self, size_out: int, cost_out: int) -> (int, int):
        fee = size_out * self.fee_rate
        new_cost = cost_out + fee
        return new_cost, fee


    def _mint(self,
              total_cash: int,
              total_size: int,
              max_cash_in: int,
              exact_size_in: int) -> (int, int):
        pass

    def mint_by_boros_router(self,
                             receiver: MarketAcc,
                             total_cash: int,
                             total_size: int,
                             max_cash_in: int,
                             exact_size_in: int) -> (int, int):
        net_cash_in, net_lp_out = self._mint(total_cash, total_size, max_cash_in, exact_size_in)
        return net_lp_out, net_lp_out

    def _burn(self,
              total_cash: int,
              total_size: int,
              lp_to_burn: int) -> (int, int):
        pass

    def burn_by_boros_router(self,
                             payer: MarketAcc,
                             total_cash: int,
                             total_size: int,
                             lp_to_burn: int) -> (int, int, int):
        net_cash_out, net_size_out, is_matured = self._burn(total_cash, total_size, lp_to_burn)
        return net_cash_out, net_size_out, is_matured

    def calc_swap_size(self, target_rate: int) -> int:
        """Calculate swap size for target rate"""
        return 1000000  # Mock size


class PMath:
    """
    Precision Math library for fixed-point arithmetic

    All operations are done with 18 decimal precision (like Solidity's PMath).
    """

    ONE = 10 ** 18  # Unit precision for fixed-point calculations

    @staticmethod
    def abs(value: int) -> int:
        """Absolute value"""
        return abs(value)

    @staticmethod
    def sign(value: int) -> int:
        """Sign function: -1, 0, or 1"""
        if value < 0:
            return -1
        elif value > 0:
            return 1
        return 0

    @staticmethod
    def int(value: int) -> int:
        """Convert to int256"""
        return int(value)

    @staticmethod
    def uint(value: int) -> int:
        """Convert to uint256 (clamped to 0)"""
        return max(0, value)

    @staticmethod
    def uint128(value: int) -> int:
        """Convert to uint128"""
        return value & ((1 << 128) - 1)

    @staticmethod
    def uint32(value: int) -> int:
        """Convert to uint32"""
        return value & ((1 << 32) - 1)

    @staticmethod
    def mul_down(a: int, b: int) -> int:
        """Floor multiplication: (a * b) / ONE"""
        return (a * b) // PMath.ONE

    @staticmethod
    def mul_up(a: int, b: int) -> int:
        """Ceiling multiplication"""
        return -(-(a * b) // PMath.ONE)

    @staticmethod
    def div_down(a: int, b: int) -> int:
        """Floor division: (a * b) / ONE"""
        return (a * PMath.ONE) // b

    @staticmethod
    def div_up(a: int, b: int) -> int:
        """Ceiling division"""
        return -(-(a * PMath.ONE) // b)

    @staticmethod
    def raw_div_up(a: int, b: int) -> int:
        """Raw ceiling division without scaling"""
        return -(-a // b) if b != 0 else 0

    @staticmethod
    def sqrt(value: int) -> int:
        """Integer square root (floor)"""
        if value == 0:
            return 0
        x = value
        y = (x + 1) // 2
        while y < x:
            x = y
            y = (x + value // x) // 2
        return x

    @staticmethod
    def pow(base: int, exponent: int) -> int:
        """Power function: base^(exponent/ONE)"""
        if exponent == 0:
            return PMath.ONE
        if exponent == PMath.ONE:
            return base

        # For simplicity, using integer power (would use log-exp in production)
        exp_ratio = exponent // PMath.ONE
        return pow(base, exp_ratio)

    @staticmethod
    def max(a: int, b: int) -> int:
        """Maximum of two values"""
        return a if a > b else b

    @staticmethod
    def min(a: int, b: int) -> int:
        """Minimum of two values"""
        return a if a < b else b

    @staticmethod
    def tweak_up(value: int, factor: int) -> int:
        """Increase value slightly for rate boundaries"""
        return value + value // factor

    @staticmethod
    def tweak_down(value: int, factor: int) -> int:
        """Decrease value slightly for rate boundaries"""
        return value - value // factor


class PositiveAMMMath:
    """
    Math library for Positive AMM calculations

    This class implements the core trading and liquidity math for the AMM.
    All calculations use fixed-point arithmetic with 18 decimal precision.
    """

    ONE = PMath.ONE

    @staticmethod
    def _snap_small_size_to0(size: int) -> int:
        """
        Snap small sizes to zero to avoid precision issues

        Positions smaller than 1e3 are considered noise and set to 0.
        This prevents dust positions from affecting calculations.

        Args:
            size: Position size to check

        Returns:
            Original size if large enough, 0 otherwise
        """
        return 0 if PMath.abs(size) < 10 ** 3 else size

    @staticmethod
    def calc_seed_output(
            params: AMMSeedParams,
            maturity: int,
            latest_f_time: int
    ) -> AMMState:
        """
        Calculate initial AMM state during seeding

        This is called once when the AMM is first created.

        The initial state sets:
        - totalFloatAmount = initialSize + flipLiquidity
        - normFixedAmount = totalFloatAmount * initialAbsRate
        - totalLp = sqrt(totalFloatAmount * normFixedAmount)

        Args:
            params: Seeding parameters
            maturity: Market maturity timestamp
            latest_f_time: Current funding time

        Returns:
            Initial AMM state
        """
        # Calculate total floating amount (initial positions + buffer)
        total_float_amount = params.initial_size + params.flip_liquidity

        # Calculate normalized fixed amount (rate * float)
        norm_fixed_amount = PMath.mul_down(total_float_amount, params.initial_abs_rate)

        # Calculate initial LP tokens as geometric mean
        liquidity = PMath.sqrt(total_float_amount * norm_fixed_amount)

        # Calculate fixed value needed (rate * time)
        time_to_maturity = maturity - latest_f_time
        days_in_year = 365 * 24 * 60 * 60  # 365 days in seconds
        fixed_value = PMath.mul_down(
            norm_fixed_amount,
            (time_to_maturity * PMath.ONE) // days_in_year
        )

        # Ensure sufficient initial cash
        if params.initial_cash <= fixed_value:
            raise Errors.AMMInsufficientCashIn()

        return AMMState(
            total_float_amount=total_float_amount,
            norm_fixed_amount=norm_fixed_amount,
            total_lp=liquidity,
            latest_f_time=latest_f_time,
            maturity=maturity,
            seed_time=latest_f_time,
            min_abs_rate=params.min_abs_rate,
            max_abs_rate=params.max_abs_rate,
            cut_off_timestamp=params.cut_off_timestamp
        )

    @staticmethod
    def calc_mint_output(
            state: AMMState,
            mark_rate: int,
            total_cash: int,
            total_size: int,
            max_cash_in: int,
            exact_size_in: int
    ) -> MintResult:
        """
        Calculate LP tokens to mint for adding liquidity

        This function determines how many LP tokens a user receives
        when adding liquidity to the AMM.

        Key logic:
        - If no positions exist (totalSize = 0): LP tokens = proportional to cash
        - If positions exist: LP tokens proportional to position size
        - Uses favorable rounding based on position direction

        Args:
            state: Current AMM state
            mark_rate: Current market oracle rate
            total_cash: Total cash in AMM
            total_size: Total position size in AMM
            max_cash_in: Maximum cash user愿意添加
            exact_size_in: Position size user wants to add (dL)

        Returns:
            MintResult with net cash in and LP tokens out
        """
        # Check market has not matured
        if state.maturity <= state.latest_f_time:
            raise Errors.MarketMatured()

        if total_cash <= 0:
            raise ValueError("Total cash must be positive")

        # Snap small positions to zero
        total_size = PositiveAMMMath._snap_small_size_to0(total_size)

        # Validate direction: liquidity must match position direction
        if PMath.sign(total_size) != PMath.sign(exact_size_in):
            raise Errors.AMMSignMismatch()

        # Case 1: No existing positions - use proportional calculation
        if total_size == 0:
            # LP = totalLp * cashIn / totalCash
            net_lp_out = PMath.mul_down(
                state.total_lp,
                max_cash_in // total_cash  # Simplified
            )
            return MintResult(net_cash_in=max_cash_in, net_lp_out=net_lp_out)

        # Case 2: Existing positions - use position-based calculation
        abs_total_size = PMath.abs(total_size)
        abs_exact_size_in = PMath.abs(exact_size_in)

        # Check if position direction matches market rate
        # If position is profitable (same sign as rate), use floor division
        is_position_profitable = PMath.sign(total_size) == PMath.sign(mark_rate)

        if is_position_profitable:
            # LP = totalLp * exactSizeIn / totalSize (floor division)
            net_lp_out = PMath.mul_down(
                state.total_lp,
                abs_exact_size_in // abs_total_size
            )
        else:
            # LP = totalLp * exactSizeIn / totalSize (ceiling division)
            net_lp_out = PMath.mul_up(
                state.total_lp * abs_exact_size_in,
                abs_total_size
            )

        # Calculate cash required (always favors AMM with ceiling)
        net_cash_in = PMath.mul_up(
            total_cash * net_lp_out,
            state.total_lp
        )

        if net_cash_in > max_cash_in:
            raise Errors.AMMInsufficientCashIn()

        return MintResult(net_cash_in=net_cash_in, net_lp_out=net_lp_out)

    @staticmethod
    def calc_burn_output(
            state: AMMState,
            mark_rate: int,
            total_cash: int,
            total_size: int,
            lp_to_burn: int
    ) -> BurnResult:
        """
        Calculate output when burning LP tokens

        Removes liquidity and returns proportional cash and position size.

        Args:
            state: Current AMM state
            mark_rate: Current market oracle rate
            total_cash: Total cash in AMM
            total_size: Total position size
            lp_to_burn: Amount of LP tokens to burn

        Returns:
            BurnResult with cash out, size out, and maturity status
        """
        # Calculate proportional cash out
        net_cash_out = PMath.mul_down(
            total_cash * lp_to_burn,
            state.total_lp
        )

        # Check if market has matured
        is_matured = state.maturity <= state.latest_f_time

        if is_matured:
            return BurnResult(
                net_cash_out=net_cash_out,
                net_size_out=0,
                is_matured=True
            )

        # Calculate position size to return
        total_size = PositiveAMMMath._snap_small_size_to0(total_size)
        abs_total_size = PMath.abs(total_size)

        # Determine rounding based on position profitability
        is_position_profitable = PMath.sign(total_size) == PMath.sign(mark_rate)

        if is_position_profitable:
            abs_size_out = PMath.mul_down(
                abs_total_size * lp_to_burn,
                state.total_lp
            )
        else:
            abs_size_out = PMath.mul_up(
                abs_total_size * lp_to_burn,
                state.total_lp
            )

        net_size_out = abs_size_out * PMath.sign(total_size)

        return BurnResult(
            net_cash_out=net_cash_out,
            net_size_out=net_size_out,
            is_matured=False
        )

    @staticmethod
    def calc_swap_output(state: AMMState, float_out: int) -> int:
        """
        Calculate fixed tokens required for a swap

        This is the core trading function. Users swap between
        fixed and floating rate tokens.

        Formula based on constant product invariant:
        L = F^t * N^(1-t)

        Where:
        - F = totalFloatAmount
        - N = normFixedAmount
        - t = normalized time
        - L = Liquidity invariant

        Args:
            state: Current AMM state
            float_out: Amount of float tokens to receive (positive) or give (negative)

        Returns:
            Amount of fixed tokens required (positive) or received (negative)
        """
        normalized_time = PositiveAMMMath._calc_normalized_time(state)

        # Handle float amount change
        float_out_abs = PMath.abs(float_out)

        if float_out > 0:
            # Receiving float tokens - decrease float amount
            if state.total_float_amount <= float_out_abs + 1:
                raise Errors.AMMInsufficientLiquidity()
            new_total_float_amount = state.total_float_amount - float_out_abs
        else:
            # Giving float tokens - increase float amount
            new_total_float_amount = state.total_float_amount + float_out_abs

        # Calculate new normFixedAmount using invariant
        liquidity = PMath.mul_down(
            PMath.pow(state.total_float_amount, normalized_time),
            state.norm_fixed_amount
        )

        new_norm_fixed_amount = PMath.div_down(
            liquidity,
            PMath.pow(new_total_float_amount, normalized_time)
        )

        # Validate rate bounds
        if new_norm_fixed_amount * PMath.ONE < state.min_abs_rate * new_total_float_amount:
            raise Errors.AMMInsufficientLiquidity()
        if new_norm_fixed_amount * PMath.ONE > state.max_abs_rate * new_total_float_amount:
            raise Errors.AMMInsufficientLiquidity()

        # Calculate fixed tokens in/out
        norm_fixed_in = new_norm_fixed_amount - state.norm_fixed_amount

        # Normalize by time
        fixed_in = PMath.div_down(norm_fixed_in, normalized_time)

        return fixed_in

    @staticmethod
    def calc_swap_size(state: AMMState, target_rate: int) -> int:
        """
        Calculate swap size to achieve a target rate

        Determines how many float tokens to swap to reach
        a specific exchange rate.

        Args:
            state: Current AMM state
            target_rate: Target exchange rate

        Returns:
            Amount of float tokens to swap
        """
        # Clamp target rate to valid range
        target_rate = PositiveAMMMath._clamp_rate(state, target_rate)
        target_rate_uint = PMath.uint(target_rate)

        normalized_time = PositiveAMMMath._calc_normalized_time(state)
        normalized_time_plus_one = normalized_time + PMath.ONE

        # Calculate new float amount for target rate
        liquidity_mul = PMath.mul_down(
            PMath.pow(state.total_float_amount, normalized_time),
            state.norm_fixed_amount
        )

        new_total_float_amount = PMath.pow(
            PMath.div_down(liquidity_mul, target_rate_uint),
            PMath.div_down(PMath.ONE, normalized_time_plus_one)
        )

        # Ensure minimum float amount
        new_total_float_amount = max(new_total_float_amount, 2)

        return state.total_float_amount - new_total_float_amount

    @staticmethod
    def _clamp_rate(state: AMMState, rate: int) -> int:
        """
        Clamp rate to valid bounds with tweak

        Applies slight adjustment to minimum/maximum rates.

        Args:
            state: Current AMM state
            rate: Input rate

        Returns:
            Clamped rate
        """
        adjusted_min, adjusted_max = PositiveAMMMath._tweak_rate(
            state.min_abs_rate,
            state.max_abs_rate
        )
        return max(adjusted_min, min(adjusted_max, rate))

    RATE_TWEAK_FACTOR = 10 ** 8

    @staticmethod
    def _tweak_rate(min_abs_rate: int, max_abs_rate: int) -> Tuple[int, int]:
        """
        Slightly adjust rate bounds

        The tweak factor prevents edge cases.

        Args:
            min_abs_rate: Original minimum rate
            max_abs_rate: Original maximum rate

        Returns:
            Tuple of (adjusted_min, adjusted_max)
        """
        adjusted_min = min_abs_rate + min_abs_rate // PositiveAMMMath.RATE_TWEAK_FACTOR
        adjusted_max = max_abs_rate - max_abs_rate // PositiveAMMMath.RATE_TWEAK_FACTOR
        return (adjusted_min, adjusted_max)

    @staticmethod
    def calc_implied_rate(total_float_amount: int, norm_fixed_amount: int) -> int:
        """
        Calculate the implied exchange rate

        Rate = normFixedAmount / totalFloatAmount

        Args:
            total_float_amount: Floating rate liquidity
            norm_fixed_amount: Normalized fixed rate liquidity

        Returns:
            Implied exchange rate
        """
        return PMath.div_down(norm_fixed_amount, total_float_amount)

    @staticmethod
    def _calc_normalized_time(state: AMMState) -> int:
        """
        Calculate normalized time (t)

        t = (maturity - latestFTime) / (maturity - seedTime)

        This represents the remaining time as a fraction of total period.

        Args:
            state: Current AMM state

        Returns:
            Normalized time (0 to 1)
        """
        if state.latest_f_time >= state.cut_off_timestamp:
            raise Errors.AMMCutOffReached()

        return PMath.div_down(
            state.maturity - state.latest_f_time,
            state.maturity - state.seed_time
        )


class PositiveAMM(AMM):


    def _swap(self, size_out: int) -> int:
        state = self._get_state()
        cost_out = PositiveAMMMath.calc_swap_output(state, size_out)
        return cost_out

    def _mint(self,
              total_cash: int,
              total_size: int,
              max_cash_in: int,
              exact_size_in: int) -> (int, int):
        mark_rate = self._get_mark_rate()
        result = PositiveAMMMath.calc_mint_output(
            self._get_state(),
            mark_rate,
            total_cash,
            total_size,
            max_cash_in,
            exact_size_in
        )
        return result.net_cash_in, result.net_lp_out

    def _burn(self,
              total_cash: int,
              total_size: int,
              lp_to_burn: int) -> (int, int):
        mark_rate = self._get_mark_rate()
        result = PositiveAMMMath.calc_burn_output(
            self._get_state(),
            mark_rate,
            total_cash,
            total_size,
            lp_to_burn
        )
        return result.net_cash_out, result.net_size_out


class NegativeAMMMath:
    """
    Math library for Negative AMM calculations

    This class delegates to PositiveAMMMath with sign inversions.

    The key insight is that the Negative AMM is the mathematical inverse
    of the Positive AMM. By negating all rate and size inputs/outputs,
    we can reuse the same math formulas while maintaining separate pools.

    For example:
    - If PositiveAMM has a "long" position, NegativeAMM has a "short" position
    - If PositiveAMM receives fixed tokens when selling float,
      NegativeAMM pays fixed tokens when selling float
    """

    ONE = PMath.ONE

    @staticmethod
    def calc_seed_output(
            params: AMMSeedParams,
            maturity: int,
            latest_f_time: int
    ) -> AMMState:
        """
        Calculate initial AMM state for Negative AMM

        The only difference from PositiveAMM is that initialSize is negated.
        This creates the initial "short" bias in the AMM.

        Args:
            params: Seeding parameters (initialSize will be negated)
            maturity: Market maturity timestamp
            latest_f_time: Current funding time

        Returns:
            Initial AMM state for Negative AMM
        """
        # Negate initial size for Negative AMM
        params.initial_size = -params.initial_size

        # Delegate to PositiveAMMMath
        return PositiveAMMMath.calc_seed_output(params, maturity, latest_f_time)

    @staticmethod
    def calc_mint_output(
            state: AMMState,
            mark_rate: int,
            total_cash: int,
            total_size: int,
            max_cash_in: int,
            exact_size_in: int
    ) -> MintResult:
        """
        Calculate LP tokens for adding liquidity to Negative AMM

        All rate and size parameters are negated before delegation.

        Args:
            state: Current AMM state
            mark_rate: Market oracle rate (will be negated)
            total_cash: Total cash in AMM
            total_size: Total position size (will be negated)
            max_cash_in: Maximum cash to add
            exact_size_in: Position size to add (will be negated)

        Returns:
            MintResult with net cash in and LP tokens out
        """
        # Negate all rate/size inputs
        neg_mark_rate = -mark_rate
        neg_total_size = -total_size
        neg_exact_size_in = -exact_size_in

        # Delegate to PositiveAMMMath with negated values
        return PositiveAMMMath.calc_mint_output(
            state,
            neg_mark_rate,
            total_cash,
            neg_total_size,
            max_cash_in,
            neg_exact_size_in
        )

    @staticmethod
    def calc_burn_output(
            state: AMMState,
            mark_rate: int,
            total_cash: int,
            total_size: int,
            lp_to_burn: int
    ) -> BurnResult:
        """
        Calculate output when burning LP tokens from Negative AMM

        Negates inputs and then negates netSizeOut to restore correct sign.

        Args:
            state: Current AMM state
            mark_rate: Market oracle rate (will be negated)
            total_cash: Total cash in AMM
            total_size: Total position size (will be negated)
            lp_to_burn: Amount of LP tokens to burn

        Returns:
            BurnResult with cash out, size out, and maturity status
        """
        # Negate inputs
        neg_mark_rate = -mark_rate
        neg_total_size = -total_size

        # Delegate to PositiveAMMMath
        result = PositiveAMMMath.calc_burn_output(
            state,
            neg_mark_rate,
            total_cash,
            neg_total_size,
            lp_to_burn
        )

        # Negate netSizeOut to restore correct sign for Negative AMM
        return BurnResult(
            net_cash_out=result.net_cash_out,
            net_size_out=-result.net_size_out,
            is_matured=result.is_matured
        )

    @staticmethod
    def calc_swap_output(state: AMMState, float_out: int) -> int:
        """
        Calculate fixed tokens for a swap in Negative AMM

        Negates floatOut before delegation.

        Args:
            state: Current AMM state
            float_out: Amount of float tokens (will be negated)

        Returns:
            Fixed tokens required (will be positive when giving float)
        """
        # Negate floatOut for Negative AMM
        neg_float_out = -float_out

        # Delegate to PositiveAMMMath
        return PositiveAMMMath.calc_swap_output(state, neg_float_out)

    @staticmethod
    def calc_swap_size(state: AMMState, target_rate: int) -> int:
        """
        Calculate swap size to achieve target rate in Negative AMM

        Negates targetRate before delegation, then negates result.

        Args:
            state: Current AMM state
            target_rate: Target exchange rate (will be negated)

        Returns:
            Float tokens to swap (negated result)
        """
        # Negate target rate for Negative AMM
        neg_target_rate = -target_rate

        # Delegate to PositiveAMMMath and negate result
        return -PositiveAMMMath.calc_swap_size(state, neg_target_rate)

    @staticmethod
    def calc_implied_rate(total_float_amount: int, norm_fixed_amount: int) -> int:
        """
        Calculate the implied exchange rate for Negative AMM

        The rate is the negative of PositiveAMM's rate.

        Args:
            total_float_amount: Floating rate liquidity
            norm_fixed_amount: Normalized fixed rate liquidity

        Returns:
            Implied exchange rate (negative of PositiveAMM)
        """
        # Return negative of PositiveAMM's rate
        return -PositiveAMMMath.calc_implied_rate(
            total_float_amount,
            norm_fixed_amount
        )

class NegativeAMM(AMM):
    def _swap(self, size_out: int) -> int:
        state = self._get_state()
        cost_out = NegativeAMMMath.calc_swap_output(state, size_out)
        return cost_out

    def _mint(self,
              total_cash: int,
              total_size: int,
              max_cash_in: int,
              exact_size_in: int) -> (int, int):
        mark_rate = self._get_mark_rate()

        # Calculate mint output using math library
        result = NegativeAMMMath.calc_mint_output(
            self._get_state(),
            mark_rate,
            total_cash,
            total_size,
            max_cash_in,
            exact_size_in
        )
        return result.net_cash_in, result.net_lp_out

    def _burn(self,
              total_cash: int,
              total_size: int,
              lp_to_burn: int) -> (int, int):
        mark_rate = self._get_mark_rate()
        result = NegativeAMMMath.calc_burn_output(
            self._get_state(),
            mark_rate,
            total_cash,
            total_size,
            lp_to_burn
        )
        return result.net_cash_out, result.net_size_out
