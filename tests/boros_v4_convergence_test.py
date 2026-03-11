import csv
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd

from demeter import Actuator, MarketInfo, MarketTypeEnum, USD
from demeter.boros_v4 import (
    BorosExecutionMode,
    BorosMarket,
    FundingConvergenceStrategy,
    export_convergence_result,
    load_boros_event_data,
    load_boros_event_ledger,
    load_boros_event_trade_ledger,
)


ORDERBOOK_FILLED_TOPIC = "0x02bab1fddd0d69675bb484195c44cfcb7ee30600f166c947e573b757665587c4"
F_INDEX_TOPIC = "0x589ac0c8263878a0b9876e05d3c1df33ee0680818e7ba8df67d9163342e57e55"
SWAP_TOPIC = "0x15391ef1cdeab4c973414c6652cf113cb3c8d26819a60aaebaae91bcb82c83da"


def _encode_signed(value: int, bits: int) -> str:
    if value < 0:
        value += 1 << bits
    return f"{value:0{bits // 4}x}"


def _encode_market_orders_filled(size: Decimal, trade_value: Decimal, fee_value: Decimal = Decimal(0)) -> str:
    size_raw = int(size * Decimal("1e18"))
    value_raw = int(trade_value * Decimal("1e19"))
    fee_raw = int(fee_value * Decimal("1e19"))
    return "0x" + "".join(
        [
            "0" * 64,
            _encode_signed(size_raw, 128) + _encode_signed(value_raw, 128),
            f"{fee_raw:064x}",
        ]
    )


def _encode_swap(size: Decimal, trade_value: Decimal) -> str:
    size_raw = int(size * Decimal("1e18"))
    value_raw = int(trade_value * Decimal("1e19"))
    return "0x" + "".join([_encode_signed(size_raw, 256), _encode_signed(value_raw, 256), "0" * 64])


def _encode_dummy_findex() -> str:
    return "0x" + "0" * 128


def _trade_value_for_rate(rate: Decimal, timestamp: datetime, maturity: datetime, size: Decimal = Decimal("1")) -> Decimal:
    seconds = Decimal((maturity - timestamp).total_seconds())
    return rate * size * seconds / Decimal(365 * 24 * 3600)


def _write_csv(path: Path, rows: list[dict]):
    fieldnames = ["block_number", "block_timestamp", "transaction_hash", "address", "log_index", "data", "topics"]
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_dual_market_fixture(root: Path):
    maturity = datetime(2026, 2, 27, 0, 0, 0)
    (root / "orderbook").mkdir(parents=True, exist_ok=True)
    (root / "liquidity").mkdir(parents=True, exist_ok=True)

    rates = {
        "BINANCE-ETHUSDT-27FEB2026": [Decimal("0.0500"), Decimal("0.0500"), Decimal("0.0600"), Decimal("0.0502")],
        "HYPERLIQUID-ETH-27FEB2026": [Decimal("0.0490"), Decimal("0.0490"), Decimal("0.0500"), Decimal("0.0500")],
    }
    timestamps = [
        datetime(2026, 1, 21, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 21, 9, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 21, 9, 2, tzinfo=timezone.utc),
        datetime(2026, 1, 21, 9, 3, tzinfo=timezone.utc),
    ]

    for market_key, rate_series in rates.items():
        orderbook_rows = []
        amm_rows = []
        market_address = "0x" + market_key.encode().hex()[:40].ljust(40, "0")
        amm_address = "0x" + ("amm" + market_key).encode().hex()[:40].ljust(40, "0")
        for index, (timestamp, rate) in enumerate(zip(timestamps, rate_series), start=1):
            trade_value = _trade_value_for_rate(rate=rate, timestamp=timestamp.replace(tzinfo=None), maturity=maturity)
            orderbook_rows.append(
                {
                    "block_number": 1,
                    "block_timestamp": timestamp.isoformat(),
                    "transaction_hash": f"0x{market_key[:6]}ord{index:02d}",
                    "address": market_address,
                    "log_index": index,
                    "data": _encode_market_orders_filled(Decimal("1"), trade_value),
                    "topics": str([ORDERBOOK_FILLED_TOPIC]),
                }
            )
            amm_rows.append(
                {
                    "block_number": 1,
                    "block_timestamp": timestamp.isoformat(),
                    "transaction_hash": f"0x{market_key[:6]}amm{index:02d}",
                    "address": amm_address,
                    "log_index": index,
                    "data": _encode_swap(Decimal("1"), trade_value),
                    "topics": str([SWAP_TOPIC]),
                }
            )
        orderbook_rows.append(
            {
                "block_number": 1,
                "block_timestamp": timestamps[1].isoformat(),
                "transaction_hash": f"0x{market_key[:6]}fidx",
                "address": market_address,
                "log_index": 99,
                "data": _encode_dummy_findex(),
                "topics": str([F_INDEX_TOPIC]),
            }
        )
        _write_csv(root / "orderbook" / f"{market_key}-2026-01-21.csv", orderbook_rows)
        _write_csv(root / "liquidity" / f"AMM-{market_key}-2026-01-21.csv", amm_rows)
    return maturity


class BorosV4ConvergenceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.maturity = _build_dual_market_fixture(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_boros_event_ledger(self):
        ledger = load_boros_event_ledger(str(self.root), market_key="BINANCE-ETHUSDT-27FEB2026")
        self.assertEqual(set(ledger["source_kind"]), {"orderbook", "amm"})
        self.assertIn("market_orders_filled", set(ledger["event_type"]))
        self.assertIn("swap", set(ledger["event_type"]))

    def test_load_boros_event_trade_ledger_and_data(self):
        trade_ledger = load_boros_event_trade_ledger(
            str(self.root), market_key="BINANCE-ETHUSDT-27FEB2026", maturity=self.maturity
        )
        self.assertEqual(len(trade_ledger.index), 8)
        self.assertGreater(trade_ledger.iloc[0]["implied_rate"], Decimal("0.04"))

        data, event_ledger, tx_ledger = load_boros_event_data(
            event_dir=str(self.root),
            market_key="BINANCE-ETHUSDT-27FEB2026",
            venue="BINANCE",
            maturity=self.maturity,
        )
        self.assertEqual(len(data.index), 4)
        self.assertIn("latest_f_time", data.columns)
        self.assertEqual(len(event_ledger.index), 9)
        self.assertEqual(len(tx_ledger.index), 8)

    def test_funding_convergence_strategy_runs(self):
        market_a_info = MarketInfo("binance_feb27", MarketTypeEnum.boros)
        market_b_info = MarketInfo("hyperliquid_feb27", MarketTypeEnum.boros)
        market_a = BorosMarket(market_a_info)
        market_b = BorosMarket(market_b_info)
        market_a.load_event_data(str(self.root), "BINANCE-ETHUSDT-27FEB2026", "BINANCE", self.maturity)
        market_b.load_event_data(str(self.root), "HYPERLIQUID-ETH-27FEB2026", "HYPERLIQUID", self.maturity)

        actuator = Actuator()
        actuator.broker.add_market(market_a)
        actuator.broker.add_market(market_b)
        actuator.broker.set_balance(USD, Decimal("1000"))
        actuator.strategy = FundingConvergenceStrategy(
            market_a_info=market_a_info,
            market_b_info=market_b_info,
            notional=Decimal("100"),
            lookback=2,
            entry_threshold=Decimal("0.004"),
            exit_threshold=Decimal("0.005"),
            stop_loss=Decimal("10"),
            execution_mode=BorosExecutionMode.TX_REPLAY_BEST_EXEC,
        )
        actuator.set_price(pd.DataFrame(index=market_a.data.index.union(market_b.data.index)))
        actuator.run(False)

        self.assertGreaterEqual(len(actuator.actions), 4)
        self.assertEqual(actuator.actions[0].execution_source, "orderbook")
        self.assertIn(("binance_feb27", "net_value"), actuator.account_status_df.columns)

        output_dir = self.root / "outputs"
        export_convergence_result(
            actuator=actuator,
            strategy=actuator.strategy,
            output_dir=str(output_dir),
            markets=[market_a, market_b],
        )
        self.assertTrue((output_dir / "trade_ledger.csv").exists())
        self.assertTrue((output_dir / "summary.json").exists())
