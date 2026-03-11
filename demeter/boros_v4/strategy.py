from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

import pandas as pd

from .. import MarketInfo, Snapshot
from ..strategy import Strategy
from .market import BorosMarket, FixedFloatDirection


class BorosExecutionMode(Enum):
    BAR_APPROX = "bar_approx"
    NEXT_TRADE = "next_trade"
    TX_REPLAY_BEST_EXEC = "tx_replay_best_exec"


@dataclass
class SpreadPosition:
    position_id_a: int
    position_id_b: int


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

    def _current_minute_trade_rate(self, snapshot: Snapshot) -> Decimal | None:
        current_minute = snapshot.timestamp.floor("1min")
        tx_rows = self.market.tx_ledger.loc[self.market.tx_ledger["minute"] == current_minute]
        if len(tx_rows.index) == 0:
            return None
        column = "trade_rate_vwap" if "trade_rate_vwap" in tx_rows.columns else "implied_rate"
        return tx_rows.iloc[-1][column]

    def _claim_execution(self, snapshot: Snapshot):
        if self.execution_mode == BorosExecutionMode.BAR_APPROX:
            return None
        if self.execution_mode == BorosExecutionMode.NEXT_TRADE:
            execution_rate = self._current_minute_trade_rate(snapshot)
            if execution_rate is None:
                return None
            return {
                "fixed_rate": execution_rate,
                "execution_fee_paid": Decimal(0),
                "execution_timestamp": snapshot.timestamp.to_pydatetime(),
                "execution_tx_hash": "",
                "execution_source": "minute_trade",
            }
        row = self.market.claim_next_replay_execution(snapshot.timestamp)
        if row is None:
            return None
        return {
            "fixed_rate": row.implied_rate,
            "execution_fee_paid": row.fee_paid,
            "execution_timestamp": row.timestamp.to_pydatetime(),
            "execution_tx_hash": row.tx_hash,
            "execution_source": row.source_kind,
        }

    def on_bar(self, snapshot: Snapshot):
        current_mark_rate = self.market.market_status.data["mark_rate"]
        self._mark_window.append(current_mark_rate)
        reference_rate = self._reference_rate()
        if reference_rate is None:
            return

        spread = current_mark_rate - reference_rate
        open_positions = self.market.get_open_positions()

        if len(open_positions) == 0:
            execution = self._claim_execution(snapshot)
            if self.execution_mode != BorosExecutionMode.BAR_APPROX and execution is None:
                return
            if spread >= self.entry_threshold:
                self.market.open_fixed_float(
                    self.notional,
                    FixedFloatDirection.PAY_FIXED,
                    fixed_rate=current_mark_rate if execution is None else execution["fixed_rate"],
                    execution_fee_paid=Decimal(0) if execution is None else execution["execution_fee_paid"],
                    execution_timestamp=None if execution is None else execution["execution_timestamp"],
                    execution_tx_hash="" if execution is None else execution["execution_tx_hash"],
                    execution_source="" if execution is None else execution["execution_source"],
                )
            elif spread <= -self.entry_threshold:
                self.market.open_fixed_float(
                    self.notional,
                    FixedFloatDirection.RECEIVE_FIXED,
                    fixed_rate=current_mark_rate if execution is None else execution["fixed_rate"],
                    execution_fee_paid=Decimal(0) if execution is None else execution["execution_fee_paid"],
                    execution_timestamp=None if execution is None else execution["execution_timestamp"],
                    execution_tx_hash="" if execution is None else execution["execution_tx_hash"],
                    execution_source="" if execution is None else execution["execution_source"],
                )
            return

        balance = self.market.get_market_balance()
        if abs(spread) <= self.exit_threshold or balance.unrealized_pnl <= -self.stop_loss:
            execution = self._claim_execution(snapshot)
            self.market.close_position(
                close_reason="signal",
                execution_fee_paid=Decimal(0) if execution is None else execution["execution_fee_paid"],
                execution_timestamp=None if execution is None else execution["execution_timestamp"],
                execution_tx_hash="" if execution is None else execution["execution_tx_hash"],
                execution_source="" if execution is None else execution["execution_source"],
                close_rate=None if execution is None else execution["fixed_rate"],
            )


class FundingConvergenceStrategy(Strategy):
    def __init__(
        self,
        market_a_info: MarketInfo,
        market_b_info: MarketInfo,
        notional: Decimal,
        lookback: int = 60,
        entry_threshold: Decimal = Decimal("0.003"),
        exit_threshold: Decimal = Decimal("0.0008"),
        stop_loss: Decimal | None = None,
        execution_mode: BorosExecutionMode = BorosExecutionMode.TX_REPLAY_BEST_EXEC,
        min_time_to_maturity_seconds: int = 24 * 3600,
        max_signal_rate: Decimal = Decimal("2"),
        expected_holding_seconds: int | None = None,
        min_expected_edge_after_cost: Decimal = Decimal("0"),
        max_execution_delay_seconds: int | None = None,
        max_pair_execution_skew_seconds: int | None = None,
    ):
        super().__init__()
        self.market_a_info = market_a_info
        self.market_b_info = market_b_info
        self.notional = Decimal(notional)
        self.lookback = int(lookback)
        self.entry_threshold = Decimal(entry_threshold)
        self.exit_threshold = Decimal(exit_threshold)
        self.stop_loss = Decimal(stop_loss) if stop_loss is not None else self.notional * Decimal("0.02")
        self.execution_mode = execution_mode
        self.min_time_to_maturity_seconds = int(min_time_to_maturity_seconds)
        self.max_signal_rate = Decimal(max_signal_rate)
        self.expected_holding_seconds = (
            max(3600, int(expected_holding_seconds))
            if expected_holding_seconds is not None
            else max(3600, self.lookback * 60)
        )
        self.min_expected_edge_after_cost = Decimal(min_expected_edge_after_cost)
        self.max_execution_delay_seconds = (
            None if max_execution_delay_seconds is None else max(0, int(max_execution_delay_seconds))
        )
        self.max_pair_execution_skew_seconds = (
            None if max_pair_execution_skew_seconds is None else max(0, int(max_pair_execution_skew_seconds))
        )
        self._spread_window: deque[Decimal] = deque(maxlen=self.lookback)
        self._spread_position: SpreadPosition | None = None
        self.spread_history: list[dict] = []

    @property
    def market_a(self) -> BorosMarket:
        return self.broker.markets[self.market_a_info]

    @property
    def market_b(self) -> BorosMarket:
        return self.broker.markets[self.market_b_info]

    def _reference_spread(self) -> Decimal | None:
        if len(self._spread_window) < self.lookback:
            return None
        return sum(self._spread_window, Decimal(0)) / Decimal(len(self._spread_window))

    def _pair_execution(self, snapshot: Snapshot, consume: bool = True):
        if self.execution_mode == BorosExecutionMode.BAR_APPROX:
            return (
                {"fixed_rate": self.market_a.market_status.data["mark_rate"], "execution_timestamp": None, "execution_tx_hash": "", "execution_source": "", "execution_fee_paid": Decimal(0)},
                {"fixed_rate": self.market_b.market_status.data["mark_rate"], "execution_timestamp": None, "execution_tx_hash": "", "execution_source": "", "execution_fee_paid": Decimal(0)},
            )
        if self.execution_mode == BorosExecutionMode.NEXT_TRADE:
            current_minute = snapshot.timestamp.floor("1min")
            rows_a = self.market_a.tx_ledger.loc[self.market_a.tx_ledger["minute"] == current_minute]
            rows_b = self.market_b.tx_ledger.loc[self.market_b.tx_ledger["minute"] == current_minute]
            if len(rows_a.index) == 0 or len(rows_b.index) == 0:
                return None
            row_a = rows_a.iloc[-1]
            row_b = rows_b.iloc[-1]
            return (
                {"fixed_rate": row_a["trade_rate_vwap"], "execution_timestamp": snapshot.timestamp.to_pydatetime(), "execution_tx_hash": "", "execution_source": "minute_trade", "execution_fee_paid": row_a["fee_paid"] if "fee_paid" in row_a.index else Decimal(0)},
                {"fixed_rate": row_b["trade_rate_vwap"], "execution_timestamp": snapshot.timestamp.to_pydatetime(), "execution_tx_hash": "", "execution_source": "minute_trade", "execution_fee_paid": row_b["fee_paid"] if "fee_paid" in row_b.index else Decimal(0)},
            )

        row_a = self.market_a.peek_next_replay_execution(snapshot.timestamp)
        row_b = self.market_b.peek_next_replay_execution(snapshot.timestamp)
        if row_a is None or row_b is None:
            return None
        signal_ts = pd.Timestamp(snapshot.timestamp)
        if self.max_execution_delay_seconds is not None:
            max_delay = pd.Timedelta(seconds=self.max_execution_delay_seconds)
            if row_a.timestamp - signal_ts > max_delay or row_b.timestamp - signal_ts > max_delay:
                return None
        if self.max_pair_execution_skew_seconds is not None:
            max_skew = pd.Timedelta(seconds=self.max_pair_execution_skew_seconds)
            if abs(row_a.timestamp - row_b.timestamp) > max_skew:
                return None
        if consume:
            row_a = self.market_a.claim_next_replay_execution(snapshot.timestamp)
            row_b = self.market_b.claim_next_replay_execution(snapshot.timestamp)
        return (
            {
                "fixed_rate": row_a.implied_rate,
                "execution_fee_paid": row_a.fee_paid,
                "execution_timestamp": row_a.timestamp.to_pydatetime(),
                "execution_tx_hash": row_a.tx_hash,
                "execution_source": row_a.source_kind,
            },
            {
                "fixed_rate": row_b.implied_rate,
                "execution_fee_paid": row_b.fee_paid,
                "execution_timestamp": row_b.timestamp.to_pydatetime(),
                "execution_tx_hash": row_b.tx_hash,
                "execution_source": row_b.source_kind,
            },
        )

    def _open_spread(self, snapshot: Snapshot, spread: Decimal):
        execution = self._pair_execution(snapshot, consume=True)
        if execution is None:
            return
        exec_a, exec_b = execution
        if spread >= self.entry_threshold:
            pos_a = self.market_a.open_fixed_float(
                self.notional,
                FixedFloatDirection.PAY_FIXED,
                fixed_rate=exec_a["fixed_rate"],
                execution_fee_paid=exec_a["execution_fee_paid"],
                execution_timestamp=exec_a["execution_timestamp"],
                execution_tx_hash=exec_a["execution_tx_hash"],
                execution_source=exec_a["execution_source"],
            )
            pos_b = self.market_b.open_fixed_float(
                self.notional,
                FixedFloatDirection.RECEIVE_FIXED,
                fixed_rate=exec_b["fixed_rate"],
                execution_fee_paid=exec_b["execution_fee_paid"],
                execution_timestamp=exec_b["execution_timestamp"],
                execution_tx_hash=exec_b["execution_tx_hash"],
                execution_source=exec_b["execution_source"],
            )
        else:
            pos_a = self.market_a.open_fixed_float(
                self.notional,
                FixedFloatDirection.RECEIVE_FIXED,
                fixed_rate=exec_a["fixed_rate"],
                execution_fee_paid=exec_a["execution_fee_paid"],
                execution_timestamp=exec_a["execution_timestamp"],
                execution_tx_hash=exec_a["execution_tx_hash"],
                execution_source=exec_a["execution_source"],
            )
            pos_b = self.market_b.open_fixed_float(
                self.notional,
                FixedFloatDirection.PAY_FIXED,
                fixed_rate=exec_b["fixed_rate"],
                execution_fee_paid=exec_b["execution_fee_paid"],
                execution_timestamp=exec_b["execution_timestamp"],
                execution_tx_hash=exec_b["execution_tx_hash"],
                execution_source=exec_b["execution_source"],
            )
        self._spread_position = SpreadPosition(position_id_a=pos_a.position_id, position_id_b=pos_b.position_id)

    def _estimate_pair_edge_after_cost(
        self,
        spread_deviation: Decimal,
        time_to_mat_a: int,
        time_to_mat_b: int,
        execution: tuple[dict, dict] | None,
    ) -> tuple[Decimal, Decimal, Decimal]:
        effective_time_to_mat = Decimal(max(0, min(time_to_mat_a, time_to_mat_b)))
        effective_edge_rate = max(Decimal(0), abs(spread_deviation) - self.exit_threshold)
        gross_edge_value = (
            self.notional * effective_edge_rate * effective_time_to_mat / Decimal(365 * 24 * 3600)
        )

        market_rows = (
            (self.market_a, time_to_mat_a, None if execution is None else execution[0]),
            (self.market_b, time_to_mat_b, None if execution is None else execution[1]),
        )
        estimated_total_cost = Decimal(0)
        hold_seconds = Decimal(self.expected_holding_seconds)
        for market, time_to_mat, execution_row in market_rows:
            opening_fee = Decimal(0)
            if execution_row is not None:
                opening_fee += Decimal(execution_row["execution_fee_paid"])
            else:
                opening_fee_rate = Decimal(market.market_status.data.get("opening_fee_rate_annualized_proxy", Decimal(0)))
                opening_fee += self.notional * opening_fee_rate * Decimal(time_to_mat) / Decimal(365 * 24 * 3600)

            settlement_fee_rate = Decimal(
                market.market_status.data.get("settlement_fee_rate_annualized_actual", Decimal(0))
            )
            settlement_fee = self.notional * settlement_fee_rate * hold_seconds / Decimal(365 * 24 * 3600)
            estimated_total_cost += opening_fee + settlement_fee

        return gross_edge_value, estimated_total_cost, gross_edge_value - estimated_total_cost

    def _close_spread(self, snapshot: Snapshot, reason: str):
        if self._spread_position is None:
            return
        execution = self._pair_execution(snapshot, consume=True)
        exec_a = None if execution is None else execution[0]
        exec_b = None if execution is None else execution[1]
        if self._spread_position.position_id_a in self.market_a.positions and self.market_a.positions[self._spread_position.position_id_a].can_close():
            self.market_a.close_position(
                position_id=self._spread_position.position_id_a,
                close_reason=reason,
                execution_fee_paid=Decimal(0) if exec_a is None else exec_a["execution_fee_paid"],
                execution_timestamp=None if exec_a is None else exec_a["execution_timestamp"],
                execution_tx_hash="" if exec_a is None else exec_a["execution_tx_hash"],
                execution_source="" if exec_a is None else exec_a["execution_source"],
                close_rate=None if exec_a is None else exec_a["fixed_rate"],
            )
        if self._spread_position.position_id_b in self.market_b.positions and self.market_b.positions[self._spread_position.position_id_b].can_close():
            self.market_b.close_position(
                position_id=self._spread_position.position_id_b,
                close_reason=reason,
                execution_fee_paid=Decimal(0) if exec_b is None else exec_b["execution_fee_paid"],
                execution_timestamp=None if exec_b is None else exec_b["execution_timestamp"],
                execution_tx_hash="" if exec_b is None else exec_b["execution_tx_hash"],
                execution_source="" if exec_b is None else exec_b["execution_source"],
                close_rate=None if exec_b is None else exec_b["fixed_rate"],
            )
        self._spread_position = None

    def on_bar(self, snapshot: Snapshot):
        rate_a = self.market_a.market_status.data["mark_rate"]
        rate_b = self.market_b.market_status.data["mark_rate"]
        time_to_mat_a = int(
            self.market_a.market_status.data.get(
                "latest_f_time_to_maturity_seconds",
                self.market_a.market_status.data["time_to_maturity_seconds"],
            )
        )
        time_to_mat_b = int(
            self.market_b.market_status.data.get(
                "latest_f_time_to_maturity_seconds",
                self.market_b.market_status.data["time_to_maturity_seconds"],
            )
        )
        signal_ready = (
            time_to_mat_a >= self.min_time_to_maturity_seconds
            and time_to_mat_b >= self.min_time_to_maturity_seconds
            and abs(rate_a) <= self.max_signal_rate
            and abs(rate_b) <= self.max_signal_rate
        )
        spread = rate_a - rate_b
        if signal_ready:
            self._spread_window.append(spread)
        reference_spread = self._reference_spread()
        spread_deviation = None if reference_spread is None else spread - reference_spread
        expected_gross_edge = None
        expected_total_cost = None
        expected_edge_after_cost = None
        entry_allowed = False
        if signal_ready and spread_deviation is not None and abs(spread_deviation) >= self.entry_threshold:
            planned_execution = self._pair_execution(snapshot, consume=False)
            if planned_execution is not None:
                expected_gross_edge, expected_total_cost, expected_edge_after_cost = self._estimate_pair_edge_after_cost(
                    spread_deviation=spread_deviation,
                    time_to_mat_a=time_to_mat_a,
                    time_to_mat_b=time_to_mat_b,
                    execution=planned_execution,
                )
                entry_allowed = expected_edge_after_cost >= self.min_expected_edge_after_cost
        self.spread_history.append(
            {
                "timestamp": snapshot.timestamp,
                "rate_a": rate_a,
                "rate_b": rate_b,
                "spread": spread,
                "reference_spread": spread if reference_spread is None else reference_spread,
                "signal_ready": signal_ready,
                "time_to_maturity_a": time_to_mat_a,
                "time_to_maturity_b": time_to_mat_b,
                "position_open": self._spread_position is not None,
                "spread_deviation": None if spread_deviation is None else spread_deviation,
                "expected_gross_edge": expected_gross_edge,
                "expected_total_cost": expected_total_cost,
                "expected_edge_after_cost": expected_edge_after_cost,
                "entry_allowed": entry_allowed,
            }
        )
        if reference_spread is None:
            return

        open_a = self.market_a.get_open_positions()
        open_b = self.market_b.get_open_positions()
        if self._spread_position is None and len(open_a) == 0 and len(open_b) == 0:
            if signal_ready and abs(spread_deviation) >= self.entry_threshold and entry_allowed:
                self._open_spread(snapshot, spread_deviation)
            return

        combined_unrealized = self.market_a.get_market_balance().unrealized_pnl + self.market_b.get_market_balance().unrealized_pnl
        snapshot_ts = pd.Timestamp(snapshot.timestamp).to_pydatetime()
        matured = snapshot_ts >= self.market_a.maturity.to_pydatetime() or snapshot_ts >= self.market_b.maturity.to_pydatetime()
        if not signal_ready:
            self._close_spread(snapshot, "signal_guard")
        elif abs(spread_deviation) <= self.exit_threshold:
            self._close_spread(snapshot, "spread_exit")
        elif combined_unrealized <= -self.stop_loss:
            self._close_spread(snapshot, "stop_loss")
        elif matured:
            self._close_spread(snapshot, "maturity")
