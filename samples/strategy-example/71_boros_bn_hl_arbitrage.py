from pathlib import Path
import pandas as pd
import sys
from collections import deque
from demeter import Actuator, MarketInfo, MarketTypeEnum, Strategy, USD, Snapshot
from demeter.boros_v4 import BorosMarket, BorosExecutionMode, FixedFloatDirection
from demeter.boros_v4.helper import EVENT_KIND_ORDERBOOK, EVENT_KIND_AMM
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass

# 第一步：在 Boros 做空 BNB HL 市场的 YU，这一步是为了收HL固定利率，付HL浮动费率。
# 第二步：在 Hyperliquid 开YU等量的 BNB 空单，收HL的浮动费率，抵消在boros付的浮动费率。
#
# 前两步让你的只剩下在Boros市场收到的做空YU的固定利率，现在这个值是6.45%
#
# 第三步：在 Boros 做多 BNB BN 市场的 YU， 同理收BN浮动费率，付BN固定利率。
# 第四步：在 Binance 开YU等量的 BNB 多单，付BN浮动费率，抵消在boros收的浮动费率。
#
# 后两步让你的只剩下在Boros市场付出的做多YU的固定利率，现在这个值是2.83%
#
# 一收一付之间产生了6.45% - 2.83% = 3.62% 的利差。但是波动已经被摒除，同时达到价格波动和费率波动的delta中性了。
#
# 再严谨一点，严格计算一下APR，举个例子，这个100 YU的情况下，吃100BNB的固定费率，你在boros的BNB BN和BNB HL分别需要付 0.2613 BNB， 0.5204 BNB来做多空YU。BN和HL上各需要100BNB等值的U来做多空。
#
# 也就是说在没有杠杆的情况下 Y = 100 * 3.62% / (100 / 1 + 100 / 1 + 0.2613 + 0.5204） = 1.80% APR
#
# 但对于BNB这个量级的币，5x 开多空还算相对安全（因合约仓位是否全仓，是否有其他已开仓位产生安全垫而异）
#
# 在5x杠杆的情况下 Y = 100 * 3.62% / (100 / 5 + 100 / 5 + 0.2613 + 0.5204） = 8.88% APR
#
# 依次类推 10x 为 17.4% APR， 20x为33.6% APR
#
# 另外需要注意的是，由于费率在boros也会产生结算和波动，且boros自带了少量杠杆，在boros上开多空YU也会被清算，所以健康因子也同样需要关注。


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EVENT_DIR = ROOT / "bn_hl_260121-260226"


@dataclass
class SpreadPosition:
    position_id_a: int
    position_id_b: int


class BorosBinanceHyperliquidArbitrageStrategy(Strategy):
    """
    Interest Rate Spread Lock Between BNB and HyperLiquid
    """
    def __init__(
            self,
            market_a_info: MarketInfo,
            market_b_info: MarketInfo,
            notional: Decimal,
            lookback: int = 60,
            entry_threshold: Decimal = Decimal("0.002"),
            exit_threshold: Decimal = Decimal("0.0005"),
            rebalance_threshold: Decimal = Decimal("0.002"),
            stop_loss: Decimal | None = None,
            execution_mode: BorosExecutionMode = BorosExecutionMode.BAR_APPROX,
            min_time_to_maturity_seconds: int = 24 * 3600,
            max_signal_rate: Decimal = Decimal("2"),
            max_execution_delay_seconds: int | None = None,
            max_pair_execution_skew_seconds: int | None = None
    ):
        super().__init__()
        self.market_a_info = market_a_info
        self.market_b_info = market_b_info
        self.notional = Decimal(notional)
        self.lookback = int(lookback)
        self.entry_threshold = Decimal(entry_threshold)
        self.exit_threshold = Decimal(exit_threshold)
        self.rebalance_threshold = Decimal(rebalance_threshold)
        self.stop_loss = Decimal(stop_loss) if stop_loss is not None else self.notional * Decimal("0.01")
        self.execution_mode = execution_mode
        self.min_time_to_maturity_seconds = int(min_time_to_maturity_seconds)
        self.max_signal_rate = Decimal(max_signal_rate)
        self.max_signal_rate = Decimal(max_signal_rate)
        self.max_execution_delay_seconds = (
            None if max_execution_delay_seconds is None else max(0, int(max_execution_delay_seconds))
        )
        self.max_pair_execution_skew_seconds = (
            None if max_pair_execution_skew_seconds is None else max(0, int(max_pair_execution_skew_seconds))
        )

        self._spread_window: deque[Decimal] = deque(maxlen=self.lookback)
        self._spread_position: SpreadPosition | None = None


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

    def _entry_directions(self, spread_deviation: Decimal) -> tuple[FixedFloatDirection, FixedFloatDirection]:
        if spread_deviation >= self.entry_threshold:
            return FixedFloatDirection.PAY_FIXED, FixedFloatDirection.RECEIVE_FIXED
        return FixedFloatDirection.RECEIVE_FIXED, FixedFloatDirection.PAY_FIXED

    @staticmethod
    def _open_rate_preference(direction: FixedFloatDirection) -> bool:
        return direction == FixedFloatDirection.RECEIVE_FIXED

    @staticmethod
    def _close_rate_preference(direction: FixedFloatDirection) -> bool:
        return direction == FixedFloatDirection.PAY_FIXED

    @staticmethod
    def _required_trade_side_for_open(direction: FixedFloatDirection) -> str:
        return direction.to_side().name

    @staticmethod
    def _required_trade_side_for_close(direction: FixedFloatDirection) -> str:
        return direction.to_side().opposite().name

    def _pair_execution(
        self,
        snapshot: Snapshot,
        consume: bool = True,
        prefer_higher_rate_a: bool | None = None,
        prefer_higher_rate_b: bool | None = None,
        required_trade_side_a: str | None = None,
        required_trade_side_b: str | None = None,
        include_opening_fee_rate: bool = True,
    ):
        if self.execution_mode == BorosExecutionMode.BAR_APPROX:
            return (
                {"fixed_rate": self.market_a.market_status.data["mark_rate"], "execution_timestamp": None, "execution_tx_hash": "", "execution_source": "", "execution_fee_paid": Decimal(0), "execution_opening_fee_rate": None},
                {"fixed_rate": self.market_b.market_status.data["mark_rate"], "execution_timestamp": None, "execution_tx_hash": "", "execution_source": "", "execution_fee_paid": Decimal(0), "execution_opening_fee_rate": None},
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
                {"fixed_rate": row_a["trade_rate_vwap"], "execution_timestamp": snapshot.timestamp.to_pydatetime(), "execution_tx_hash": "", "execution_source": "minute_trade", "execution_fee_paid": row_a["fee_paid"] if "fee_paid" in row_a.index else Decimal(0), "execution_opening_fee_rate": Decimal(0)},
                {"fixed_rate": row_b["trade_rate_vwap"], "execution_timestamp": snapshot.timestamp.to_pydatetime(), "execution_tx_hash": "", "execution_source": "minute_trade", "execution_fee_paid": row_b["fee_paid"] if "fee_paid" in row_b.index else Decimal(0), "execution_opening_fee_rate": Decimal(0)},
            )
        if self.execution_mode == BorosExecutionMode.EVENT_REPLAY_FULL_PROTO:
            if (
                prefer_higher_rate_a is None
                or prefer_higher_rate_b is None
            ):
                return None
            row_a = self.market_a.peek_full_execution_quote(
                snapshot.timestamp,
                required_trade_side=required_trade_side_a,
                prefer_higher_rate=prefer_higher_rate_a,
                max_delay_seconds=self.max_execution_delay_seconds,
                include_opening_fee_rate=include_opening_fee_rate,
            )
            row_b = self.market_b.peek_full_execution_quote(
                snapshot.timestamp,
                required_trade_side=required_trade_side_b,
                prefer_higher_rate=prefer_higher_rate_b,
                max_delay_seconds=self.max_execution_delay_seconds,
                include_opening_fee_rate=include_opening_fee_rate,
            )
            if row_a is None and required_trade_side_a is not None:
                row_a = self.market_a.peek_full_execution_quote(
                    snapshot.timestamp,
                    required_trade_side=None,
                    prefer_higher_rate=prefer_higher_rate_a,
                    max_delay_seconds=self.max_execution_delay_seconds,
                    include_opening_fee_rate=include_opening_fee_rate,
                )
            if row_b is None and required_trade_side_b is not None:
                row_b = self.market_b.peek_full_execution_quote(
                    snapshot.timestamp,
                    required_trade_side=None,
                    prefer_higher_rate=prefer_higher_rate_b,
                    max_delay_seconds=self.max_execution_delay_seconds,
                    include_opening_fee_rate=include_opening_fee_rate,
                )
            if row_a is None or row_b is None:
                return None
            signal_ts = pd.Timestamp(snapshot.timestamp)
            if self.max_pair_execution_skew_seconds is not None:
                max_skew = pd.Timedelta(seconds=self.max_pair_execution_skew_seconds)
                ts_a = pd.Timestamp(row_a["execution_timestamp"])
                ts_b = pd.Timestamp(row_b["execution_timestamp"])
                if abs(ts_a - ts_b) > max_skew:
                    return None
            if consume:
                row_a = self.market_a.claim_full_execution_quote(
                    snapshot.timestamp,
                    required_trade_side=required_trade_side_a,
                    prefer_higher_rate=prefer_higher_rate_a,
                    max_delay_seconds=self.max_execution_delay_seconds,
                    include_opening_fee_rate=include_opening_fee_rate,
                )
                row_b = self.market_b.claim_full_execution_quote(
                    snapshot.timestamp,
                    required_trade_side=required_trade_side_b,
                    prefer_higher_rate=prefer_higher_rate_b,
                    max_delay_seconds=self.max_execution_delay_seconds,
                    include_opening_fee_rate=include_opening_fee_rate,
                )
                if row_a is None and required_trade_side_a is not None:
                    row_a = self.market_a.claim_full_execution_quote(
                        snapshot.timestamp,
                        required_trade_side=None,
                        prefer_higher_rate=prefer_higher_rate_a,
                        max_delay_seconds=self.max_execution_delay_seconds,
                        include_opening_fee_rate=include_opening_fee_rate,
                    )
                if row_b is None and required_trade_side_b is not None:
                    row_b = self.market_b.claim_full_execution_quote(
                        snapshot.timestamp,
                        required_trade_side=None,
                        prefer_higher_rate=prefer_higher_rate_b,
                        max_delay_seconds=self.max_execution_delay_seconds,
                        include_opening_fee_rate=include_opening_fee_rate,
                    )
            return row_a, row_b

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
                "execution_opening_fee_rate": row_a.opening_fee_rate_annualized,
                "execution_timestamp": row_a.timestamp.to_pydatetime(),
                "execution_tx_hash": row_a.tx_hash,
                "execution_source": row_a.source_kind,
            },
            {
                "fixed_rate": row_b.implied_rate,
                "execution_fee_paid": row_b.fee_paid,
                "execution_opening_fee_rate": row_b.opening_fee_rate_annualized,
                "execution_timestamp": row_b.timestamp.to_pydatetime(),
                "execution_tx_hash": row_b.tx_hash,
                "execution_source": row_b.source_kind,
            },
        )

    def _open_spread(self, snapshot: Snapshot, spread: Decimal):
        direction_a, direction_b = self._entry_directions(spread)
        execution = self._pair_execution(
            snapshot,
            consume=True,
            prefer_higher_rate_a=self._open_rate_preference(direction_a),
            prefer_higher_rate_b=self._open_rate_preference(direction_b),
            required_trade_side_a=self._required_trade_side_for_open(direction_a),
            required_trade_side_b=self._required_trade_side_for_open(direction_b),
            include_opening_fee_rate=True,
        )
        if execution is None:
            return
        exec_a, exec_b = execution
        if spread >= self.entry_threshold:
            pos_a = self.market_a.open_fixed_float(
                self.notional,
                FixedFloatDirection.PAY_FIXED, # bn open BNB pay fixed
                fixed_rate=exec_a["fixed_rate"],
                execution_fee_paid=exec_a["execution_fee_paid"],
                execution_opening_fee_rate=exec_a["execution_opening_fee_rate"],
                execution_timestamp=exec_a["execution_timestamp"],
                execution_tx_hash=exec_a["execution_tx_hash"],
                execution_source=exec_a["execution_source"],
                execution_effective_rate=exec_a.get("_effective_rate", Decimal(0)),
                execution_available_abs_size_total=exec_a.get("available_abs_size_total", Decimal(0)),
                execution_option_count=exec_a.get("execution_option_count", 0),
                execution_selection_reason=exec_a.get("execution_selection_reason", ""),
                execution_quote_options_json=exec_a.get("execution_quote_options_json", ""),
            )
            pos_b = self.market_b.open_fixed_float(
                self.notional,
                FixedFloatDirection.RECEIVE_FIXED, # hl open BNB receive fixed
                fixed_rate=exec_b["fixed_rate"],
                execution_fee_paid=exec_b["execution_fee_paid"],
                execution_opening_fee_rate=exec_b["execution_opening_fee_rate"],
                execution_timestamp=exec_b["execution_timestamp"],
                execution_tx_hash=exec_b["execution_tx_hash"],
                execution_source=exec_b["execution_source"],
                execution_effective_rate=exec_b.get("_effective_rate", Decimal(0)),
                execution_available_abs_size_total=exec_b.get("available_abs_size_total", Decimal(0)),
                execution_option_count=exec_b.get("execution_option_count", 0),
                execution_selection_reason=exec_b.get("execution_selection_reason", ""),
                execution_quote_options_json=exec_b.get("execution_quote_options_json", ""),
            )
        else:  # reversed
            pos_a = self.market_a.open_fixed_float(
                self.notional,
                FixedFloatDirection.RECEIVE_FIXED,
                fixed_rate=exec_a["fixed_rate"],
                execution_fee_paid=exec_a["execution_fee_paid"],
                execution_opening_fee_rate=exec_a["execution_opening_fee_rate"],
                execution_timestamp=exec_a["execution_timestamp"],
                execution_tx_hash=exec_a["execution_tx_hash"],
                execution_source=exec_a["execution_source"],
                execution_effective_rate=exec_a.get("_effective_rate", Decimal(0)),
                execution_available_abs_size_total=exec_a.get("available_abs_size_total", Decimal(0)),
                execution_option_count=exec_a.get("execution_option_count", 0),
                execution_selection_reason=exec_a.get("execution_selection_reason", ""),
                execution_quote_options_json=exec_a.get("execution_quote_options_json", ""),
            )
            pos_b = self.market_b.open_fixed_float(
                self.notional,
                FixedFloatDirection.PAY_FIXED,
                fixed_rate=exec_b["fixed_rate"],
                execution_fee_paid=exec_b["execution_fee_paid"],
                execution_opening_fee_rate=exec_b["execution_opening_fee_rate"],
                execution_timestamp=exec_b["execution_timestamp"],
                execution_tx_hash=exec_b["execution_tx_hash"],
                execution_source=exec_b["execution_source"],
                execution_effective_rate=exec_b.get("_effective_rate", Decimal(0)),
                execution_available_abs_size_total=exec_b.get("available_abs_size_total", Decimal(0)),
                execution_option_count=exec_b.get("execution_option_count", 0),
                execution_selection_reason=exec_b.get("execution_selection_reason", ""),
                execution_quote_options_json=exec_b.get("execution_quote_options_json", ""),
            )
        self._spread_position = SpreadPosition(position_id_a=pos_a.position_id, position_id_b=pos_b.position_id)

    def _close_spread(self, snapshot: Snapshot, reason: str):
        if self._spread_position is None:
            return
        position_a = self.market_a.positions.get(self._spread_position.position_id_a)
        position_b = self.market_b.positions.get(self._spread_position.position_id_b)
        execution = self._pair_execution(
            snapshot,
            consume=True,
            prefer_higher_rate_a=None if position_a is None else self._close_rate_preference(position_a.direction),
            prefer_higher_rate_b=None if position_b is None else self._close_rate_preference(position_b.direction),
            required_trade_side_a=None if position_a is None else self._required_trade_side_for_close(
                position_a.direction),
            required_trade_side_b=None if position_b is None else self._required_trade_side_for_close(
                position_b.direction),
            include_opening_fee_rate=False,
        )
        exec_a = None if execution is None else execution[0]
        exec_b = None if execution is None else execution[1]
        if self._spread_position.position_id_a in self.market_a.positions and self.market_a.positions[
            self._spread_position.position_id_a].can_close():
            self.market_a.close_position(
                position_id=self._spread_position.position_id_a,
                close_reason=reason,
                execution_fee_paid=Decimal(0) if exec_a is None else exec_a["execution_fee_paid"],
                execution_timestamp=None if exec_a is None else exec_a["execution_timestamp"],
                execution_tx_hash="" if exec_a is None else exec_a["execution_tx_hash"],
                execution_source="" if exec_a is None else exec_a["execution_source"],
                execution_effective_rate=Decimal(0) if exec_a is None else exec_a.get("_effective_rate", Decimal(0)),
                execution_available_abs_size_total=Decimal(0) if exec_a is None else exec_a.get(
                    "available_abs_size_total", Decimal(0)),
                execution_option_count=0 if exec_a is None else exec_a.get("execution_option_count", 0),
                execution_selection_reason="" if exec_a is None else exec_a.get("execution_selection_reason", ""),
                execution_quote_options_json="" if exec_a is None else exec_a.get("execution_quote_options_json", ""),
                close_rate=None if exec_a is None else exec_a["fixed_rate"],
            )
        if self._spread_position.position_id_b in self.market_b.positions and self.market_b.positions[
            self._spread_position.position_id_b].can_close():
            self.market_b.close_position(
                position_id=self._spread_position.position_id_b,
                close_reason=reason,
                execution_fee_paid=Decimal(0) if exec_b is None else exec_b["execution_fee_paid"],
                execution_timestamp=None if exec_b is None else exec_b["execution_timestamp"],
                execution_tx_hash="" if exec_b is None else exec_b["execution_tx_hash"],
                execution_source="" if exec_b is None else exec_b["execution_source"],
                execution_effective_rate=Decimal(0) if exec_b is None else exec_b.get("_effective_rate", Decimal(0)),
                execution_available_abs_size_total=Decimal(0) if exec_b is None else exec_b.get(
                    "available_abs_size_total", Decimal(0)),
                execution_option_count=0 if exec_b is None else exec_b.get("execution_option_count", 0),
                execution_selection_reason="" if exec_b is None else exec_b.get("execution_selection_reason", ""),
                execution_quote_options_json="" if exec_b is None else exec_b.get("execution_quote_options_json", ""),
                close_rate=None if exec_b is None else exec_b["fixed_rate"],
            )
        self._spread_position = None

    def on_bar(self, snapshot: Snapshot):
        rate_a, rate_b = self.market_a.market_status.data["mark_rate"], self.market_b.market_status.data["mark_rate"]
        time_to_mat_a, time_to_mat_b = int(
            self.market_a.market_status.data.get(
                "latest_f_time_to_maturity_seconds",
                self.market_a.market_status.data["time_to_maturity_seconds"],
            )
        ), int(
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
        spread = rate_a - rate_b  # 价格差
        # reference_spread = self._reference_spread()
        # if reference_spread is None:
        #     return
        # spread_deviation = None if reference_spread is None else spread - reference_spread

        spread_deviation = spread

        open_a = self.market_a.get_open_positions()
        open_b = self.market_b.get_open_positions()

        if self._spread_position is None and len(open_a) == 0 and len(open_b) == 0:
            if signal_ready and abs(spread_deviation) >= self.entry_threshold:
                self._open_spread(snapshot, spread_deviation)
                if self._spread_position:
                    self._spread_window.append(spread_deviation)
            return

        to_rebalance = False
        if (abs(spread_deviation) > abs(self._spread_window[-1])):
            print('-' * 20, abs(spread_deviation), abs(self._spread_window[-1]))
        if len(self._spread_window) >= 1 and (abs(spread_deviation) - abs(self._spread_window[-1])) > self.rebalance_threshold:
            to_rebalance = True

        snapshot_ts = pd.Timestamp(snapshot.timestamp).to_pydatetime()
        unrealized = self.market_a.get_market_balance().unrealized_pnl + self.market_b.get_market_balance().unrealized_pnl
        matured = snapshot_ts >= self.market_a.maturity.to_pydatetime() or snapshot_ts >= self.market_b.maturity.to_pydatetime()

        if not to_rebalance:
            if not signal_ready:
                self._close_spread(snapshot, "signal_guard")
            # elif abs(spread_deviation) <= self.exit_threshold:
            #     self._close_spread(snapshot, "spread_exit")
            elif unrealized <= -self.stop_loss:
                self._close_spread(snapshot, "stop_loss")
            elif matured:
                self._close_spread(snapshot, "maturity")
        else:
            self._close_spread(snapshot, "rebalance")

            open_a = self.market_a.get_open_positions()
            open_b = self.market_b.get_open_positions()
            if self._spread_position is None and len(open_a) == 0 and len(open_b) == 0:
                if signal_ready and abs(spread_deviation) >= self.entry_threshold:
                    self._open_spread(snapshot, spread_deviation)
                    if self._spread_position:
                        self._spread_window.append(spread_deviation)
                return




if __name__ == '__main__':
    event_dir = str(EVENT_DIR)
    market_a_name, market_b_name = 'binance_feb27', 'hyperliquid_feb27'
    market_a_key = "BINANCE-ETHUSDT-27FEB2026"
    market_b_key = "HYPERLIQUID-ETH-27FEB2026"
    venue_a = "BINANCE"
    venue_b = "HYPERLIQUID"
    market_a_info = MarketInfo(market_a_name, MarketTypeEnum.boros)
    market_b_info = MarketInfo(market_b_name, MarketTypeEnum.boros)
    market_a = BorosMarket(market_a_info)
    market_b = BorosMarket(market_b_info)
    maturity = datetime(2026, 2, 27, 0, 0, 0)
    market_a.load_event_data(event_dir=event_dir, market_key=market_a_key, venue=venue_a, maturity=maturity, source_kind=EVENT_KIND_ORDERBOOK)
    market_b.load_event_data(event_dir=event_dir, market_key=market_b_key, venue=venue_b, maturity=maturity)

    actuator = Actuator()
    actuator.broker.add_market(market_a)
    actuator.broker.add_market(market_b)
    actuator.broker.set_balance(USD, Decimal("1000"))

    notional = Decimal("100")
    lookback = 60
    entry_threshold = Decimal("0.004")
    exit_threshold = Decimal("0.001")
    stop_loss = Decimal("5")
    execution_mode = BorosExecutionMode.TX_REPLAY_BEST_EXEC
    min_time_to_maturity_seconds = 24 * 3600
    max_signal_rate = Decimal("2")
    max_execution_delay_seconds = 15 * 60
    max_pair_execution_skew_seconds = 5 * 60

    strategy = BorosBinanceHyperliquidArbitrageStrategy(
        market_a_info=market_a_info,
        market_b_info=market_b_info,
        notional=notional,
        lookback=lookback,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        stop_loss=stop_loss,
        execution_mode=execution_mode,
        min_time_to_maturity_seconds=min_time_to_maturity_seconds,
        max_signal_rate=max_signal_rate,
        max_execution_delay_seconds=max_execution_delay_seconds,
        max_pair_execution_skew_seconds=max_pair_execution_skew_seconds
    )

    actuator.strategy = strategy
    price_index = market_a.get_price_from_data().index.union(market_b.get_price_from_data().index)
    actuator.set_price(pd.DataFrame(index=price_index))
    actuator.run(print_result=True)
    actuator.save_result(path="./result", file_name="boros", decimals=5)
