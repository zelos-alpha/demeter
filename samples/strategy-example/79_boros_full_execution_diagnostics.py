from __future__ import annotations

import json
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
OUTPUT_DIR = ROOT / "outputs" / "boros_full_execution_diagnostics"


def main():
    actuator, strategy, _ = run_funding_convergence_backtest(
        event_dir=str(EVENT_DIR),
        output_dir=str(OUTPUT_DIR),
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
        execution_mode=BorosExecutionMode.EVENT_REPLAY_FULL_PROTO,
        min_time_to_maturity_seconds=24 * 3600,
        max_signal_rate=Decimal("2"),
        expected_holding_seconds=2 * 3600,
        min_expected_edge_after_cost=Decimal("0.02"),
        max_execution_delay_seconds=15 * 60,
        max_pair_execution_skew_seconds=5 * 60,
    )

    diagnostics_path = OUTPUT_DIR / "execution_diagnostics.csv"
    diagnostics = pd.read_csv(diagnostics_path)
    summary_path = OUTPUT_DIR / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    source_counts = diagnostics["execution_source"].value_counts().to_dict()
    selection_reason_counts = diagnostics["execution_selection_reason"].fillna("").value_counts().to_dict()
    option_count_distribution = diagnostics["execution_option_count"].value_counts().sort_index().to_dict()
    market_source_counts = diagnostics.groupby(["market", "execution_source"]).size().unstack(fill_value=0).to_dict(orient="index")

    effective_rate_gap = []
    for row in diagnostics.itertuples():
        try:
            options = json.loads(row.execution_quote_options_json) if row.execution_quote_options_json else []
        except json.JSONDecodeError:
            options = []
        if len(options) <= 1:
            continue
        selected = next((item for item in options if item["execution_source"] == row.execution_source), None)
        if selected is None:
            continue
        selected_rate = Decimal(selected["effective_rate"])
        alt_rates = [Decimal(item["effective_rate"]) for item in options if item["execution_source"] != row.execution_source]
        if not alt_rates:
            continue
        if row.direction == "PAY_FIXED":
            gap = min(alt_rates) - selected_rate
        else:
            gap = selected_rate - max(alt_rates)
        effective_rate_gap.append(gap)

    report_lines = [
        "# Boros Full Execution Diagnostics",
        "",
        f"- final_net_value: {summary['final_net_value']}",
        f"- total_pnl: {summary['total_pnl']}",
        f"- action_count: {summary['action_count']}",
        f"- diagnostics_rows: {len(diagnostics)}",
        f"- source_counts: {source_counts}",
        f"- selection_reason_counts: {selection_reason_counts}",
        f"- option_count_distribution: {option_count_distribution}",
        f"- market_source_counts: {market_source_counts}",
        f"- mean_selected_edge_vs_alternatives: {str(sum(effective_rate_gap, Decimal(0)) / Decimal(len(effective_rate_gap))) if effective_rate_gap else '0'}",
        "",
        "## Sample Rows",
    ]
    sample_columns = [
        "timestamp",
        "market",
        "direction",
        "execution_source",
        "execution_selection_reason",
        "execution_option_count",
        "execution_effective_rate",
        "execution_available_abs_size_total",
    ]
    for row in diagnostics[sample_columns].head(10).itertuples(index=False):
        report_lines.append(f"- {tuple(row)}")

    (OUTPUT_DIR / "diagnostics_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "final_net_value": summary["final_net_value"],
                "total_pnl": summary["total_pnl"],
                "diagnostics_rows": len(diagnostics),
                "source_counts": source_counts,
                "selection_reason_counts": selection_reason_counts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
