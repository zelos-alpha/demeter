import json
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path

import pandas as pd

from .._typing import DemeterError
from ..utils import to_decimal
from .PMath import PMath


def _normalize_maturity(maturity: date | datetime) -> pd.Timestamp:
    if isinstance(maturity, datetime):
        ts = pd.Timestamp(maturity)
        return ts.tz_localize(None) if ts.tzinfo else ts
    return pd.Timestamp(datetime.combine(maturity, time(23, 59)))


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
    result["floating_index"] = floating_indices
    result["fee_index"] = fee_indices
    result["opening_fee_rate_annualized_proxy"] = Decimal(0)

    if result["mark_rate"].isna().any():
        raise DemeterError(f"Unable to build mark_rate series from {trade_path}")
    return result


def get_price_from_data(data: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(index=data.index)
