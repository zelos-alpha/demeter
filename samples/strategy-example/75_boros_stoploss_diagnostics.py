from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


INPUT_DIR = ROOT / "outputs" / "boros_convergence"
OUTPUT_DIR = ROOT / "outputs" / "boros_stoploss_diagnostics"


def main():
    trade_path = INPUT_DIR / "trade_ledger.csv"
    if not trade_path.exists():
        raise FileNotFoundError(f"missing trade ledger: {trade_path}")

    trade_ledger = pd.read_csv(trade_path)
    for column in ["fixed_rate", "mark_rate", "pnl", "execution_fee_paid"]:
        if column in trade_ledger.columns:
            trade_ledger[column] = pd.to_numeric(trade_ledger[column], errors="coerce")

    opens = trade_ledger[trade_ledger["action_type"].str.contains("open", case=False, na=False)].copy()
    closes = trade_ledger[trade_ledger["action_type"].str.contains("close", case=False, na=False)].copy()
    opens["entry_slippage_abs"] = (opens["fixed_rate"] - opens["mark_rate"]).abs()

    paired = opens.merge(
        closes,
        on=["market", "position_id"],
        suffixes=("_open", "_close"),
        how="inner",
    )
    stop_loss_positions = paired[paired["close_reason_close"] == "stop_loss"].copy()
    stop_loss_positions = stop_loss_positions[
        [
            "market",
            "position_id",
            "timestamp_open",
            "timestamp_close",
            "direction_open",
            "fixed_rate_open",
            "mark_rate_open",
            "entry_slippage_abs",
            "execution_tx_hash_open",
            "execution_tx_hash_close",
            "pnl_close",
            "execution_fee_paid_open",
            "execution_fee_paid_close",
        ]
    ].sort_values(["market", "timestamp_open"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stop_loss_positions.to_csv(OUTPUT_DIR / "stop_loss_positions.csv", index=False)

    close_counts = closes["close_reason"].value_counts()
    market_pnl = closes.groupby(["market", "close_reason"])["pnl"].sum().reset_index()
    market_pnl.to_csv(OUTPUT_DIR / "close_reason_pnl.csv", index=False)

    lines = [
        "# Boros Stop Loss Diagnostics",
        "",
        f"- total_close_actions: {len(closes)}",
        f"- stop_loss_close_actions: {int(close_counts.get('stop_loss', 0))}",
        f"- spread_exit_close_actions: {int(close_counts.get('spread_exit', 0))}",
        f"- signal_guard_close_actions: {int(close_counts.get('signal_guard', 0))}",
        "",
        "## Stop Loss By Market",
    ]
    if len(stop_loss_positions.index) == 0:
        lines.append("- no stop loss positions found")
    else:
        grouped = stop_loss_positions.groupby("market").agg(
            stop_loss_count=("position_id", "count"),
            stop_loss_pnl=("pnl_close", "sum"),
            mean_entry_slippage_abs=("entry_slippage_abs", "mean"),
            max_entry_slippage_abs=("entry_slippage_abs", "max"),
        )
        for market, row in grouped.iterrows():
            lines.append(
                f"- {market}: count={int(row.stop_loss_count)}, pnl={row.stop_loss_pnl}, "
                f"mean_entry_slippage_abs={row.mean_entry_slippage_abs}, max_entry_slippage_abs={row.max_entry_slippage_abs}"
            )

    lines.extend(["", "## Close Reason PnL"])
    for row in market_pnl.itertuples(index=False):
        lines.append(f"- {row.market} / {row.close_reason}: pnl={row.pnl}")

    (OUTPUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(stop_loss_positions.to_string(index=False))


if __name__ == "__main__":
    main()
