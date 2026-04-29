from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT / "outputs" / "boros_convergence"
OUTPUT_DIR = ROOT / "outputs" / "boros_diagnostics"


def _load_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    spread = pd.read_csv(INPUT_DIR / "spread_timeseries.csv", parse_dates=["timestamp"])
    trades = pd.read_csv(INPUT_DIR / "trade_ledger.csv", parse_dates=["timestamp", "execution_timestamp"])
    return spread, trades


def _pair_frame(spread: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    spread_indexed = spread.set_index("timestamp")
    binance = trades.loc[trades["market"] == "binance_feb27"].sort_values("timestamp").reset_index(drop=True)
    opens = binance.loc[binance["action_type"] == "boros_open_fixed_float"].reset_index(drop=True)
    closes = binance.loc[binance["action_type"] == "boros_close_fixed_float"].reset_index(drop=True)
    if len(opens.index) != len(closes.index):
        raise RuntimeError("Open/close pair count mismatch in trade ledger")

    hyperliquid_closes = (
        trades.loc[(trades["market"] == "hyperliquid_feb27") & (trades["action_type"] == "boros_close_fixed_float")]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    rows: list[dict] = []
    for idx in range(len(opens.index)):
        open_row = opens.iloc[idx]
        close_row = closes.iloc[idx]
        hyper_close = hyperliquid_closes.iloc[idx]
        entry_state = spread_indexed.loc[open_row["timestamp"]]
        exit_state = spread_indexed.loc[close_row["timestamp"]]
        entry_spread = float(entry_state["spread"])
        exit_spread = float(exit_state["spread"])
        entry_reference = float(entry_state["reference_spread"])
        exit_reference = float(exit_state["reference_spread"])
        rows.append(
            {
                "pair_id": idx + 1,
                "entry_timestamp": open_row["timestamp"],
                "exit_timestamp": close_row["timestamp"],
                "entry_direction_binance": open_row["direction"],
                "entry_spread": entry_spread,
                "exit_spread": exit_spread,
                "entry_reference_spread": entry_reference,
                "exit_reference_spread": exit_reference,
                "entry_abs_spread": abs(entry_spread),
                "exit_abs_spread": abs(exit_spread),
                "abs_spread_change": abs(exit_spread) - abs(entry_spread),
                "entry_abs_deviation": abs(entry_spread - entry_reference),
                "exit_abs_deviation": abs(exit_spread - exit_reference),
                "abs_deviation_change": abs(exit_spread - exit_reference) - abs(entry_spread - entry_reference),
                "holding_minutes": (close_row["timestamp"] - open_row["timestamp"]).total_seconds() / 60,
                "binance_pnl": float(close_row["pnl"]),
                "hyperliquid_pnl": float(hyper_close["pnl"]),
                "pair_pnl": float(close_row["pnl"]) + float(hyper_close["pnl"]),
                "close_reason": close_row["close_reason"],
            }
        )
    return pd.DataFrame(rows)


def _summary(spread: pd.DataFrame, pairs: pd.DataFrame) -> dict:
    signal = spread.loc[spread["signal_ready"]].copy()
    reference_deviation = signal["spread"] - signal["reference_spread"]
    convergence_success_spread = pairs["exit_abs_spread"] < pairs["entry_abs_spread"]
    convergence_success_deviation = pairs["exit_abs_deviation"] < pairs["entry_abs_deviation"]

    return {
        "sample_start": str(spread["timestamp"].min()),
        "sample_end": str(spread["timestamp"].max()),
        "signal_ready_ratio": float(spread["signal_ready"].mean()) if "signal_ready" in spread else 1.0,
        "rate_corr_signal_ready": float(signal["rate_a"].corr(signal["rate_b"])),
        "spread_mean_signal_ready": float(signal["spread"].mean()),
        "spread_std_signal_ready": float(signal["spread"].std()),
        "spread_abs_p50_signal_ready": float(signal["spread"].abs().quantile(0.5)),
        "spread_abs_p95_signal_ready": float(signal["spread"].abs().quantile(0.95)),
        "spread_abs_start_signal_ready": float(abs(signal.iloc[0]["spread"])),
        "spread_abs_end_signal_ready": float(abs(signal.iloc[-1]["spread"])),
        "deviation_mean_signal_ready": float(reference_deviation.mean()),
        "deviation_std_signal_ready": float(reference_deviation.std()),
        "pair_count": int(len(pairs.index)),
        "pair_win_rate": float((pairs["pair_pnl"] > 0).mean()),
        "pair_mean_pnl": float(pairs["pair_pnl"].mean()),
        "pair_median_pnl": float(pairs["pair_pnl"].median()),
        "avg_holding_minutes": float(pairs["holding_minutes"].mean()),
        "median_holding_minutes": float(pairs["holding_minutes"].median()),
        "convergence_success_rate_to_zero": float(convergence_success_spread.mean()),
        "convergence_success_rate_to_reference": float(convergence_success_deviation.mean()),
        "avg_abs_spread_change": float(pairs["abs_spread_change"].mean()),
        "median_abs_spread_change": float(pairs["abs_spread_change"].median()),
        "avg_abs_deviation_change": float(pairs["abs_deviation_change"].mean()),
        "median_abs_deviation_change": float(pairs["abs_deviation_change"].median()),
        "spread_exit_reason_counts": pairs["close_reason"].value_counts().to_dict(),
    }


def _plot(spread: pd.DataFrame, pairs: pd.DataFrame):
    signal = spread.loc[spread["signal_ready"]].copy()
    open_times = pairs["entry_timestamp"]
    close_times = pairs["exit_timestamp"]
    open_points = signal.set_index("timestamp").reindex(open_times)
    close_points = signal.set_index("timestamp").reindex(close_times)

    fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True, constrained_layout=True)

    axes[0].plot(signal["timestamp"], signal["rate_a"], label="Binance implied rate", linewidth=1.2)
    axes[0].plot(signal["timestamp"], signal["rate_b"], label="Hyperliquid implied rate", linewidth=1.2)
    axes[0].set_ylabel("Implied Rate")
    axes[0].set_title("Boros Dual-Market Implied Rates")
    axes[0].legend(loc="upper right")
    axes[0].grid(alpha=0.25)

    axes[1].plot(signal["timestamp"], signal["spread"], label="Spread (A - B)", linewidth=1.2)
    axes[1].plot(signal["timestamp"], signal["reference_spread"], label="Reference spread", linewidth=1.0, alpha=0.8)
    axes[1].scatter(open_times, open_points["spread"], marker="^", s=28, label="Pair open", color="#0f9d58")
    axes[1].scatter(close_times, close_points["spread"], marker="v", s=28, label="Pair close", color="#db4437")
    axes[1].set_ylabel("Spread")
    axes[1].set_title("Spread With Trade Markers")
    axes[1].legend(loc="upper right")
    axes[1].grid(alpha=0.25)

    plot_path = OUTPUT_DIR / "funding_convergence_timeseries.png"
    fig.savefig(plot_path, dpi=180)
    plt.close(fig)
    return plot_path


def _write_report(summary: dict):
    lines = [
        "# Boros Funding Convergence Diagnostics",
        "",
        "## Sample",
        f"- start: {summary['sample_start']}",
        f"- end: {summary['sample_end']}",
        f"- signal_ready_ratio: {summary['signal_ready_ratio']:.4f}",
        "",
        "## Rate And Spread Stats",
        f"- rate_corr_signal_ready: {summary['rate_corr_signal_ready']:.4f}",
        f"- spread_mean_signal_ready: {summary['spread_mean_signal_ready']:.6f}",
        f"- spread_std_signal_ready: {summary['spread_std_signal_ready']:.6f}",
        f"- spread_abs_p50_signal_ready: {summary['spread_abs_p50_signal_ready']:.6f}",
        f"- spread_abs_p95_signal_ready: {summary['spread_abs_p95_signal_ready']:.6f}",
        f"- spread_abs_start_signal_ready: {summary['spread_abs_start_signal_ready']:.6f}",
        f"- spread_abs_end_signal_ready: {summary['spread_abs_end_signal_ready']:.6f}",
        f"- deviation_mean_signal_ready: {summary['deviation_mean_signal_ready']:.6f}",
        f"- deviation_std_signal_ready: {summary['deviation_std_signal_ready']:.6f}",
        "",
        "## Pair Trade Stats",
        f"- pair_count: {summary['pair_count']}",
        f"- pair_win_rate: {summary['pair_win_rate']:.4f}",
        f"- pair_mean_pnl: {summary['pair_mean_pnl']:.6f}",
        f"- pair_median_pnl: {summary['pair_median_pnl']:.6f}",
        f"- avg_holding_minutes: {summary['avg_holding_minutes']:.2f}",
        f"- median_holding_minutes: {summary['median_holding_minutes']:.2f}",
        f"- convergence_success_rate_to_zero: {summary['convergence_success_rate_to_zero']:.4f}",
        f"- convergence_success_rate_to_reference: {summary['convergence_success_rate_to_reference']:.4f}",
        f"- avg_abs_spread_change: {summary['avg_abs_spread_change']:.6f}",
        f"- median_abs_spread_change: {summary['median_abs_spread_change']:.6f}",
        f"- avg_abs_deviation_change: {summary['avg_abs_deviation_change']:.6f}",
        f"- median_abs_deviation_change: {summary['median_abs_deviation_change']:.6f}",
        "",
        "## Close Reasons",
    ]
    for key, value in summary["spread_exit_reason_counts"].items():
        lines.append(f"- {key}: {value}")

    (OUTPUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    spread, trades = _load_frames()
    pairs = _pair_frame(spread, trades)
    summary = _summary(spread, pairs)
    pairs.to_csv(OUTPUT_DIR / "pair_trade_stats.csv", index=False)
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_report(summary)
    plot_path = _plot(spread, pairs)
    print(f"plot={plot_path}")
    print(
        "pair_count="
        f"{summary['pair_count']} convergence_success_rate_to_reference="
        f"{summary['convergence_success_rate_to_reference']:.4f}"
    )


if __name__ == "__main__":
    main()
