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
OUTPUT_DIR = ROOT / "outputs" / "boros_convergence_with_perp_funding"
START = datetime(2026, 1, 21, 0, 0, 0)
END = datetime(2026, 2, 26, 23, 59, 0)


if __name__ == "__main__":
    synthetic_funding = {
        "binance_feb27": load_binance_funding_history("ETHUSDT", START, END),
        "hyperliquid_feb27": load_hyperliquid_funding_history("ETH", START, END),
    }
    actuator, strategy, markets = run_funding_convergence_backtest(
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
        execution_mode=BorosExecutionMode.TX_REPLAY_BEST_EXEC,
        min_time_to_maturity_seconds=24 * 3600,
        max_signal_rate=Decimal("2"),
        expected_holding_seconds=2 * 3600,
        min_expected_edge_after_cost=Decimal("0.02"),
        max_execution_delay_seconds=15 * 60,
        max_pair_execution_skew_seconds=5 * 60,
        synthetic_perp_funding=synthetic_funding,
    )
    print(
        f"actions={len(actuator.actions)} funding_events={len(strategy.perp_funding_ledger)} output_dir={OUTPUT_DIR}"
    )
