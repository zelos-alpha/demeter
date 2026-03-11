import ast
import json
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import pandas as pd

from .._typing import DemeterError
from ..utils import to_decimal
from .PMath import PMath

SIZE_SCALE = Decimal("1e18")
TRADE_VALUE_SCALE = Decimal("1e19")
EVENT_KIND_ORDERBOOK = "orderbook"
EVENT_KIND_AMM = "amm"

ORDERBOOK_TOPIC_MAP = {
    "0x7a1823ff8473ae353f7ac7587b085e7544b1e3cc8f87c33c504af60fe5111471": "limit_order_placed",
    "0x2c85ce2db412cbd774172130804b8f3851259af67fb84249f5d0254031be8116": "limit_order_cancelled",
    "0x8b1ba40288a7ae7a8dff44ed28d9e1f2d04e0df0a75ee02a6ed2aa9529696f66": "limit_order_forced_cancelled",
    "0x48dc6d310fa6f4ef65aacba36e1aad2df2296c7024eb71845d8e2b7c76c6e852": "limit_order_partially_filled",
    "0x4dd6c06b2aacc3dcdf47336de46618f3c502752339f73dc5d9b6ccb52a15a916": "limit_order_filled",
    "0x02bab1fddd0d69675bb484195c44cfcb7ee30600f166c947e573b757665587c4": "market_orders_filled",
    "0xadb7ee2a2cab5fa33ce9a74433c0700099a72877d67b06a9c249a97d184aef9a": "oob_orders_purged",
    "0x589ac0c8263878a0b9876e05d3c1df33ee0680818e7ba8df67d9163342e57e55": "findex_updated",
}

AMM_TOPIC_MAP = {
    "0x89a302decbf25a038eb274f71951f4be62b45c4e96bdf6e4f3bb246770a24bd4": "mint",
    "0xa4d3bfbe6e7fe6b8d6c00f6cc61e2087b14a629095e6afdd82cb7842c457d770": "burn",
    "0x15391ef1cdeab4c973414c6652cf113cb3c8d26819a60aaebaae91bcb82c83da": "swap",
    "0x208f1b468d3d61f0f085e975bd9d04367c930d599642faad06695229f3eadcd8": "fee_rate_updated",
    "0x49465dfaf65a9f995d83e80aaabd038e108086e61a6215bd725f698586d5a223": "amm_config_updated",
}


def _normalize_maturity(maturity: date | datetime) -> pd.Timestamp:
    if isinstance(maturity, datetime):
        ts = pd.Timestamp(maturity)
        return ts.tz_localize(None) if ts.tzinfo else ts
    return pd.Timestamp(datetime.combine(maturity, time(23, 59)))


def _hex_words(data: str) -> list[str]:
    payload = data[2:] if data.startswith("0x") else data
    if len(payload) % 64 != 0:
        raise DemeterError(f"Unexpected hex payload length: {len(payload)}")
    return [payload[index : index + 64] for index in range(0, len(payload), 64)]


def _parse_signed_int(hex_word: str, bits: int) -> int:
    value = int(hex_word, 16)
    if value >= 1 << (bits - 1):
        value -= 1 << bits
    return value


def _parse_signed_256(hex_word: str) -> Decimal:
    return Decimal(_parse_signed_int(hex_word, 256))


def _parse_unsigned_256(hex_word: str) -> Decimal:
    return Decimal(int(hex_word, 16))


def _parse_two_signed_128(hex_word: str) -> tuple[Decimal, Decimal]:
    return Decimal(_parse_signed_int(hex_word[:32], 128)), Decimal(_parse_signed_int(hex_word[32:], 128))


def _to_decimal_size(raw_value: Decimal) -> Decimal:
    return raw_value / SIZE_SCALE


def _to_decimal_trade_value(raw_value: Decimal) -> Decimal:
    return raw_value / TRADE_VALUE_SCALE


def _safe_topics(value: str) -> list[str]:
    parsed = ast.literal_eval(value)
    if not isinstance(parsed, list):
        raise DemeterError(f"Invalid topics payload: {value}")
    return parsed


def _classify_topic(source_kind: str, topic0: str) -> str:
    mapping = ORDERBOOK_TOPIC_MAP if source_kind == EVENT_KIND_ORDERBOOK else AMM_TOPIC_MAP
    return mapping.get(topic0, "unknown")


def _normalize_market_key(file_stem: str, source_kind: str) -> str:
    parts = file_stem.split("-")
    if len(parts) >= 4 and all(part.isdigit() for part in parts[-3:]):
        prefix = "-".join(parts[:-3])
    else:
        prefix = "-".join(parts[:-1])
    if source_kind == EVENT_KIND_AMM and prefix.startswith("AMM-"):
        return prefix.removeprefix("AMM-")
    return prefix


def _read_event_csv(file_path: Path, source_kind: str) -> pd.DataFrame | None:
    required_columns = {"block_timestamp", "transaction_hash", "address", "log_index", "data", "topics"}
    frame = pd.read_csv(file_path)
    missing = required_columns - set(frame.columns)
    if missing:
        raise DemeterError(f"Missing columns in {file_path}: {sorted(missing)}")
    if len(frame.index) == 0:
        return None

    timestamps = pd.to_datetime(frame["block_timestamp"], utc=True).dt.tz_localize(None)
    topics = frame["topics"].apply(_safe_topics)
    topic0 = topics.apply(lambda values: values[0] if values else "")
    market_key = _normalize_market_key(file_path.stem, source_kind)
    day = file_path.stem.split("-")[-1]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "market_key": market_key,
            "source_kind": source_kind,
            "tx_hash": frame["transaction_hash"],
            "address": frame["address"],
            "log_index": frame["log_index"].astype(int),
            "raw_data": frame["data"],
            "raw_topics": topics,
            "topic0": topic0,
            "event_type": topic0.apply(lambda value: _classify_topic(source_kind, value)),
            "file_day": day,
        }
    )


def load_boros_event_ledger(event_dir: str, market_key: str | None = None, source_kind: str | None = None) -> pd.DataFrame:
    root = Path(event_dir)
    if not root.exists():
        raise DemeterError(f"Event directory not found: {event_dir}")

    frames: list[pd.DataFrame] = []
    selected_kinds = [EVENT_KIND_ORDERBOOK, EVENT_KIND_AMM] if source_kind is None else [source_kind]
    for kind in selected_kinds:
        folders = [root / kind]
        if kind == EVENT_KIND_AMM:
            folders.append(root / "liquidity")
        for folder in folders:
            if not folder.exists():
                continue
            for file_path in sorted(folder.glob("*.csv")):
                frame = _read_event_csv(file_path, kind)
                if frame is None:
                    continue
                if market_key is None or frame["market_key"].iloc[0] == market_key:
                    frames.append(frame)

    if not frames:
        raise DemeterError(f"No Boros event files found for market_key={market_key} source_kind={source_kind}")

    result = pd.concat(frames, ignore_index=True)
    return result.sort_values(["timestamp", "tx_hash", "log_index"]).reset_index(drop=True)


def _decode_market_orders_filled(raw_data: str) -> dict[str, Decimal]:
    words = _hex_words(raw_data)
    if len(words) < 3:
        raise DemeterError("market_orders_filled payload is too short")
    signed_size_raw, signed_trade_value_raw = _parse_two_signed_128(words[1])
    fee_raw = _parse_unsigned_256(words[2])
    signed_size = _to_decimal_size(signed_size_raw)
    signed_trade_value = _to_decimal_trade_value(signed_trade_value_raw)
    fee_paid = _to_decimal_trade_value(fee_raw)
    return {
        "signed_size": signed_size,
        "signed_trade_value": signed_trade_value,
        "fee_paid": fee_paid,
    }


def _decode_amm_swap(raw_data: str) -> dict[str, Decimal]:
    words = _hex_words(raw_data)
    if len(words) < 2:
        raise DemeterError("swap payload is too short")
    signed_size = _to_decimal_size(_parse_signed_256(words[0]))
    signed_trade_value = _to_decimal_trade_value(_parse_signed_256(words[1]))
    fee_paid = Decimal(0)
    if len(words) > 2:
        fee_paid = _to_decimal_trade_value(_parse_unsigned_256(words[2]))
    return {
        "signed_size": signed_size,
        "signed_trade_value": signed_trade_value,
        "fee_paid": fee_paid,
    }


def _build_decoded_trade_rows(event_ledger: pd.DataFrame, maturity: date | datetime) -> pd.DataFrame:
    maturity_ts = _normalize_maturity(maturity)
    rows: list[dict] = []
    for row in event_ledger.itertuples():
        decoded: dict[str, Decimal] | None = None
        if row.event_type == "market_orders_filled":
            decoded = _decode_market_orders_filled(row.raw_data)
        elif row.event_type == "swap":
            decoded = _decode_amm_swap(row.raw_data)
        if decoded is None:
            continue

        signed_size = decoded["signed_size"]
        signed_trade_value = decoded["signed_trade_value"]
        fee_paid = decoded["fee_paid"]
        abs_size = abs(signed_size)
        time_to_mat = max(0, int((maturity_ts - row.timestamp).total_seconds()))
        implied_rate = Decimal(0)
        if abs_size > 0 and time_to_mat > 0:
            implied_rate = abs(signed_trade_value) * Decimal(PMath.ONE_YEAR) / (abs_size * Decimal(time_to_mat))
        rows.append(
            {
                "timestamp": row.timestamp,
                "minute": row.timestamp.floor("1min"),
                "market_key": row.market_key,
                "source_kind": row.source_kind,
                "tx_hash": row.tx_hash,
                "log_index": int(row.log_index),
                "event_type": row.event_type,
                "signed_size_net": signed_size,
                "abs_size_total": abs_size,
                "signed_trade_value": signed_trade_value,
                "abs_trade_value": abs(signed_trade_value),
                "fee_paid": fee_paid,
                "implied_rate": implied_rate,
                "time_to_maturity_seconds": time_to_mat,
            }
        )
    if not rows:
        raise DemeterError("Unable to decode trade events from Boros event ledger")
    return pd.DataFrame(rows).sort_values(["timestamp", "tx_hash", "log_index"]).reset_index(drop=True)


def _build_event_tx_ledger(trade_ledger: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for tx_hash, group in trade_ledger.groupby(["market_key", "tx_hash"], sort=True):
        market_key, tx_hash_value = tx_hash
        abs_size_total = sum(group["abs_size_total"], Decimal(0))
        abs_trade_value = sum(group["abs_trade_value"], Decimal(0))
        weighted_sum = sum((row.abs_size_total * row.implied_rate for row in group.itertuples()), Decimal(0))
        rows.append(
            {
                "market_key": market_key,
                "tx_hash": tx_hash_value,
                "timestamp": group["timestamp"].iloc[0],
                "minute": group["minute"].iloc[0],
                "source_kind": group["source_kind"].iloc[-1],
                "fill_count": int(len(group.index)),
                "signed_size_net": sum(group["signed_size_net"], Decimal(0)),
                "abs_size_total": abs_size_total,
                "signed_trade_value": sum(group["signed_trade_value"], Decimal(0)),
                "abs_trade_value": abs_trade_value,
                "fee_paid": sum(group["fee_paid"], Decimal(0)),
                "trade_rate_vwap": weighted_sum / abs_size_total if abs_size_total else Decimal(0),
                "implied_rate": weighted_sum / abs_size_total if abs_size_total else Decimal(0),
            }
        )
    result = pd.DataFrame(rows)
    source_priority = {EVENT_KIND_ORDERBOOK: 0, EVENT_KIND_AMM: 1}
    result["source_priority"] = result["source_kind"].map(source_priority).fillna(9)
    result = result.sort_values(["timestamp", "source_priority", "tx_hash"]).reset_index(drop=True)
    return result.drop(columns=["source_priority"])


def load_boros_event_trade_ledger(event_dir: str, market_key: str, maturity: date | datetime) -> pd.DataFrame:
    event_ledger = load_boros_event_ledger(event_dir=event_dir, market_key=market_key)
    return _build_decoded_trade_rows(event_ledger=event_ledger, maturity=maturity)


def load_boros_event_tx_ledger(event_dir: str, market_key: str, maturity: date | datetime) -> pd.DataFrame:
    trade_ledger = load_boros_event_trade_ledger(event_dir=event_dir, market_key=market_key, maturity=maturity)
    return _build_event_tx_ledger(trade_ledger)


def _build_state_frame(
    event_ledger: pd.DataFrame,
    trade_ledger: pd.DataFrame,
    maturity: date | datetime,
    default_opening_fee_rate: Decimal,
) -> pd.DataFrame:
    maturity_ts = _normalize_maturity(maturity)
    start_timestamp = min(event_ledger["timestamp"].min(), trade_ledger["timestamp"].min())
    findex_events = event_ledger.loc[event_ledger["event_type"] == "findex_updated", ["timestamp"]].drop_duplicates().sort_values("timestamp")
    fee_events = event_ledger.loc[event_ledger["event_type"] == "fee_rate_updated", ["timestamp", "raw_data"]].sort_values("timestamp")

    boundaries = [start_timestamp]
    boundaries.extend(list(findex_events["timestamp"]))
    boundaries = sorted(set(boundaries))
    fee_rate = Decimal(default_opening_fee_rate)
    fee_event_iter = list(fee_events.itertuples())
    fee_pointer = 0
    trade_rows = list(trade_ledger.sort_values("timestamp").itertuples())
    trade_pointer = 0
    current_rate = trade_rows[0].implied_rate if trade_rows else Decimal(0)
    last_trade_timestamp = start_timestamp
    floating_index = Decimal(0)
    fee_index = Decimal(0)
    rows: list[dict] = []

    for boundary in boundaries:
        while fee_pointer < len(fee_event_iter) and fee_event_iter[fee_pointer].timestamp <= boundary:
            raw_words = _hex_words(fee_event_iter[fee_pointer].raw_data)
            if raw_words:
                fee_rate = _parse_unsigned_256(raw_words[0]) / SIZE_SCALE
            fee_pointer += 1

        while trade_pointer < len(trade_rows) and trade_rows[trade_pointer].timestamp <= boundary:
            trade = trade_rows[trade_pointer]
            delta_seconds = int((trade.timestamp - last_trade_timestamp).total_seconds())
            if delta_seconds > 0:
                floating_index += current_rate * Decimal(delta_seconds) / Decimal(PMath.ONE_YEAR)
                fee_index += fee_rate * Decimal(delta_seconds) / Decimal(PMath.ONE_YEAR)
            current_rate = trade.implied_rate
            last_trade_timestamp = trade.timestamp
            trade_pointer += 1

        if boundary > last_trade_timestamp:
            delta_seconds = int((boundary - last_trade_timestamp).total_seconds())
            floating_index += current_rate * Decimal(delta_seconds) / Decimal(PMath.ONE_YEAR)
            fee_index += fee_rate * Decimal(delta_seconds) / Decimal(PMath.ONE_YEAR)
            last_trade_timestamp = boundary

        rows.append(
            {
                "latest_f_time_timestamp": boundary,
                "floating_index": floating_index,
                "fee_index": fee_index,
                "opening_fee_rate_annualized_proxy": fee_rate,
                "time_to_maturity_seconds": max(0, int((maturity_ts - boundary).total_seconds())),
            }
        )

    return pd.DataFrame(rows).sort_values("latest_f_time_timestamp").reset_index(drop=True)


def load_boros_event_data(
    event_dir: str,
    market_key: str,
    venue: str,
    maturity: date | datetime,
    resample_rule: str = "1min",
    default_opening_fee_rate: Decimal = Decimal(0),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    event_ledger = load_boros_event_ledger(event_dir=event_dir, market_key=market_key)
    trade_ledger = _build_decoded_trade_rows(event_ledger=event_ledger, maturity=maturity)
    tx_ledger = _build_event_tx_ledger(trade_ledger=trade_ledger)
    state_frame = _build_state_frame(
        event_ledger=event_ledger,
        trade_ledger=trade_ledger,
        maturity=maturity,
        default_opening_fee_rate=default_opening_fee_rate,
    )

    rows: list[dict] = []
    for minute, group in trade_ledger.groupby("minute", sort=True):
        abs_size_total = sum(group["abs_size_total"], Decimal(0))
        abs_trade_value = sum(group["abs_trade_value"], Decimal(0))
        weighted_rate_sum = sum((row.abs_size_total * row.implied_rate for row in group.itertuples()), Decimal(0))
        mark_rate = weighted_rate_sum / abs_size_total if abs_size_total else Decimal(0)
        rows.append(
            {
                "timestamp": minute,
                "trade_rate_last": group["implied_rate"].iloc[-1],
                "trade_rate_vwap": mark_rate,
                "mark_rate": mark_rate,
                "executed_size_abs": abs_size_total,
                "executed_size_net": sum(group["signed_size_net"], Decimal(0)),
                "trade_count": int(len(group.index)),
                "tx_count": int(group["tx_hash"].nunique()),
                "abs_trade_value": abs_trade_value,
                "fee_paid": sum(group["fee_paid"], Decimal(0)),
            }
        )
    data = pd.DataFrame(rows).set_index("timestamp").sort_index()

    full_index = pd.date_range(data.index.min(), data.index.max(), freq=resample_rule)
    data = data.reindex(full_index)
    data.index.name = "timestamp"
    data["mark_rate"] = data["mark_rate"].ffill()
    data["trade_rate_last"] = data["trade_rate_last"].ffill()
    data["trade_rate_vwap"] = data["trade_rate_vwap"].ffill()
    for column in ["executed_size_abs", "executed_size_net", "abs_trade_value", "fee_paid"]:
        data[column] = data[column].apply(lambda value: value if pd.notna(value) else Decimal(0))
    for column in ["trade_count", "tx_count"]:
        data[column] = data[column].fillna(0).astype(int)

    merged_state = pd.merge_asof(
        pd.DataFrame({"timestamp": data.index}).sort_values("timestamp"),
        state_frame.sort_values("latest_f_time_timestamp"),
        left_on="timestamp",
        right_on="latest_f_time_timestamp",
        direction="backward",
    )
    maturity_ts = _normalize_maturity(maturity)
    time_deltas = [0]
    for index in range(1, len(data.index)):
        time_deltas.append(int((data.index[index] - data.index[index - 1]).total_seconds()))

    data["market_name"] = market_key
    data["venue"] = venue
    data["maturity"] = maturity_ts
    data["time_delta_seconds"] = time_deltas
    data["time_to_maturity_seconds"] = [max(0, int((maturity_ts - timestamp).total_seconds())) for timestamp in data.index]
    data["latest_f_time"] = list(merged_state["latest_f_time_timestamp"].fillna(data.index[0]))
    data["floating_index"] = list(merged_state["floating_index"].fillna(Decimal(0)))
    data["fee_index"] = list(merged_state["fee_index"].fillna(Decimal(0)))
    data["opening_fee_rate_annualized_proxy"] = list(
        merged_state["opening_fee_rate_annualized_proxy"].fillna(Decimal(default_opening_fee_rate))
    )

    if data["mark_rate"].isna().any():
        raise DemeterError(f"Unable to build mark_rate series from {market_key} event files")
    return data, event_ledger, tx_ledger


def _load_log_tx_hashes(log_path: str) -> set[str]:
    tx_hashes: set[str] = set()
    with open(log_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            events = json.loads(line)
            if not isinstance(events, list):
                raise DemeterError(f"Each line in {log_path} must be a JSON array")
            for event in events:
                tx_hash = event.get("transactionHash")
                if tx_hash:
                    tx_hashes.add(tx_hash)
    return tx_hashes


def _load_trade_frame(trade_path: str, log_path: str, validate_logs: bool = True) -> pd.DataFrame:
    required_columns = {"size", "rate", "txHash", "blockTimestamp"}
    trade_path = str(Path(trade_path))
    log_path = str(Path(log_path))
    if not Path(trade_path).exists():
        raise DemeterError(f"Trade file not found: {trade_path}")
    if validate_logs and not Path(log_path).exists():
        raise DemeterError(f"Log file not found: {log_path}")

    data = pd.read_csv(trade_path, converters={"size": to_decimal, "rate": to_decimal})
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        raise DemeterError(f"Missing columns in {trade_path}: {sorted(missing_columns)}")
    if len(data.index) == 0:
        raise DemeterError(f"Trade file is empty: {trade_path}")

    if validate_logs:
        log_tx_hashes = _load_log_tx_hashes(log_path)
        missing_tx_hashes = sorted(set(data["txHash"]) - log_tx_hashes)
        if missing_tx_hashes:
            raise DemeterError(f"{trade_path} contains txHash values missing from logs: {missing_tx_hashes[:5]}")

    timestamps = pd.to_datetime(data["blockTimestamp"], unit="s", utc=True).dt.tz_localize(None)
    return data.assign(timestamp=timestamps).sort_values(["timestamp", "txHash"]).reset_index(drop=True)


def _build_minute_row(group: pd.DataFrame) -> dict:
    abs_sizes = [abs(size) for size in group["size"]]
    total_abs_size = sum(abs_sizes, Decimal(0))
    weighted_sum = sum((abs(size) * rate for size, rate in zip(group["size"], group["rate"])), Decimal(0))
    trade_rate_vwap = weighted_sum / total_abs_size if total_abs_size else group["rate"].iloc[-1]
    return {
        "trade_rate_last": group["rate"].iloc[-1],
        "trade_rate_vwap": trade_rate_vwap,
        "mark_rate": trade_rate_vwap,
        "executed_size_abs": total_abs_size,
        "executed_size_net": sum(group["size"], Decimal(0)),
        "trade_count": len(group),
        "tx_count": group["txHash"].nunique(),
    }


def load_boros_tx_ledger(
    trade_path: str,
    log_path: str,
    validate_logs: bool = True,
) -> pd.DataFrame:
    trade_frame = _load_trade_frame(trade_path=trade_path, log_path=log_path, validate_logs=validate_logs)
    rows: list[dict] = []
    for tx_hash, group in trade_frame.groupby("txHash", sort=True):
        abs_size_total = sum((abs(size) for size in group["size"]), Decimal(0))
        weighted_sum = sum((abs(size) * rate for size, rate in zip(group["size"], group["rate"])), Decimal(0))
        rows.append(
            {
                "tx_hash": tx_hash,
                "timestamp": group["timestamp"].iloc[0],
                "minute": group["timestamp"].iloc[0].floor("1min"),
                "fill_count": int(len(group.index)),
                "signed_size_net": sum(group["size"], Decimal(0)),
                "abs_size_total": abs_size_total,
                "signed_trade_value": sum((size * rate for size, rate in zip(group["size"], group["rate"])), Decimal(0)),
                "trade_rate_first": group["rate"].iloc[0],
                "trade_rate_last": group["rate"].iloc[-1],
                "trade_rate_vwap": weighted_sum / abs_size_total if abs_size_total else group["rate"].iloc[-1],
            }
        )
    return pd.DataFrame(rows).sort_values(["timestamp", "tx_hash"]).reset_index(drop=True)


def _build_tx_indices(tx_ledger: pd.DataFrame, floating_fee_rate: Decimal) -> pd.DataFrame:
    if len(tx_ledger.index) == 0:
        return pd.DataFrame(columns=["timestamp", "floating_index", "fee_index", "trade_rate_vwap"])

    rows: list[dict] = []
    cumulative_floating = Decimal(0)
    cumulative_fee = Decimal(0)
    previous_timestamp = None
    previous_rate = None
    for row in tx_ledger.sort_values(["timestamp", "tx_hash"]).itertuples():
        if previous_timestamp is not None and previous_rate is not None:
            delta_seconds = int((row.timestamp - previous_timestamp).total_seconds())
            if delta_seconds > 0:
                cumulative_floating += previous_rate * Decimal(delta_seconds) / Decimal(PMath.ONE_YEAR)
                cumulative_fee += floating_fee_rate * Decimal(delta_seconds) / Decimal(PMath.ONE_YEAR)
        rows.append(
            {
                "timestamp": row.timestamp,
                "floating_index": cumulative_floating,
                "fee_index": cumulative_fee,
                "trade_rate_vwap": row.trade_rate_vwap,
            }
        )
        previous_timestamp = row.timestamp
        previous_rate = row.trade_rate_vwap
    return pd.DataFrame(rows)


def _index_as_of(timestamp: pd.Timestamp, tx_indices: pd.DataFrame, floating_fee_rate: Decimal) -> tuple[Decimal, Decimal]:
    eligible = tx_indices.loc[tx_indices["timestamp"] <= timestamp]
    if len(eligible.index) == 0:
        return Decimal(0), Decimal(0)
    last_row = eligible.iloc[-1]
    delta_seconds = int((timestamp - last_row["timestamp"]).total_seconds())
    floating_index = last_row["floating_index"]
    fee_index = last_row["fee_index"]
    if delta_seconds > 0:
        floating_index += last_row["trade_rate_vwap"] * Decimal(delta_seconds) / Decimal(PMath.ONE_YEAR)
        fee_index += floating_fee_rate * Decimal(delta_seconds) / Decimal(PMath.ONE_YEAR)
    return floating_index, fee_index


def load_boros_data(
    trade_path: str,
    log_path: str,
    market_name: str,
    venue: str,
    maturity: date | datetime,
    resample_rule: str = "1min",
    validate_logs: bool = True,
    floating_fee_rate: Decimal = Decimal(0),
) -> pd.DataFrame:
    data = _load_trade_frame(trade_path=trade_path, log_path=log_path, validate_logs=validate_logs)
    tx_ledger = load_boros_tx_ledger(trade_path=trade_path, log_path=log_path, validate_logs=validate_logs)

    rows = []
    for minute, group in data.groupby(data["timestamp"].dt.floor(resample_rule), sort=True):
        row = _build_minute_row(group)
        row["timestamp"] = minute
        rows.append(row)
    result = pd.DataFrame(rows).set_index("timestamp").sort_index()

    full_index = pd.date_range(result.index.min(), result.index.max(), freq=resample_rule)
    result = result.reindex(full_index)
    result.index.name = "timestamp"
    result["mark_rate"] = result["mark_rate"].ffill()
    result["trade_rate_last"] = result["trade_rate_last"].ffill()
    result["trade_rate_vwap"] = result["trade_rate_vwap"].ffill()

    for column in ["executed_size_abs", "executed_size_net"]:
        result[column] = result[column].apply(lambda value: value if pd.notna(value) else Decimal(0))
    for column in ["trade_count", "tx_count"]:
        result[column] = result[column].fillna(0).astype(int)

    tx_indices = _build_tx_indices(tx_ledger=tx_ledger, floating_fee_rate=floating_fee_rate)
    floating_indices: list[Decimal] = []
    fee_indices: list[Decimal] = []
    time_deltas: list[int] = [0]
    for index, timestamp in enumerate(result.index):
        if index > 0:
            time_deltas.append(int((timestamp - result.index[index - 1]).total_seconds()))
        floating_index, fee_index = _index_as_of(timestamp, tx_indices, floating_fee_rate)
        floating_indices.append(floating_index)
        fee_indices.append(fee_index)

    maturity_ts = _normalize_maturity(maturity)
    result["market_name"] = market_name
    result["venue"] = venue
    result["maturity"] = maturity_ts
    result["time_delta_seconds"] = time_deltas
    result["time_to_maturity_seconds"] = [max(0, int((maturity_ts - timestamp).total_seconds())) for timestamp in result.index]
    result["latest_f_time"] = list(result.index)
    result["floating_index"] = floating_indices
    result["fee_index"] = fee_indices
    result["opening_fee_rate_annualized_proxy"] = Decimal(0)

    if result["mark_rate"].isna().any():
        raise DemeterError(f"Unable to build mark_rate series from {trade_path}")
    return result


def get_price_from_data(data: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(index=data.index)
