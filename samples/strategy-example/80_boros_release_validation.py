from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demeter.boros_v4 import (
    BorosExecutionMode,
    load_binance_funding_history,
    load_hyperliquid_funding_history,
    run_funding_convergence_backtest,
)


EVENT_DIR = ROOT / "bn_hl_260121-260226"
OUTPUT_ROOT = ROOT / "outputs" / "boros_release_validation"
BASELINE_PATH = ROOT / "samples" / "boros-backtest-modes" / "release_baseline.json"
START = datetime(2026, 1, 21, 0, 0, 0)
END = datetime(2026, 2, 26, 23, 59, 0)
MATURITY = datetime(2026, 2, 27, 0, 0, 0)
COMMON_ARGS = dict(
    event_dir=str(EVENT_DIR),
    market_a_name="binance_feb27",
    market_b_name="hyperliquid_feb27",
    market_a_key="BINANCE-ETHUSDT-27FEB2026",
    market_b_key="HYPERLIQUID-ETH-27FEB2026",
    venue_a="BINANCE",
    venue_b="HYPERLIQUID",
    maturity=MATURITY,
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


def decimalize(value):
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    return Decimal(str(value))


def json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def run_summary(output_name: str, execution_mode: BorosExecutionMode, synthetic_perp_funding=None):
    output_dir = OUTPUT_ROOT / output_name
    run_funding_convergence_backtest(
        output_dir=str(output_dir),
        execution_mode=execution_mode,
        synthetic_perp_funding=synthetic_perp_funding,
        **COMMON_ARGS,
    )
    return json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))


def load_existing_summary(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_compare_result(baseline_summary: dict, full_summary: dict):
    return {
        "baseline_final_net_value": baseline_summary["final_net_value"],
        "baseline_total_pnl": baseline_summary["total_pnl"],
        "full_final_net_value": full_summary["final_net_value"],
        "full_total_pnl": full_summary["total_pnl"],
        "pnl_delta_full_minus_baseline": str(
            decimalize(full_summary["total_pnl"]) - decimalize(baseline_summary["total_pnl"])
        ),
    }


def build_diagnostics_result(summary: dict):
    source_counts = summary["execution_diagnostics"]["execution_source_counts"]
    return {
        "final_net_value": summary["final_net_value"],
        "total_pnl": summary["total_pnl"],
        "action_count": summary["action_count"],
        "orderbook_fill_count": source_counts.get("orderbook_fill", 0),
        "amm_fill_count": source_counts.get("amm_fill", 0),
    }


def load_compare_result():
    payload = json.loads((ROOT / "outputs" / "boros_full_execution_compare" / "comparison.json").read_text(encoding="utf-8"))
    return {
        "baseline_final_net_value": payload["baseline"]["final_net_value"],
        "baseline_total_pnl": payload["baseline"]["total_pnl"],
        "full_final_net_value": payload["full_execution_proto"]["final_net_value"],
        "full_total_pnl": payload["full_execution_proto"]["total_pnl"],
        "pnl_delta_full_minus_baseline": payload["pnl_delta_full_minus_baseline"],
    }


def compare_metrics(name: str, actual: dict, expected: dict, tolerance: dict):
    checks = []
    failures = []
    for key, expected_value in expected.items():
        actual_value = actual[key]
        tol = tolerance[key]
        if isinstance(expected_value, int):
            ok = abs(int(actual_value) - int(expected_value)) <= int(tol)
            delta = int(actual_value) - int(expected_value)
        else:
            actual_dec = decimalize(actual_value)
            expected_dec = decimalize(expected_value)
            tol_dec = decimalize(tol)
            delta = actual_dec - expected_dec
            ok = abs(delta) <= tol_dec
        checks.append(
            {
                "metric": key,
                "actual": actual_value,
                "expected": expected_value,
                "tolerance": tol,
                "delta": delta,
                "ok": ok,
            }
        )
        if not ok:
            failures.append(key)
    return {
        "name": name,
        "ok": not failures,
        "checks": checks,
        "failures": failures,
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rerun",
        action="store_true",
        help="Regenerate the Boros release baseline scenarios instead of reusing existing output artifacts.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    if args.rerun:
        synthetic_funding = {
            "binance_feb27": load_binance_funding_history("ETHUSDT", START, END),
            "hyperliquid_feb27": load_hyperliquid_funding_history("ETH", START, END),
        }
        two_leg_summary = run_summary("two_leg_baseline", BorosExecutionMode.TX_REPLAY_BEST_EXEC)
        four_leg_summary = run_summary(
            "four_leg_synthetic_funding",
            BorosExecutionMode.TX_REPLAY_BEST_EXEC,
            synthetic_perp_funding=synthetic_funding,
        )
        full_proto_summary = run_summary("full_execution_diagnostics", BorosExecutionMode.EVENT_REPLAY_FULL_PROTO)
        actual = {
            "two_leg_baseline": two_leg_summary,
            "four_leg_synthetic_funding": four_leg_summary,
            "full_execution_compare": build_compare_result(two_leg_summary, full_proto_summary),
            "full_execution_diagnostics": build_diagnostics_result(full_proto_summary),
        }
        source_mode = "rerun"
    else:
        actual = {
            "two_leg_baseline": load_existing_summary(ROOT / "outputs" / "boros_convergence" / "summary.json"),
            "four_leg_synthetic_funding": load_existing_summary(
                ROOT / "outputs" / "boros_convergence_with_perp_funding" / "summary.json"
            ),
            "full_execution_compare": load_compare_result(),
            "full_execution_diagnostics": build_diagnostics_result(
                load_existing_summary(ROOT / "outputs" / "boros_full_execution_diagnostics" / "summary.json")
            ),
        }
        source_mode = "existing_outputs"

    validations = []
    overall_ok = True
    for scenario_name, scenario_baseline in baseline["scenarios"].items():
        result = compare_metrics(
            scenario_name,
            actual[scenario_name],
            scenario_baseline["expected"],
            scenario_baseline["tolerance"],
        )
        validations.append(result)
        overall_ok = overall_ok and result["ok"]

    report_lines = [
        "# Boros Release Validation",
        "",
        f"- overall_ok: {overall_ok}",
        f"- source_mode: {source_mode}",
        f"- baseline_file: {BASELINE_PATH.name}",
        f"- dataset: {baseline['dataset']['market_a_key']} vs {baseline['dataset']['market_b_key']}",
        "",
    ]
    for item in validations:
        report_lines.append(f"## {item['name']}")
        report_lines.append(f"- ok: {item['ok']}")
        if item["failures"]:
            report_lines.append(f"- failures: {item['failures']}")
        for check in item["checks"]:
            report_lines.append(
                f"- {check['metric']}: actual={check['actual']} expected={check['expected']} "
                f"tol={check['tolerance']} delta={check['delta']} ok={check['ok']}"
            )
        report_lines.append("")

    payload = {
        "overall_ok": overall_ok,
        "source_mode": source_mode,
        "baseline_file": str(BASELINE_PATH),
        "validations": validations,
    }
    (OUTPUT_ROOT / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    (OUTPUT_ROOT / "validation.json").write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")
    print(json.dumps(json_safe(payload), indent=2))
    if not overall_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
