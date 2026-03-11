from collections import deque
from decimal import Decimal
from enum import Enum

from .. import Snapshot
from ..strategy import Strategy
from .market import BorosMarket, FixedFloatDirection


class BorosExecutionMode(Enum):
    BAR_APPROX = "bar_approx"
    NEXT_TRADE = "next_trade"


class SimpleFixedFloatStrategy(Strategy):
    def __init__(
        self,
        notional: Decimal,
        lookback: int = 60,
        entry_threshold: Decimal = Decimal("0.002"),
        exit_threshold: Decimal = Decimal("0.0005"),
        stop_loss: Decimal | None = None,
        execution_mode: BorosExecutionMode = BorosExecutionMode.BAR_APPROX,
    ):
        super().__init__()
        self.notional = Decimal(notional)
        self.lookback = int(lookback)
        self.entry_threshold = Decimal(entry_threshold)
        self.exit_threshold = Decimal(exit_threshold)
        self.stop_loss = Decimal(stop_loss) if stop_loss is not None else self.notional * Decimal("0.01")
        self.execution_mode = execution_mode
        self._mark_window: deque[Decimal] = deque(maxlen=self.lookback)

    @property
    def market(self) -> BorosMarket:
        return self.broker.markets.default

    def _reference_rate(self) -> Decimal | None:
        if len(self._mark_window) < self.lookback:
            return None
        return sum(self._mark_window, Decimal(0)) / Decimal(len(self._mark_window))

    def _signal_rate(self, snapshot: Snapshot) -> Decimal | None:
        current_mark_rate = self.market.market_status.data["mark_rate"]
        if self.execution_mode == BorosExecutionMode.BAR_APPROX:
            return current_mark_rate
        current_minute = snapshot.timestamp.floor("1min")
        tx_rows = self.market.tx_ledger.loc[self.market.tx_ledger["minute"] == current_minute]
        if len(tx_rows.index) == 0:
            return None
        return tx_rows.iloc[-1]["trade_rate_vwap"]

    def on_bar(self, snapshot: Snapshot):
        current_mark_rate = self.market.market_status.data["mark_rate"]
        self._mark_window.append(current_mark_rate)
        reference_rate = self._reference_rate()
        if reference_rate is None:
            return

        spread = current_mark_rate - reference_rate
        open_positions = self.market.get_open_positions()

        if len(open_positions) == 0:
            execution_rate = self._signal_rate(snapshot)
            if execution_rate is None:
                return
            if spread >= self.entry_threshold:
                self.market.open_fixed_float(self.notional, FixedFloatDirection.PAY_FIXED, fixed_rate=execution_rate)
            elif spread <= -self.entry_threshold:
                self.market.open_fixed_float(self.notional, FixedFloatDirection.RECEIVE_FIXED, fixed_rate=execution_rate)
            return

        balance = self.market.get_market_balance()
        if abs(spread) <= self.exit_threshold or balance.unrealized_pnl <= -self.stop_loss:
            self.market.close_position(close_reason="signal")
