from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demeter.boros_v4 import BorosExecutionMode, run_funding_convergence_backtest


EVENT_DIR = ROOT / "bn_hl_260121-260226"
OUTPUT_ROOT = ROOT / "outputs" / "boros_case_runs"


@dataclass
class CompareCase:
    name: str
    expected_holding_seconds: int
    min_expected_edge_after_cost: Decimal


CASES = [
    CompareCase(name="baseline_2h_0p02", expected_holding_seconds=2 * 3600, min_expected_edge_after_cost=Decimal("0.02")),
    CompareCase(name="lighter_gate_2h_0p01", expected_holding_seconds=2 * 3600, min_expected_edge_after_cost=Decimal("0.01")),
    CompareCase(name="stricter_gate_2h_0p05", expected_holding_seconds=2 * 3600, min_expected_edge_after_cost=Decimal("0.05")),
]


def run_case(case: CompareCase) -> dict:
    output_dir = OUTPUT_ROOT / case.name
    actuator, strategy, _markets = run_funding_convergence_backtest(
        event_dir=str(EVENT_DIR),
        output_dir=str(output_dir),
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
        execution_mode=BorosExecutionMode.TX_REPLAY_BEST_EXEC,
        min_time_to_maturity_seconds=24 * 3600,
        max_signal_rate=Decimal("2"),
        expected_holding_seconds=case.expected_holding_seconds,
        min_expected_edge_after_cost=case.min_expected_edge_after_cost,
        max_execution_delay_seconds=15 * 60,
        max_pair_execution_skew_seconds=5 * 60,
    )
    with open(output_dir / "summary.json", "r", encoding="utf-8") as file:
        summary = json.load(file)
    spread_history = pd.DataFrame(strategy.spread_history)
    entry_allowed_count = int(spread_history.get("entry_allowed", pd.Series(dtype=bool)).fillna(False).sum())
    return {
        **asdict(case),
        "final_net_value": Decimal(summary["final_net_value"]),
        "total_pnl": Decimal(summary["total_pnl"]),
        "gross_pnl_before_explicit_costs": Decimal(summary["gross_pnl_before_explicit_costs"]),
        "total_opening_fees": Decimal(summary["total_opening_fees"]),
        "total_closing_execution_fees": Decimal(summary["total_closing_execution_fees"]),
        "total_settlement_fees": Decimal(summary["total_settlement_fees"]),
        "total_explicit_costs": Decimal(summary["total_explicit_costs"]),
        "action_count": int(summary["action_count"]),
        "open_action_count": int(summary["open_action_count"]),
        "entry_allowed_count": entry_allowed_count,
        "binance_pnl": Decimal(summary["market_balances"]["binance_feb27"]["realized_pnl"]),
        "hyperliquid_pnl": Decimal(summary["market_balances"]["hyperliquid_feb27"]["realized_pnl"]),
    }


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = [run_case(case) for case in CASES]
    result = pd.DataFrame(rows).sort_values("final_net_value", ascending=False).reset_index(drop=True)
    result.to_csv(OUTPUT_ROOT / "costed_case_compare.csv", index=False)
    lines = ["# Boros Costed Case Compare", ""]
    for row in result.itertuples():
        lines.extend(
            [
                f"## {row.name}",
                f"- expected_holding_seconds: {row.expected_holding_seconds}",
                f"- min_expected_edge_after_cost: {row.min_expected_edge_after_cost}",
                f"- final_net_value: {row.final_net_value}",
                f"- total_pnl: {row.total_pnl}",
                f"- gross_pnl_before_explicit_costs: {row.gross_pnl_before_explicit_costs}",
                f"- total_opening_fees: {row.total_opening_fees}",
                f"- total_closing_execution_fees: {row.total_closing_execution_fees}",
                f"- total_settlement_fees: {row.total_settlement_fees}",
                f"- total_explicit_costs: {row.total_explicit_costs}",
                f"- action_count: {row.action_count}",
                f"- open_action_count: {row.open_action_count}",
                f"- entry_allowed_count: {row.entry_allowed_count}",
                f"- binance_pnl: {row.binance_pnl}",
                f"- hyperliquid_pnl: {row.hyperliquid_pnl}",
                "",
            ]
        )
    (OUTPUT_ROOT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
