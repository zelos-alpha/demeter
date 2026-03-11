from ._typing import Side, TimeInForce, LongShort
from CoreStateUtils import CoreStateUtils

ONE = 10**18  # WAD precision
MAIN_ACCOUNT_ID = 0
AMM_ACCOUNT_ID = 255


class PayFee(object):
    """
    Payment and fee structure.

    Packed as: payment (128 bits) | fees (128 bits)
    """

    def __init__(self, payment=0, fees=0):
        self.payment = payment
        self.fees = fees

    @classmethod
    def ZERO(cls):
        return cls(0, 0)

    @classmethod
    def from_pack(cls, packed):
        """Unpack a single uint256 value"""
        payment = (packed >> 128) & ((1 << 128) - 1)
        fees = packed & ((1 << 128) - 1)
        return cls(int(payment), int(fees))

    def pack(self):
        """Pack into a single uint256 value"""
        return (self.payment << 128) | self.fees

    def is_zero(self):
        return self.payment == 0 and self.fees == 0

    def fee(self):
        """Get fee amount"""
        return self.fees

    def __add__(self, other):
        return PayFee(self.payment + other.payment, self.fees + other.fees)

    def __repr__(self):
        return "PayFee(payment=%s, fees=%s)" % (self.payment, self.fees)


class Trade(object):
    """Trade represents a fill"""

    def __init__(self, raw_val=0):
        self.raw_val = raw_val

    @classmethod
    def ZERO(cls):
        return cls(0)

    def is_zero(self):
        return self.raw_val == 0

    def __repr__(self):
        return "Trade(%s)" % self.raw_val


class VMResult(object):
    """
    Value and Margin result for margin calculations.

    Packed as: value (128 bits) | margin (128 bits)
    value can be negative (int128)
    """

    def __init__(self, value=0, margin=0):
        self.value = value
        self.margin = margin

    @classmethod
    def ZERO(cls):
        return cls(0, 0)

    @classmethod
    def from_pack(cls, packed):
        """Unpack a single uint256 value"""
        value = (packed >> 128) & ((1 << 128) - 1)
        margin = packed & ((1 << 128) - 1)
        # Convert value to signed int128
        if value >= (1 << 127):
            value = value - (1 << 128)
        return cls(int(value), int(margin))

    def pack(self):
        """Pack into a single uint256 value"""
        # Handle negative values
        value = self.value
        if value < 0:
            value = value + (1 << 128)
        return (value << 128) | self.margin

    def __add__(self, other):
        return VMResult(self.value + other.value, self.margin + other.margin)

    def __repr__(self):
        return "VMResult(value=%s, margin=%s)" % (self.value, self.margin)

class CLOCheck:
    NO = 0
    YES = 1


class GetRequest:
    IM = 0
    MM = 1
    ZERO = 2

class MarketAcc(object):
    """
    Market account identifier that packs:
    - address (160 bits)
    - accountId (8 bits)
    - tokenId (16 bits)
    - marketId (24 bits)
    Total: 208 bits
    """

    def __init__(self, root="0x0000000000000000000000000000000000000000",
                 account_id=0, token_id=0, market_id=0):
        self.root = root
        self.account_id = account_id
        self.token_id = token_id
        self.market_id = market_id

    @classmethod
    def ZERO(cls):
        return cls()

    @classmethod
    def from_address(cls, addr):
        """Create from Ethereum address"""
        return cls(root=addr)

    def is_zero(self):
        return self.root == "0x0000000000000000000000000000000000000000"

    def is_cross(self):
        """Check if this is a cross-margin account"""
        return self.market_id == (2 ** 24 - 1)  # CROSS = type(uint24).max

    def root_address(self):
        return self.root

    def is_main(self):
        return self.account_id == MAIN_ACCOUNT_ID

    def is_amm(self):
        return self.account_id == AMM_ACCOUNT_ID

    def __eq__(self, other):
        if not isinstance(other, MarketAcc):
            return False
        return (self.root == other.root and
                self.account_id == other.account_id and
                self.token_id == other.token_id and
                self.market_id == other.market_id)

    def __repr__(self):
        return "MarketAcc(root=%s, account_id=%d, token_id=%d, market_id=%d)" % (
            self.root[:10] + "...", self.account_id, self.token_id, self.market_id)

class UserResult(object):
    """Result of user order processing"""
    def __init__(self):
        self.settle = PayFee.ZERO()  # Settlement payment
        self.payment = PayFee.ZERO()  # Payment for orders
        self.removed_ids = []  # Removed order IDs
        self.book_matched = Trade.ZERO()  # Book matched trade
        self.partial_maker = MarketAcc.ZERO()  # Partial maker
        self.partial_pay_fee = PayFee.ZERO()  # Partial payment/fee
        self.is_strict_im = False  # Strict IM check
        self.final_vm = VMResult.ZERO()  # Final VM result (IM if isStrictIM, else MM)

    def __repr__(self):
        return "UserResult(settle=%s, payment=%s, removed_ids=%s, book_matched=%s, is_strict_im=%s)" % (
            self.settle, self.payment, len(self.removed_ids), self.book_matched, self.is_strict_im)


class OrderBook(object):
    """Simplified order book"""

    def __init__(self):
        self.bids = []  # Buy orders [(size, tick), ...]
        self.asks = []  # Sell orders [(size, tick), ...]

    def add_bid(self, size, tick):
        """Add a bid order"""
        self.bids.append({'size': size, 'tick': tick})
        self.bids.sort(key=lambda x: x['tick'], reverse=True)  # Best bid first

    def add_ask(self, size, tick):
        """Add an ask order"""
        self.asks.append({'size': size, 'tick': tick})
        self.asks.sort(key=lambda x: x['tick'])  # Best ask first


class MarketOracle(object):
    """Simplified market oracle for price feeds"""

    def __init__(self):
        self.price = ONE  # Initial price

    def get_price(self):
        return self.price

class UserMem(object):
    """In-memory user state during order processing"""

    def __init__(self, addr=MarketAcc.ZERO()):
        self.addr = addr
        self.cash = 1000000 * ONE  # Initial cash for demo
        self.long_ids = []
        self.short_ids = []
        self.position = None  # Position data

    def __repr__(self):
        return "UserMem(addr=%s, cash=%s, long_ids=%d, short_ids=%d)" % (
            self.addr, self.cash, len(self.long_ids), len(self.short_ids))


class MarketMem(object):
    """In-memory market state during order processing"""

    def __init__(self):
        self.k_tick_step = 0
        self.latest_ftag = 0
        self.r_mark = 0
        self.k_i_thresh = 0
        self.max_rate_deviation_factor_base1e4 = 0
        self.max_open_orders = 100

    def __repr__(self):
        return "MarketMem(k_tick_step=%s, r_mark=%s)" % (self.k_tick_step, self.r_mark)


class OrderId(object):
    """Order identifier"""

    def __init__(self, value=0):
        self.value = value

    @classmethod
    def ZERO(cls):
        return cls(0)

    def is_zero(self):
        return self.value == 0

    def tick_index(self):
        """Extract tick index from order ID"""
        return (self.value >> 40) & 0xFFFF

    def __repr__(self):
        return "OrderId(%s)" % hex(self.value)


class OTCResult(object):
    """Result of OTC processing"""

    def __init__(self):
        self.settle = PayFee.ZERO()  # Settlement
        self.payment = PayFee.ZERO()  # Payment
        self.is_strict_im = False  # Strict IM check
        self.final_vm = VMResult.ZERO()  # Final VM result

    def __repr__(self):
        return "OTCResult(settle=%s, payment=%s, is_strict_im=%s)" % (
            self.settle, self.payment, self.is_strict_im)


class Market(CoreStateUtils):
    """Market contract"""
    def __init__(self, market_id):
        super().__init__()
        self.market_id = market_id
        self.address = "0x" + "0" * 40
        self.order_book = OrderBook()
        self.oracle = MarketOracle()
        self.treasury_cash = 0
        self.maturity = 0
        self.latest_f_time = 0
        self.is_isolated_only = False
        self.token_id = 0

        # Initialize market parameters
        self.k_tick_step = 100
        self.r_mark = ONE  # Mark rate
        self.k_i_thresh = ONE
        self.max_rate_deviation_factor_base1e4 = ONE // 100  # 1%

    def order_and_otc(self, user_addr, orders, cancel_data, otcs, crit_hr):
        """
        Process orders and OTC trades within the market.

        This is the main order processing function that handles:
        1. Order validation
        2. User initialization
        3. Order cancellation
        4. Order matching
        5. Order placement on book
        6. OTC processing
        7. State writing and margin checks
        """

        # Phase 0: Validate orders and OTCs
        self._validate_order_and_otc(user_addr, orders, otcs)

        # Phase 1: Read market & user state
        market = self._read_market()
        user, user_settle = self._init_user(user_addr, market)

        # Initialize result
        res = UserResult()
        res.settle = user_settle

        # Phase 2: Remove orders
        res.removed_ids = self._core_remove_aft(market, user, cancel_data, False)
        print("  [Phase 2] Cancelled %d orders" % len(res.removed_ids))

        # Phase 3: Match orders & place on book
        self._match_order(market, user, orders, res)
        self._core_add(market, user, orders, res.book_matched)
        print("  [Phase 3] Order matching completed, book_matched=%s" % res.book_matched)

        # Phase 4: OTC trades
        otc_res = []
        if len(otcs) > 0:
            otc_res = self._otc(user, otcs, res, market, crit_hr)
            print("  [Phase 4] Processed %d OTC trades" % len(otcs))

        # Phase 5: Write state and calculate margin
        res.is_strict_im, res.final_vm = self._write_user(user, market, res.payment, orders, crit_hr, CLOCheck.YES)
        self._write_market(market)
        print("  [Phase 5] State written, isStrictIM=%s" % res.is_strict_im)

        return (res, otc_res)

    def _validate_order_and_otc(self, user, orders, otcs):
        """Validate orders and OTC trades"""
        # Validate orders - sizes must match limit_ticks length
        assert len(orders.sizes) == len(orders.limit_ticks), "InvalidLength"

        # Validate no zero sizes
        for size in orders.sizes:
            assert size != 0, "MarketZeroSize"

        # Validate OTCs - no self-trading
        for i, otc in enumerate(otcs):
            assert otc.counter != user, "MarketSelfSwap"
            # No duplicate counterparties
            for j in range(i + 1, len(otcs)):
                assert otc.counter != otcs[j].counter, "MarketDuplicateOTC"

    def _read_market(self):
        """Read current market state"""
        market = MarketMem()
        market.k_tick_step = self.k_tick_step
        market.latest_ftag = 0
        market.r_mark = self.r_mark
        market.k_i_thresh = self.k_i_thresh
        market.max_rate_deviation_factor_base1e4 = self.max_rate_deviation_factor_base1e4
        market.max_open_orders = 100
        return market

    # def _init_user(self, user_addr, market):
    #     """Initialize user state"""
    #     user = UserMem(user_addr)
    #     # In a real implementation, this would load from storage
    #     user.cash = 1000000 * ONE
    #     return (user, PayFee.ZERO())

    # def _core_remove_aft(self, market, user, cancel_data, is_forced):
    #     """Remove orders from the book"""
    #     if cancel_data.is_all:
    #         # Remove all orders
    #         removed_long = list(user.long_ids)
    #         removed_short = list(user.short_ids)
    #         user.long_ids = []
    #         user.short_ids = []
    #         return removed_long + removed_short
    #
    #     # Remove specific orders
    #     removed = []
    #     for order_id in cancel_data.ids:
    #         # Check if in long or short
    #         found = False
    #         if order_id in user.long_ids:
    #             user.long_ids.remove(order_id)
    #             removed.append(order_id)
    #             found = True
    #         elif order_id in user.short_ids:
    #             user.short_ids.remove(order_id)
    #             removed.append(order_id)
    #             found = True
    #
    #         if not found and cancel_data.is_strict:
    #             raise Exception("MarketOrderNotFound")
    #
    #     return removed

    def _match_order(self, market: MarketMem, user:UserMem, orders: LongShort, res: UserResult):
        """
        Match orders against the order book.

        This function:
        1. Calls _bookMatch to find matching orders
        2. Validates no self-trade occurred
        3. Validates rate deviation
        4. Updates implied rate
        5. Calculates payment
        6. Handles partial fills
        """
        if orders.is_empty() or len(orders.sizes) == 0:  # todo
            return

        # Simplified book matching
        book_matched, partial_fill, partial_maker, last_matched_tick, last_matched_rate = \
            self._book_match(market.k_tick_step, market.latest_ftag, orders)

        if book_matched.is_zero():
            return

        # Check for self-fill after match
        has_self_fill = self._has_self_filled_after_match(
            user, partial_maker, orders.side, last_matched_tick
        )
        assert not has_self_fill, "MarketSelfSwap"

        # Check rate deviation
        is_valid_rate = self._check_rate_deviation(last_matched_rate, market)
        assert is_valid_rate, "MarketLastTradedRateTooFar"

        # Update implied rate
        self._update_implied_rate(last_matched_tick, market.k_tick_step)

        # Store results
        res.book_matched = book_matched
        res.partial_maker = partial_maker

        # Calculate payment
        res.payment = self._merge_new_match_aft(user, market, book_matched)
        print("    [Match] book_matched=%s, payment=%s" % (book_matched, res.payment))

        # Handle partial fill
        if partial_fill.is_zero():
            return

        # Simplified partial fill handling
        print("    [Match] Partial fill detected")

    def _book_match(self, tick_step, latest_ftag, orders):
        """
        Match orders against the order book.

        Returns:
            book_matched: Total matched trade
            partial_fill: Any partial fill information
            partial_maker: Maker account for partial fill
            last_matched_tick: Last tick index matched
            last_matched_rate: Last matched rate
        """
        # Simplified matching - in reality this is a complex algorithm
        if len(orders.sizes) == 0:
            return (Trade.ZERO(), Trade.ZERO(), MarketAcc.ZERO(), 0, 0)

        # Calculate total order size
        total_size = sum(orders.sizes)

        # Check if there are matching orders on the opposite side
        if orders.side == Side.LONG and len(self.order_book.asks) > 0:
            # Match with best ask
            best_ask = self.order_book.asks[0]
            matched_size = min(total_size, best_ask.get('size', 0))
            if matched_size > 0:
                book_matched = Trade(matched_size)
                last_matched_tick = best_ask.get('tick', 0)
                last_matched_rate = self._tick_to_rate(last_matched_tick, self.k_tick_step)
                return (book_matched, Trade.ZERO(), MarketAcc.ZERO(), last_matched_tick, last_matched_rate)
        elif orders.side == Side.SHORT and len(self.order_book.bids) > 0:
            # Match with best bid
            best_bid = self.order_book.bids[0]
            matched_size = min(total_size, best_bid.get('size', 0))
            if matched_size > 0:
                book_matched = Trade(matched_size)
                last_matched_tick = best_bid.get('tick', 0)
                last_matched_rate = self._tick_to_rate(last_matched_tick, self.k_tick_step)
                return (book_matched, Trade.ZERO(), MarketAcc.ZERO(), last_matched_tick, last_matched_rate)

        # No match found
        return (Trade.ZERO(), Trade.ZERO(), MarketAcc.ZERO(), 0, 0)

    def _has_self_filled_after_match(self, user, partial_maker, order_side, last_matched_tick):
        """
        Check if user has self-filled after the match.

        This prevents users from matching with their own orders on the book.
        """
        if partial_maker == user.addr or partial_maker.is_zero():
            return True

        # Check if user's best order on the opposite side could have been filled
        matching_side = Side.SHORT if order_side == Side.LONG else Side.LONG

        if matching_side == Side.LONG and len(user.long_ids) > 0:
            best_long = user.long_ids[-1]
            # Check if this order could have been filled at last_matched_tick
            can_fill = best_long.tick_index() >= last_matched_tick
            if can_fill:
                return True

        if matching_side == Side.SHORT and len(user.short_ids) > 0:
            best_short = user.short_ids[-1]
            # Check if this order could have been filled at last_matched_tick
            can_fill = best_short.tick_index() <= last_matched_tick
            if can_fill:
                return True

        return False

    def _check_rate_deviation(self, last_matched_rate, market):
        """
        Check if the last matched rate is within acceptable deviation
        from the current mark rate.
        """
        if last_matched_rate == 0:
            return True

        mark_rate = market.r_mark
        deviation = abs(mark_rate - last_matched_rate)
        threshold = market.k_i_thresh * market.max_rate_deviation_factor_base1e4

        return deviation <= threshold

    def _update_implied_rate(self, last_matched_tick, tick_step):
        """Update the implied rate based on last matched trade"""
        if last_matched_tick != 0:
            self.implied_rate = self._tick_to_rate(last_matched_tick, tick_step)

    def _tick_to_rate(self, tick, tick_step):
        """Convert tick to rate"""
        return tick * tick_step * ONE // 10000

    def _merge_new_match_aft(self, user, market, book_matched):
        """
        Calculate payment for a new match.

        The payment includes:
        - Position change value
        - Trading fees
        """
        # Simplified payment calculation
        trade_value = book_matched.raw_val * market.r_mark // ONE
        fee = trade_value // 1000  # 0.1% fee

        # Payment is negative (user pays)
        payment = -int(trade_value)
        fees = fee

        return PayFee(payment, fees)

    def _core_add(self, market, user, orders, prev_matched):
        """
        Add orders to the order book.

        Logic for placing orders on book depends on TimeInForce:
        - GTC: Place if not fully matched
        - IOC: Never place (immediate execution only)
        - FOK: Require full match, never place
        - ALO: Require no partial fill, place if not fully matched
        - SOFT_ALO: Place if not fully matched
        """
        if not self._should_place_on_book(orders, prev_matched):
            print("  [CoreAdd] Order not placed on book (TIF=%s)" % orders.tif)
            return

        # Check max open orders
        total_orders = len(user.long_ids) + len(user.short_ids) + len(orders.sizes)
        assert total_orders <= market.max_open_orders, "MarketMaxOrdersExceeded"

        # Add orders to appropriate side
        if orders.side == Side.LONG:
            for size, tick in zip(orders.sizes, orders.limit_ticks):
                order_id = self._create_order_id(tick)
                user.long_ids.append(order_id)
                self.order_book.add_bid(size, tick)
                print("  [CoreAdd] Added LONG order: size=%s, tick=%s" % (size, tick))
        else:
            for size, tick in zip(orders.sizes, orders.limit_ticks):
                order_id = self._create_order_id(tick)
                user.short_ids.append(order_id)
                self.order_book.add_ask(size, tick)
                print("  [CoreAdd] Added SHORT order: size=%s, tick=%s" % (size, tick))

    def _should_place_on_book(self, orders, prev_matched):
        """Determine if orders should be placed on the book based on TIF"""
        tif = orders.tif
        has_matched_all = orders.is_empty()

        if tif == TimeInForce.GTC:
            return not has_matched_all
        elif tif == TimeInForce.IOC:
            return False
        elif tif == TimeInForce.FOK:
            assert has_matched_all, "MarketOrderFOKNotFilled"
            return False
        elif tif == TimeInForce.ALO:
            assert prev_matched.is_zero(), "MarketOrderALOFilled"
            return not has_matched_all
        elif tif == TimeInForce.SOFT_ALO:
            return not has_matched_all
        else:
            raise Exception("Unknown TIF")

    def _create_order_id(self, tick_index):
        """Create a new order ID"""
        # In reality, this would be more complex with nonce
        import time
        nonce = int(time.time() * 1000) % (1 << 40)
        return OrderId((nonce << 40) | (tick_index & 0xFFFF))

    def _otc(self, user, otcs, user_res, market, crit_hr):
        """
        Process OTC (Over-The-Counter) trades.

        OTC trades are direct trades between two parties without going through the order book.
        """
        otc_results = []

        for i, otc in enumerate(otcs):
            print("  [OTC %d] Processing: counter=%s, trade=%s, cash_to_counter=%s" % (
                i, otc.counter, otc.trade, otc.cash_to_counter))

            # Initialize counter user
            counter_user, counter_settle = self._init_user(otc.counter, market)

            # Create result for this OTC
            otc_res = OTCResult()
            otc_res.settle = counter_settle

            # Process OTC trade
            payment_user, payment_counter = self._merge_otc_aft(
                user, counter_user, market, otc.trade, otc.cash_to_counter, 0  # fee_rate
            )

            # Accumulate user payment
            user_res.payment = user_res.payment + payment_user
            otc_res.payment = payment_counter

            print("    [OTC %d] User payment: %s, Counter payment: %s" % (
                i, payment_user, payment_counter))

            # Write counter user state and check margin
            otc_res.is_strict_im, otc_res.final_vm = self._write_user(
                counter_user, market, otc_res.payment, LongShort(), crit_hr, CLOCheck.YES
            )

            otc_results.append(otc_res)

        return otc_results

    def _merge_otc_aft(self, user, counter, market, trade, cash_to_counter, fee_rate):
        """
        Process OTC trade and calculate payments.

        Returns:
            payment_user: Payment for the main user
            payment_counter: Payment for the counterparty
        """
        # OTC trade value
        trade_value = trade.raw_val * market.r_mark // ONE
        fee = trade_value * fee_rate // ONE

        # User pays/receives based on cash_to_counter
        user_payment = -trade_value + int(cash_to_counter)
        counter_payment = trade_value - int(cash_to_counter)

        # Fees
        user_fee = fee
        counter_fee = 0

        return (
            PayFee(user_payment, user_fee),
            PayFee(counter_payment, counter_fee)
        )

    def _write_user(self, user, market, payment, orders, crit_hr, clo_check):
        """
        Write user state and perform margin check.

        Returns:
            is_strict_im: Whether strict IM check is required
            final_vm: Final VM result for margin calculation
        """
        # Calculate position and margin
        position_value = payment.payment
        margin_required = abs(position_value) // 10  # Simplified margin calculation

        is_strict_im = margin_required > crit_hr if crit_hr > 0 else False
        final_vm = VMResult(position_value, margin_required)

        # In reality, this would write to storage
        print("    [WriteUser] position_value=%s, margin=%s, isStrictIM=%s" % (
            position_value, margin_required, is_strict_im))

        return (is_strict_im, final_vm)

    def _write_market(self, market):
        """Write market state to storage"""
        pass  # Simplified

    def settle_and_get(self, user, req):
        """
        Settle user position and get VM result.

        This is called during margin checks and position updates.
        """
        return (VMResult.ZERO(), PayFee.ZERO(), 0, 0)