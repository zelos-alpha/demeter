import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

import pandas as pd

from .._typing import DemeterError, USD, TokenInfo
from ..broker import ActionTypeEnum, BaseAction, Market, MarketBalance, MarketInfo, MarketStatus, write_func
from ..utils import ForColorEnum, get_formatted_from_dict, get_formatted_predefined, require, STYLE
from ..utils.console_text import get_action_str
from ._typing import Side
from .PaymentLib import FIndex, PaymentLib, SettlementBreakdown
from .PMath import PMath
from .helper import get_price_from_data, load_boros_data, load_boros_event_data, load_boros_tx_ledger


class FixedFloatDirection(Enum):
    PAY_FIXED = "pay_fixed"
    RECEIVE_FIXED = "receive_fixed"

    @property
    def sign(self) -> int:
        return 1 if self == FixedFloatDirection.PAY_FIXED else -1

    def to_side(self) -> Side:
        """
        Protocol-level Boros side mapping.

        In Boros/YU terms:
        - LONG pays fixed upfront and receives floating
        - SHORT receives fixed upfront and pays floating
        """
        return Side.LONG if self == FixedFloatDirection.PAY_FIXED else Side.SHORT

    @staticmethod
    def from_side(side: Side) -> "FixedFloatDirection":
        return FixedFloatDirection.PAY_FIXED if side == Side.LONG else FixedFloatDirection.RECEIVE_FIXED


@dataclass
class FixedFloatPosition:
    position_id: int
    direction: FixedFloatDirection
    notional: Decimal
    entry_fixed_rate: Decimal
    entry_time: datetime
    maturity: pd.Timestamp
    entry_findex: FIndex
    entry_time_to_maturity_seconds: int
    entry_upfront_fixed_cost: Decimal
    entry_opening_fee_cost: Decimal
    remaining_notional: Decimal
    closed_notional: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)
    exit_time: datetime | None = None
    is_closed: bool = False

    def can_close(self) -> bool:
        return not self.is_closed and self.remaining_notional > 0


@dataclass
class BorosBalance(MarketBalance):
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    accrued_payment: Decimal
    accrued_fees: Decimal
    mark_to_maturity_value: Decimal
    upfront_fixed_cost: Decimal
    upfront_opening_fee_cost: Decimal
    position_count: int
    open_notional: Decimal
    pay_fixed_notional: Decimal
    receive_fixed_notional: Decimal
    current_mark_rate: Decimal


@dataclass
class OpenFixedFloatAction(BaseAction):
    position_id: int
    direction: str
    notional: Decimal
    fixed_rate: Decimal
    mark_rate: Decimal
    entry_upfront_fixed_cost: Decimal = Decimal(0)
    entry_opening_fee_cost: Decimal = Decimal(0)
    execution_fee_paid: Decimal = Decimal(0)
    execution_timestamp: datetime | None = None
    execution_tx_hash: str = ""
    execution_source: str = ""
    execution_effective_rate: Decimal = Decimal(0)
    execution_available_abs_size_total: Decimal = Decimal(0)
    execution_option_count: int = 0
    execution_selection_reason: str = ""
    execution_quote_options_json: str = ""

    def set_type(self):
        self.action_type = ActionTypeEnum.boros_open_fixed_float

    def get_output_str(self):
        return get_action_str(
            self,
            ForColorEnum.green,
            {
                "position_id": str(self.position_id),
                "direction": self.direction,
                "notional": str(self.notional),
                "fixed_rate": str(self.fixed_rate),
                "mark_rate": str(self.mark_rate),
            },
        )


@dataclass
class CloseFixedFloatAction(BaseAction):
    position_id: int
    direction: str
    notional: Decimal
    close_notional: Decimal
    remaining_notional: Decimal
    entry_fixed_rate: Decimal
    exit_mark_rate: Decimal
    pnl: Decimal
    close_reason: str
    settlement_payment: Decimal = Decimal(0)
    settlement_fees: Decimal = Decimal(0)
    mark_to_maturity_value: Decimal = Decimal(0)
    execution_fee_paid: Decimal = Decimal(0)
    execution_timestamp: datetime | None = None
    execution_tx_hash: str = ""
    execution_source: str = ""
    execution_effective_rate: Decimal = Decimal(0)
    execution_available_abs_size_total: Decimal = Decimal(0)
    execution_option_count: int = 0
    execution_selection_reason: str = ""
    execution_quote_options_json: str = ""

    def set_type(self):
        self.action_type = ActionTypeEnum.boros_close_fixed_float

    def get_output_str(self):
        return get_action_str(
            self,
            ForColorEnum.yellow,
            {
                "position_id": str(self.position_id),
                "direction": self.direction,
                "notional": str(self.notional),
                "close_notional": str(self.close_notional),
                "remaining_notional": str(self.remaining_notional),
                "pnl": str(self.pnl),
                "close_reason": self.close_reason,
            },
        )


class BorosMarket(Market):
    def __init__(self, market_info: MarketInfo, data: pd.DataFrame | None = None, data_path: str = "./data"):
        super().__init__(market_info=market_info, data=data, data_path=data_path)
        self.quote_token: TokenInfo = USD
        self.venue: str = ""
        self.maturity: pd.Timestamp | None = None
        self.positions: dict[int, FixedFloatPosition] = {}
        self.realized_pnl: Decimal = Decimal(0)
        self._next_position_id = 1
        self.tx_ledger: pd.DataFrame = pd.DataFrame()
        self.trade_ledger: pd.DataFrame = pd.DataFrame()
        self.event_ledger: pd.DataFrame = pd.DataFrame()
        self._consumed_execution_rows: set[int] = set()
        self._consumed_full_execution_rows: set[int] = set()
        self._latest_f_time_to_maturity_cache: dict[pd.Timestamp, int] = {}
        self.mark_rate_column = "mark_rate"

    @staticmethod
    def _normalize_decimal(value: Decimal) -> Decimal:
        return Decimal(0) if abs(value) < Decimal("1e-15") else value

    def __str__(self):
        return json.dumps(
            {
                "name": self.market_info.name,
                "type": type(self).__name__,
                "venue": self.venue,
                "maturity": self.maturity.isoformat() if self.maturity is not None else "",
            }
        )

    @property
    def description(self):
        return {"name": self.market_info.name, "type": type(self).__name__, "venue": self.venue}

    @property
    def has_open_position(self) -> bool:
        return len(self.get_open_positions()) > 0

    def get_open_positions(self) -> list[FixedFloatPosition]:
        return [position for position in self.positions.values() if position.can_close()]

    def _current_mark_rate(self) -> Decimal:
        if self.market_status.data is not None and self.mark_rate_column in self.market_status.data.index:
            return self.market_status.data[self.mark_rate_column]
        raise DemeterError("Boros market rate is unavailable")

    def _current_timestamp(self) -> datetime:
        if self.market_status.timestamp is not None:
            return self.market_status.timestamp
        raise DemeterError("Boros market timestamp is unavailable")

    def _current_findex(self) -> FIndex:
        if self.market_status.data is not None:
            return FIndex(
                floating_index=PaymentLib.decimal_to_wad(self.market_status.data["floating_index"]),
                fee_index=PaymentLib.decimal_to_wad(self.market_status.data["fee_index"]),
            )
        raise DemeterError("Boros settlement index is unavailable")

    def _current_time_to_maturity_seconds(self) -> int:
        if self.market_status.data is not None and "time_to_maturity_seconds" in self.market_status.data.index:
            return int(self.market_status.data["time_to_maturity_seconds"])
        raise DemeterError("Boros market maturity is unavailable")

    def _current_latest_f_time_to_maturity_seconds(self) -> int:
        if self.market_status.data is not None and "latest_f_time_to_maturity_seconds" in self.market_status.data.index:
            return int(self.market_status.data["latest_f_time_to_maturity_seconds"])
        return self._current_time_to_maturity_seconds()

    def _latest_f_time_to_maturity_seconds_asof(self, timestamp: datetime | pd.Timestamp) -> int:
        ts = pd.Timestamp(timestamp)
        cached = self._latest_f_time_to_maturity_cache.get(ts)
        if cached is not None:
            return cached
        if self.data is None or len(self.data.index) == 0:
            value = self._current_latest_f_time_to_maturity_seconds()
            self._latest_f_time_to_maturity_cache[ts] = value
            return value
        eligible = self.data.loc[self.data.index <= ts]
        if len(eligible.index) == 0:
            value = int(self.data.iloc[0].get("latest_f_time_to_maturity_seconds", self.data.iloc[0]["time_to_maturity_seconds"]))
            self._latest_f_time_to_maturity_cache[ts] = value
            return value
        row = eligible.iloc[-1]
        value = int(row.get("latest_f_time_to_maturity_seconds", row["time_to_maturity_seconds"]))
        self._latest_f_time_to_maturity_cache[ts] = value
        return value

    @staticmethod
    def _notional_to_signed_size_wad(notional: Decimal, direction: FixedFloatDirection) -> int:
        signed_notional = direction.to_side().to_signed_size(Decimal(notional))
        return PaymentLib.decimal_to_wad(signed_notional)

    def _position_value_breakdown(
        self,
        position: FixedFloatPosition,
        current_mark_rate: Decimal,
        current_findex: FIndex,
        current_time_to_maturity_seconds: int,
    ) -> SettlementBreakdown:
        signed_size = self._notional_to_signed_size_wad(position.remaining_notional, position.direction)
        return PaymentLib.calc_present_value(
            signed_size=signed_size,
            entry_fixed_rate=PaymentLib.decimal_to_wad(position.entry_fixed_rate),
            entry_findex=position.entry_findex,
            current_findex=current_findex,
            current_mark_rate=PaymentLib.decimal_to_wad(current_mark_rate),
            entry_time_to_mat=position.entry_time_to_maturity_seconds,
            current_time_to_mat=self._current_latest_f_time_to_maturity_seconds(),
            entry_opening_fee_cost=PaymentLib.decimal_to_wad(position.entry_opening_fee_cost),
        )

    def _close_position_internal(
        self,
        position: FixedFloatPosition,
        current_mark_rate: Decimal,
        close_time: datetime,
        close_notional: Decimal | None = None,
        close_reason: str = "manual",
        execution_fee_paid: Decimal = Decimal(0),
        execution_timestamp: datetime | None = None,
        execution_tx_hash: str = "",
        execution_source: str = "",
        execution_effective_rate: Decimal = Decimal(0),
        execution_available_abs_size_total: Decimal = Decimal(0),
        execution_option_count: int = 0,
        execution_selection_reason: str = "",
        execution_quote_options_json: str = "",
    ) -> Decimal:
        if not position.can_close():
            return Decimal(0)
        close_notional = position.remaining_notional if close_notional is None else Decimal(close_notional)
        require(close_notional > 0, "close_notional should be positive")
        require(close_notional <= position.remaining_notional, "close_notional exceeds open notional")

        value_breakdown = self._position_value_breakdown(
            position=position,
            current_mark_rate=current_mark_rate,
            current_findex=self._current_findex(),
            current_time_to_maturity_seconds=self._current_time_to_maturity_seconds(),
        )
        full_unrealized = PaymentLib.wad_to_decimal(value_breakdown.total)
        close_ratio = close_notional / position.remaining_notional
        portion_pnl = self._normalize_decimal(full_unrealized * close_ratio - Decimal(execution_fee_paid))

        position.realized_pnl += portion_pnl
        position.closed_notional += close_notional
        position.entry_upfront_fixed_cost = self._normalize_decimal(position.entry_upfront_fixed_cost * (Decimal(1) - close_ratio))
        position.entry_opening_fee_cost = self._normalize_decimal(position.entry_opening_fee_cost * (Decimal(1) - close_ratio))
        position.remaining_notional -= close_notional
        if position.remaining_notional <= 0:
            position.remaining_notional = Decimal(0)
            position.exit_time = close_time
            position.is_closed = True

        self.realized_pnl = self._normalize_decimal(self.realized_pnl + portion_pnl)
        self._record_action(
            CloseFixedFloatAction(
                market=self.market_info,
                position_id=position.position_id,
                direction=position.direction.name,
                notional=position.notional,
                close_notional=close_notional,
                remaining_notional=position.remaining_notional,
                entry_fixed_rate=position.entry_fixed_rate,
                exit_mark_rate=current_mark_rate,
                pnl=portion_pnl,
                close_reason=close_reason,
                settlement_payment=PaymentLib.wad_to_decimal(value_breakdown.settlement.payment) * close_ratio,
                settlement_fees=PaymentLib.wad_to_decimal(value_breakdown.settlement.fees) * close_ratio,
                mark_to_maturity_value=PaymentLib.wad_to_decimal(value_breakdown.mark_to_maturity_value) * close_ratio,
                execution_fee_paid=Decimal(execution_fee_paid),
                execution_timestamp=execution_timestamp,
                execution_tx_hash=execution_tx_hash,
                execution_source=execution_source,
                execution_effective_rate=Decimal(execution_effective_rate),
                execution_available_abs_size_total=Decimal(execution_available_abs_size_total),
                execution_option_count=int(execution_option_count),
                execution_selection_reason=execution_selection_reason,
                execution_quote_options_json=execution_quote_options_json,
            )
        )
        return portion_pnl

    @write_func
    def open_fixed_float(
        self,
        notional: Decimal,
        direction: FixedFloatDirection,
        fixed_rate: Decimal | None = None,
        execution_fee_paid: Decimal = Decimal(0),
        execution_opening_fee_rate: Decimal | None = None,
        execution_timestamp: datetime | None = None,
        execution_tx_hash: str = "",
        execution_source: str = "",
        execution_effective_rate: Decimal = Decimal(0),
        execution_available_abs_size_total: Decimal = Decimal(0),
        execution_option_count: int = 0,
        execution_selection_reason: str = "",
        execution_quote_options_json: str = "",
    ):
        require(notional > 0, "notional should be positive")
        current_time = self._current_timestamp()
        if self.maturity is not None and current_time >= self.maturity.to_pydatetime():
            raise DemeterError("Boros market has matured")

        current_mark_rate = self._current_mark_rate()
        fixed_rate = current_mark_rate if fixed_rate is None else Decimal(fixed_rate)
        entry_time_to_mat = self._current_latest_f_time_to_maturity_seconds()
        entry_opening_fee_cost = Decimal(execution_fee_paid)
        if entry_opening_fee_cost <= 0:
            if execution_opening_fee_rate is None:
                opening_fee_rate = Decimal(self.market_status.data.get("opening_fee_rate_annualized_proxy", Decimal(0)))
            else:
                opening_fee_rate = Decimal(execution_opening_fee_rate)
            entry_opening_fee_cost = PaymentLib.wad_to_decimal(
                PaymentLib.calc_floating_fee(
                    abs_size=PaymentLib.decimal_to_wad(abs(Decimal(notional))),
                    fee_rate=PaymentLib.decimal_to_wad(opening_fee_rate),
                    time_to_mat=entry_time_to_mat,
                )
            )
        entry_upfront_fixed_cost = PaymentLib.wad_to_decimal(
            PaymentLib.calc_entry_fixed_cost(
                signed_size=self._notional_to_signed_size_wad(Decimal(notional), direction),
                fixed_rate=PaymentLib.decimal_to_wad(fixed_rate),
                entry_time_to_mat=entry_time_to_mat,
            )
        )
        position = FixedFloatPosition(
            position_id=self._next_position_id,
            direction=direction,
            notional=Decimal(notional),
            entry_fixed_rate=fixed_rate,
            entry_time=current_time,
            maturity=self.maturity,
            entry_findex=self._current_findex(),
            entry_time_to_maturity_seconds=entry_time_to_mat,
            entry_upfront_fixed_cost=entry_upfront_fixed_cost,
            entry_opening_fee_cost=entry_opening_fee_cost,
            remaining_notional=Decimal(notional),
        )
        self.positions[position.position_id] = position
        self._next_position_id += 1
        self._record_action(
            OpenFixedFloatAction(
                market=self.market_info,
                position_id=position.position_id,
                direction=direction.name,
                notional=position.notional,
                fixed_rate=fixed_rate,
                mark_rate=current_mark_rate,
                entry_upfront_fixed_cost=entry_upfront_fixed_cost,
                entry_opening_fee_cost=entry_opening_fee_cost,
                execution_fee_paid=Decimal(execution_fee_paid),
                execution_timestamp=execution_timestamp,
                execution_tx_hash=execution_tx_hash,
                execution_source=execution_source,
                execution_effective_rate=Decimal(execution_effective_rate),
                execution_available_abs_size_total=Decimal(execution_available_abs_size_total),
                execution_option_count=int(execution_option_count),
                execution_selection_reason=execution_selection_reason,
                execution_quote_options_json=execution_quote_options_json,
            )
        )
        return position

    @write_func
    def close_position(
        self,
        position_id: int | None = None,
        notional: Decimal | None = None,
        close_reason: str = "manual",
        execution_fee_paid: Decimal = Decimal(0),
        execution_timestamp: datetime | None = None,
        execution_tx_hash: str = "",
        execution_source: str = "",
        execution_effective_rate: Decimal = Decimal(0),
        execution_available_abs_size_total: Decimal = Decimal(0),
        execution_option_count: int = 0,
        execution_selection_reason: str = "",
        execution_quote_options_json: str = "",
        close_rate: Decimal | None = None,
    ):
        open_positions = self.get_open_positions()
        if len(open_positions) == 0:
            raise DemeterError("Boros market has no open position")
        if position_id is None:
            if len(open_positions) > 1:
                raise DemeterError("Multiple open Boros positions exist, please specify position_id")
            position = open_positions[0]
        else:
            position = self.positions[position_id]
        return self._close_position_internal(
            position=position,
            current_mark_rate=self._current_mark_rate() if close_rate is None else Decimal(close_rate),
            close_time=self._current_timestamp(),
            close_notional=notional,
            close_reason=close_reason,
            execution_fee_paid=execution_fee_paid,
            execution_timestamp=execution_timestamp,
            execution_tx_hash=execution_tx_hash,
            execution_source=execution_source,
            execution_effective_rate=execution_effective_rate,
            execution_available_abs_size_total=execution_available_abs_size_total,
            execution_option_count=execution_option_count,
            execution_selection_reason=execution_selection_reason,
            execution_quote_options_json=execution_quote_options_json,
        )

    def check_market(self):
        super().check_market()
        required_columns = {
            "mark_rate",
            "mark_rate_full_proto",
            "trade_rate_last",
            "trade_rate_vwap",
            "executed_size_abs",
            "executed_size_net",
            "trade_count",
            "tx_count",
            "time_delta_seconds",
            "time_to_maturity_seconds",
            "latest_f_time_to_maturity_seconds",
            "floating_index",
            "fee_index",
            "settlement_fee_rate_annualized_proxy",
            "maturity",
            "venue",
            "latest_f_time",
        }
        missing_columns = required_columns - set(self.data.columns)
        require(len(missing_columns) == 0, f"Boros market data missing columns: {sorted(missing_columns)}")

    def update(self):
        if self.has_open_position and self.maturity is not None and self._current_timestamp() >= self.maturity.to_pydatetime():
            for position in list(self.get_open_positions()):
                self._close_position_internal(position, self._current_mark_rate(), self._current_timestamp(), close_reason="maturity")
            self.has_update = True

    def set_market_status(self, data: MarketStatus, price: pd.Series):
        super().set_market_status(data, price)
        if data.data is None:
            timestamp = pd.Timestamp(data.timestamp)
            if timestamp in self.data.index:
                data.data = self.data.loc[timestamp]
            else:
                previous_index = self.data.index.asof(timestamp)
                if pd.isna(previous_index):
                    raise DemeterError(f"Boros market has no data available at or before {timestamp}")
                data.data = self.data.loc[previous_index]
        self._market_status = data

    def get_market_balance(self) -> BorosBalance:
        current_mark_rate = self._current_mark_rate()
        current_findex = self._current_findex()
        current_time_to_mat = self._current_time_to_maturity_seconds()
        breakdowns = [
            self._position_value_breakdown(position, current_mark_rate, current_findex, current_time_to_mat)
            for position in self.get_open_positions()
        ]
        unrealized_pnl = self._normalize_decimal(sum((PaymentLib.wad_to_decimal(item.total) for item in breakdowns), Decimal(0)))
        accrued_payment = self._normalize_decimal(sum((PaymentLib.wad_to_decimal(item.settlement.payment) for item in breakdowns), Decimal(0)))
        accrued_fees = self._normalize_decimal(sum((PaymentLib.wad_to_decimal(item.settlement.fees) for item in breakdowns), Decimal(0)))
        mark_to_maturity_value = self._normalize_decimal(sum((PaymentLib.wad_to_decimal(item.mark_to_maturity_value) for item in breakdowns), Decimal(0)))
        pay_fixed_notional = sum((p.remaining_notional for p in self.get_open_positions() if p.direction == FixedFloatDirection.PAY_FIXED), Decimal(0))
        receive_fixed_notional = sum((p.remaining_notional for p in self.get_open_positions() if p.direction == FixedFloatDirection.RECEIVE_FIXED), Decimal(0))
        return BorosBalance(
            net_value=self.realized_pnl + unrealized_pnl,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=unrealized_pnl,
            accrued_payment=accrued_payment,
            accrued_fees=accrued_fees,
            mark_to_maturity_value=mark_to_maturity_value,
            upfront_fixed_cost=sum((p.entry_upfront_fixed_cost for p in self.get_open_positions()), Decimal(0)),
            upfront_opening_fee_cost=sum((p.entry_opening_fee_cost for p in self.get_open_positions()), Decimal(0)),
            position_count=len(self.get_open_positions()),
            open_notional=pay_fixed_notional + receive_fixed_notional,
            pay_fixed_notional=pay_fixed_notional,
            receive_fixed_notional=receive_fixed_notional,
            current_mark_rate=current_mark_rate,
        )

    def formatted_str(self):
        balance = self.get_market_balance()
        return (
            get_formatted_predefined(f"{self.market_info.name}({type(self).__name__})", STYLE["header3"])
            + "\n"
            + get_formatted_from_dict(
                {
                    "venue": self.venue,
                    "maturity": self.maturity.isoformat() if self.maturity is not None else "",
                    "net_value": balance.net_value,
                    "realized_pnl": balance.realized_pnl,
                    "unrealized_pnl": balance.unrealized_pnl,
                    "position_count": str(balance.position_count),
                    "mark_rate": balance.current_mark_rate,
                }
            )
            + "\n"
        )

    def _resample(self, freq: str):
        resampled = self.data.resample(freq).last().ffill()
        for column in ["executed_size_abs", "executed_size_net"]:
            resampled[column] = resampled[column].apply(lambda value: value if pd.notna(value) else Decimal(0))
        for column in ["trade_count", "tx_count"]:
            resampled[column] = resampled[column].fillna(0).astype(int)
        self._data = resampled
        self._consumed_execution_rows = set()
        self._consumed_full_execution_rows = set()
        self._latest_f_time_to_maturity_cache = {}

    def peek_next_replay_execution(self, timestamp: datetime | pd.Timestamp):
        if len(self.tx_ledger.index) == 0:
            return None
        ts = pd.Timestamp(timestamp)
        eligible = self.tx_ledger.loc[self.tx_ledger["timestamp"] >= ts]
        if len(eligible.index) == 0:
            return None
        for row in eligible.itertuples():
            if row.Index not in self._consumed_execution_rows:
                return row
        return None

    def claim_next_replay_execution(self, timestamp: datetime | pd.Timestamp):
        row = self.peek_next_replay_execution(timestamp)
        if row is None:
            return None
        self._consumed_execution_rows.add(row.Index)
        return row

    def peek_next_full_execution(self, timestamp: datetime | pd.Timestamp):
        return self.peek_next_full_execution_scored(timestamp)

    def _full_execution_candidates(
        self,
        timestamp: datetime | pd.Timestamp,
        max_delay_seconds: int | None = None,
        required_trade_side: str | None = None,
    ) -> pd.DataFrame:
        if len(self.trade_ledger.index) == 0:
            return pd.DataFrame()
        ts = pd.Timestamp(timestamp)
        eligible = self.trade_ledger.loc[self.trade_ledger["timestamp"] >= ts]
        if max_delay_seconds is not None:
            eligible = eligible.loc[eligible["timestamp"] <= ts + pd.Timedelta(seconds=max_delay_seconds)]
        if len(eligible.index) == 0:
            return pd.DataFrame()
        if required_trade_side is not None:
            eligible = eligible.loc[eligible["trade_side"] == required_trade_side]
        if len(eligible.index) == 0:
            return pd.DataFrame()
        eligible = eligible.loc[~eligible.index.isin(self._consumed_full_execution_rows)]
        if len(eligible.index) == 0:
            return pd.DataFrame()
        earliest_timestamp = eligible["timestamp"].min()
        eligible = eligible.loc[eligible["timestamp"] == earliest_timestamp].copy()
        return eligible

    def peek_full_execution_quote(
        self,
        timestamp: datetime | pd.Timestamp,
        required_trade_side: str,
        prefer_higher_rate: bool,
        max_delay_seconds: int | None = None,
        include_opening_fee_rate: bool = True,
    ) -> dict | None:
        candidates = self._full_execution_candidates(
            timestamp=timestamp,
            max_delay_seconds=max_delay_seconds,
            required_trade_side=required_trade_side,
        )
        if len(candidates.index) == 0:
            return None

        def build_quote(group: pd.DataFrame) -> dict | None:
            weight_sum = sum((Decimal(value) for value in group["abs_size_total"]), Decimal(0))
            if weight_sum <= 0:
                return None

            weighted_fixed_rate = sum(
                (Decimal(row.abs_size_total) * Decimal(row.implied_rate) for row in group.itertuples()),
                Decimal(0),
            ) / weight_sum
            weighted_opening_fee_rate = sum(
                (
                    Decimal(row.abs_size_total)
                    * (Decimal(row.opening_fee_rate_annualized) if pd.notna(row.opening_fee_rate_annualized) else Decimal(0))
                    for row in group.itertuples()
                ),
                Decimal(0),
            ) / weight_sum
            execution_fee_paid = sum((Decimal(row.fee_paid) for row in group.itertuples()), Decimal(0))
            time_to_mat = self._latest_f_time_to_maturity_seconds_asof(group.iloc[0]["timestamp"])
            execution_fee_rate = Decimal(0)
            if execution_fee_paid > 0 and time_to_mat > 0:
                execution_fee_rate = execution_fee_paid * Decimal(PMath.ONE_YEAR) / (weight_sum * Decimal(time_to_mat))
            source_kinds = sorted(set(group["source_kind"]))
            if len(source_kinds) == 1:
                execution_source = f"{source_kinds[0]}_fill"
            else:
                execution_source = "split_fill"

            opening_fee_rate = weighted_opening_fee_rate if include_opening_fee_rate else Decimal(0)
            effective_rate = (
                weighted_fixed_rate - opening_fee_rate - execution_fee_rate
                if prefer_higher_rate
                else weighted_fixed_rate + opening_fee_rate + execution_fee_rate
            )
            return {
                "fixed_rate": weighted_fixed_rate,
                "execution_fee_paid": execution_fee_paid,
                "execution_fee_rate_annualized": execution_fee_rate,
                "execution_opening_fee_rate": opening_fee_rate,
                "execution_timestamp": group.iloc[0]["timestamp"].to_pydatetime(),
                "execution_tx_hash": group.iloc[0]["tx_hash"],
                "execution_source": execution_source,
                "available_abs_size_total": weight_sum,
                "_effective_rate": effective_rate,
                "_candidate_indices": list(group.index),
            }

        quote_options: list[dict] = []
        for _, source_group in candidates.groupby("source_kind", sort=True):
            quote = build_quote(source_group.copy())
            if quote is not None:
                quote_options.append(quote)
        if candidates["source_kind"].nunique() > 1:
            split_quote = build_quote(candidates.copy())
            if split_quote is not None:
                quote_options.append(split_quote)
        if not quote_options:
            return None

        quote_options.sort(
            key=lambda quote: (
                quote["_effective_rate"],
                -quote["available_abs_size_total"],
                quote["execution_fee_paid"],
                quote["execution_source"] == "split_fill",
            ),
            reverse=prefer_higher_rate,
        )
        quote_options_summary = [
            {
                "execution_source": quote["execution_source"],
                "effective_rate": str(quote["_effective_rate"]),
                "fixed_rate": str(quote["fixed_rate"]),
                "execution_opening_fee_rate": str(quote["execution_opening_fee_rate"]),
                "execution_fee_rate_annualized": str(quote["execution_fee_rate_annualized"]),
                "execution_fee_paid": str(quote["execution_fee_paid"]),
                "available_abs_size_total": str(quote["available_abs_size_total"]),
            }
            for quote in quote_options
        ]
        best_quote = quote_options[0]
        best_quote["execution_option_count"] = len(quote_options)
        best_quote["execution_selection_reason"] = (
            "only_available_quote" if len(quote_options) == 1 else "selected_best_all_in_rate"
        )
        best_quote["execution_quote_options_json"] = json.dumps(quote_options_summary, sort_keys=True)
        return best_quote

    def claim_full_execution_quote(
        self,
        timestamp: datetime | pd.Timestamp,
        required_trade_side: str,
        prefer_higher_rate: bool,
        max_delay_seconds: int | None = None,
        include_opening_fee_rate: bool = True,
    ) -> dict | None:
        quote = self.peek_full_execution_quote(
            timestamp=timestamp,
            required_trade_side=required_trade_side,
            prefer_higher_rate=prefer_higher_rate,
            max_delay_seconds=max_delay_seconds,
            include_opening_fee_rate=include_opening_fee_rate,
        )
        if quote is None:
            return None
        self._consumed_full_execution_rows.update(quote["_candidate_indices"])
        return quote

    def peek_next_full_execution_scored(
        self,
        timestamp: datetime | pd.Timestamp,
        prefer_higher_rate: bool | None = None,
        max_delay_seconds: int | None = None,
        include_opening_fee_rate: bool = True,
    ):
        candidates = self._full_execution_candidates(timestamp=timestamp, max_delay_seconds=max_delay_seconds)
        if len(candidates.index) == 0:
            return None
        if prefer_higher_rate is None:
            return next(candidates.sort_values(["timestamp", "log_index"]).itertuples())

        def effective_rate(row: pd.Series) -> Decimal:
            implied_rate = Decimal(row["implied_rate"])
            opening_fee_rate = (
                Decimal(row["opening_fee_rate_annualized"])
                if include_opening_fee_rate and pd.notna(row["opening_fee_rate_annualized"])
                else Decimal(0)
            )
            return implied_rate - opening_fee_rate if prefer_higher_rate else implied_rate + opening_fee_rate

        candidates["_effective_rate"] = candidates.apply(effective_rate, axis=1)
        candidates["_fee_paid"] = candidates["fee_paid"].apply(Decimal)
        candidates = candidates.sort_values(
            by=["_effective_rate", "_fee_paid", "log_index"],
            ascending=[not prefer_higher_rate, True, True],
        )
        return next(candidates.itertuples())

    def claim_next_full_execution(
        self,
        timestamp: datetime | pd.Timestamp,
        prefer_higher_rate: bool | None = None,
        max_delay_seconds: int | None = None,
        include_opening_fee_rate: bool = True,
    ):
        row = self.peek_next_full_execution_scored(
            timestamp=timestamp,
            prefer_higher_rate=prefer_higher_rate,
            max_delay_seconds=max_delay_seconds,
            include_opening_fee_rate=include_opening_fee_rate,
        )
        if row is None:
            return None
        self._consumed_full_execution_rows.add(row.Index)
        return row

    def load_data(
        self,
        trade_path: str,
        log_path: str,
        venue: str,
        maturity: date | datetime,
        resample_rule: str = "1min",
        validate_logs: bool = True,
    ):
        self._data = load_boros_data(
            trade_path=trade_path,
            log_path=log_path,
            market_name=self.market_info.name,
            venue=venue,
            maturity=maturity,
            resample_rule=resample_rule,
            validate_logs=validate_logs,
        )
        self.tx_ledger = load_boros_tx_ledger(trade_path=trade_path, log_path=log_path, validate_logs=validate_logs)
        self.trade_ledger = pd.DataFrame()
        self.event_ledger = pd.DataFrame()
        self.venue = venue
        self.maturity = pd.Timestamp(self._data["maturity"].iloc[0])
        self._consumed_execution_rows = set()
        self._consumed_full_execution_rows = set()
        self._latest_f_time_to_maturity_cache = {}
        self.mark_rate_column = "mark_rate"

    def load_event_data(
        self,
        event_dir: str,
        market_key: str,
        venue: str,
        maturity: date | datetime,
        resample_rule: str = "1min",
        default_opening_fee_rate: Decimal = Decimal(0),
    ):
        data, event_ledger, tx_ledger = load_boros_event_data(
            event_dir=event_dir,
            market_key=market_key,
            venue=venue,
            maturity=maturity,
            resample_rule=resample_rule,
            default_opening_fee_rate=default_opening_fee_rate,
        )
        self._data = data
        self.event_ledger = event_ledger
        self.tx_ledger = tx_ledger
        from .helper import load_boros_event_trade_ledger

        self.trade_ledger = load_boros_event_trade_ledger(event_dir=event_dir, market_key=market_key, maturity=maturity)
        self.venue = venue
        self.maturity = pd.Timestamp(self._data["maturity"].iloc[0])
        self._consumed_execution_rows = set()
        self._consumed_full_execution_rows = set()
        self._latest_f_time_to_maturity_cache = {}
        self.mark_rate_column = "mark_rate"

    def get_price_from_data(self) -> pd.DataFrame:
        return get_price_from_data(self.data)
