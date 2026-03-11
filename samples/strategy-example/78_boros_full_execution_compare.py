from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demeter.boros_v4 import BorosExecutionMode, run_funding_convergence_backtest


EVENT_DIR = ROOT / "bn_hl_260121-260226"
OUTPUT_ROOT = ROOT / "outputs" / "boros_full_execution_compare"
COMMON_ARGS = dict(
    event_dir=str(EVENT_DIR),
    market_a_name="binance_feb27",
    market_b_name="hyperliquid_feb27",
    market_a_key="BINANCE-ETHUSDT-27FEB2026",
    market_b_key="HYPERLIQUID-ETH-27FEB2026",
    venue_a="BINANCE",
    venue_b="HYPERLIQUID",
    maturity=datetime(2026, 2, 27, 0, 0, 0),
    notional=Decimal("100"),
    lookback=60,
    entry_threshold=Decimal("0.004"),
    exit_threshold=Decimal("0.001"),
    stop_loss=Decimal("5"),
    min_time_to_maturity_seconds=24 * 3600,
    max_signal_rate=Decimal("2"),
    expected_holding_seconds=2 * 3600,
    min_expected_edge_after_cost=Decimal("0.02"),
    max_execution_delay_seconds=15 * 60,
    max_pair_execution_skew_seconds=5 * 60,
)


def run_mode(name: str, execution_mode: BorosExecutionMode) -> dict:
    output_dir = OUTPUT_ROOT / name
    started = perf_counter()
    actuator, strategy, markets = run_funding_convergence_backtest(
        output_dir=str(output_dir),
        execution_mode=execution_mode,
        **COMMON_ARGS,
    )
    runtime_seconds = perf_counter() - started
    with open(output_dir / "summary.json", "r", encoding="utf-8") as file:
        summary = json.load(file)
    spread_df = pd.DataFrame(strategy.spread_history)
    return {
        "name": name,
        "execution_mode": execution_mode.value,
        "runtime_seconds": runtime_seconds,
        "final_net_value": Decimal(summary["final_net_value"]),
        "total_pnl": Decimal(summary["total_pnl"]),
        "action_count": int(summary["action_count"]),
        "mark_rate_model": summary["mark_rate_model"],
        "protocol_alignment_mode": summary["protocol_alignment_mode"],
        "signal_ready_count": int(summary["signal_ready_count"]),
        "spread_mean": Decimal(summary["spread_mean"]),
        "signal_ready_spread_max_abs": Decimal(summary["signal_ready_spread_max_abs"]),
        "trade_ledger_rows": len(pd.read_csv(output_dir / "trade_ledger.csv")),
        "spread_rows": len(spread_df.index),
        "binance_net_value": Decimal(summary["market_balances"]["binance_feb27"]["net_value"]),
        "hyperliquid_net_value": Decimal(summary["market_balances"]["hyperliquid_feb27"]["net_value"]),
    }


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    baseline = run_mode("tx_replay_best_exec", BorosExecutionMode.TX_REPLAY_BEST_EXEC)
    full_proto = run_mode("event_replay_full_proto", BorosExecutionMode.EVENT_REPLAY_FULL_PROTO)
    comparison = {
        "baseline": baseline,
        "full_execution_proto": full_proto,
        "runtime_ratio_full_vs_baseline": (
            full_proto["runtime_seconds"] / baseline["runtime_seconds"] if baseline["runtime_seconds"] else None
        ),
        "net_value_delta_full_minus_baseline": str(full_proto["final_net_value"] - baseline["final_net_value"]),
        "pnl_delta_full_minus_baseline": str(full_proto["total_pnl"] - baseline["total_pnl"]),
        "action_count_delta_full_minus_baseline": full_proto["action_count"] - baseline["action_count"],
        "spread_mean_delta_full_minus_baseline": str(full_proto["spread_mean"] - baseline["spread_mean"]),
        "signal_ready_spread_max_abs_delta_full_minus_baseline": str(
            full_proto["signal_ready_spread_max_abs"] - baseline["signal_ready_spread_max_abs"]
        ),
    }
    with open(OUTPUT_ROOT / "comparison.json", "w", encoding="utf-8") as file:
        json.dump(_json_safe(comparison), file, indent=2)

    lines = [
        "# Boros Full Execution Prototype Compare",
        "",
        "## Baseline",
        f"- execution_mode: {baseline['execution_mode']}",
        f"- runtime_seconds: {baseline['runtime_seconds']:.4f}",
        f"- final_net_value: {baseline['final_net_value']}",
        f"- total_pnl: {baseline['total_pnl']}",
        f"- action_count: {baseline['action_count']}",
        f"- mark_rate_model: {baseline['mark_rate_model']}",
        "",
        "## Full Execution Prototype",
        f"- execution_mode: {full_proto['execution_mode']}",
        f"- runtime_seconds: {full_proto['runtime_seconds']:.4f}",
        f"- final_net_value: {full_proto['final_net_value']}",
        f"- total_pnl: {full_proto['total_pnl']}",
        f"- action_count: {full_proto['action_count']}",
        f"- mark_rate_model: {full_proto['mark_rate_model']}",
        "",
        "## Delta",
        f"- runtime_ratio_full_vs_baseline: {comparison['runtime_ratio_full_vs_baseline']}",
        f"- net_value_delta_full_minus_baseline: {comparison['net_value_delta_full_minus_baseline']}",
        f"- pnl_delta_full_minus_baseline: {comparison['pnl_delta_full_minus_baseline']}",
        f"- action_count_delta_full_minus_baseline: {comparison['action_count_delta_full_minus_baseline']}",
        f"- spread_mean_delta_full_minus_baseline: {comparison['spread_mean_delta_full_minus_baseline']}",
        f"- signal_ready_spread_max_abs_delta_full_minus_baseline: {comparison['signal_ready_spread_max_abs_delta_full_minus_baseline']}",
        "",
    ]
    (OUTPUT_ROOT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(_json_safe(comparison), indent=2))


if __name__ == "__main__":
    main()
