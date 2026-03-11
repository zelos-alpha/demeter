import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from demeter import Actuator, MarketInfo, MarketTypeEnum, USD
from demeter.boros_v4 import (
    BorosExecutionMode,
    BorosMarket,
    FixedFloatDirection,
    FundingConvergenceStrategy,
    Side,
    TimeInForce,
    Trade,
    export_convergence_result,
    load_binance_funding_history,
    load_boros_event_data,
    load_boros_event_ledger,
    load_boros_event_trade_ledger,
    load_hyperliquid_funding_history,
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


def _encode_swap(size: Decimal, trade_value: Decimal, fee_value: Decimal = Decimal(0)) -> str:
    size_raw = int(size * Decimal("1e18"))
    value_raw = int(trade_value * Decimal("1e19"))
    fee_raw = int(fee_value * Decimal("1e19"))
    return "0x" + "".join([_encode_signed(size_raw, 256), _encode_signed(value_raw, 256), f"{fee_raw:064x}"])


def _encode_dummy_findex(
    latest_f_time: datetime,
    floating_index: Decimal = Decimal("0"),
    fee_index: Decimal = Decimal("0"),
    sequence: int = 0,
) -> str:
    ts = int(latest_f_time.replace(tzinfo=timezone.utc).timestamp())
    floating_raw = int(floating_index * Decimal("1e18"))
    if floating_raw < 0:
        floating_raw += 1 << 112
    fee_raw = int(fee_index * Decimal("1e18"))
    return "0x" + "".join(
        [
            f"{ts:08x}{floating_raw:028x}{fee_raw:016x}" + "0" * 12,
            f"{sequence:064x}",
        ]
    )


def _trade_value_for_rate(rate: Decimal, pricing_timestamp: datetime, maturity: datetime, size: Decimal = Decimal("1")) -> Decimal:
    seconds = Decimal((maturity - pricing_timestamp).total_seconds())
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
            trade_value = _trade_value_for_rate(rate=rate, pricing_timestamp=timestamp.replace(tzinfo=None), maturity=maturity)
            orderbook_rows.append(
                {
                    "block_number": 1,
                    "block_timestamp": timestamp.isoformat(),
                    "transaction_hash": f"0x{market_key[:6]}ord{index:02d}",
                    "address": market_address,
                    "log_index": index,
                    "data": _encode_market_orders_filled(Decimal("1"), trade_value, Decimal("0.001")),
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
                    "data": _encode_swap(Decimal("1"), trade_value, Decimal("0.0005")),
                    "topics": str([SWAP_TOPIC]),
                }
            )
        orderbook_rows.extend(
            [
                {
                    "block_number": 1,
                    "block_timestamp": (timestamp + pd.Timedelta(seconds=30)).isoformat(),
                    "transaction_hash": f"0x{market_key[:6]}fidx{index:02d}",
                    "address": market_address,
                    "log_index": 90 + index,
                    "data": _encode_dummy_findex(
                        timestamp.replace(tzinfo=None),
                        floating_index=Decimal("0.0001") * Decimal(index),
                        fee_index=Decimal("0.00001") * Decimal(index),
                        sequence=2 * index + 1,
                    ),
                    "topics": str([F_INDEX_TOPIC]),
                }
                for index, timestamp in enumerate(timestamps, start=1)
            ]
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
        self.assertEqual(trade_ledger.iloc[0]["trade_side"], "LONG")

        data, event_ledger, tx_ledger = load_boros_event_data(
            event_dir=str(self.root),
            market_key="BINANCE-ETHUSDT-27FEB2026",
            venue="BINANCE",
            maturity=self.maturity,
        )
        self.assertEqual(len(data.index), 4)
        self.assertIn("latest_f_time", data.columns)
        self.assertIn("latest_f_time_to_maturity_seconds", data.columns)
        self.assertIn("settlement_fee_rate_annualized_proxy", data.columns)
        self.assertIn("settlement_fee_rate_annualized_actual", data.columns)
        self.assertIn("mark_rate_full_proto", data.columns)
        self.assertEqual(len(event_ledger.index), 12)
        self.assertEqual(len(tx_ledger.index), 8)
        self.assertGreater(tx_ledger.iloc[0]["opening_fee_rate_annualized"], Decimal(0))
        self.assertEqual(data.iloc[0]["floating_index"], Decimal("0.0001"))
        self.assertEqual(data.iloc[0]["fee_index"], Decimal("0.00001"))
        self.assertEqual(data.iloc[1]["floating_index"], Decimal("0.0002"))
        self.assertEqual(data.iloc[1]["fee_index"], Decimal("0.00002"))
        self.assertEqual(data.iloc[-1]["latest_f_time"], pd.Timestamp("2026-01-21 09:03:00"))
        self.assertEqual(tx_ledger.iloc[-1]["latest_f_time"], pd.Timestamp("2026-01-21 09:02:00"))
        self.assertEqual(tx_ledger.iloc[0]["trade_side"], "LONG")

    def test_full_execution_selection_prefers_best_rate_for_direction(self):
        market = BorosMarket(MarketInfo("binance_feb27", MarketTypeEnum.boros))
        market.load_event_data(str(self.root), "BINANCE-ETHUSDT-27FEB2026", "BINANCE", self.maturity)

        pay_fixed_quote = market.peek_full_execution_quote(
            pd.Timestamp("2026-01-21 09:00:00"),
            required_trade_side=Side.LONG.name,
            prefer_higher_rate=False,
            max_delay_seconds=600,
            include_opening_fee_rate=True,
        )
        receive_fixed_quote = market.peek_full_execution_quote(
            pd.Timestamp("2026-01-21 09:00:00"),
            required_trade_side=Side.SHORT.name,
            prefer_higher_rate=True,
            max_delay_seconds=600,
            include_opening_fee_rate=True,
        )

        self.assertIsNotNone(pay_fixed_quote)
        self.assertEqual(pay_fixed_quote["execution_source"], "amm_fill")
        self.assertLess(
            Decimal(pay_fixed_quote["fixed_rate"]) + Decimal(pay_fixed_quote["execution_opening_fee_rate"]),
            Decimal("0.06"),
        )
        if receive_fixed_quote is not None:
            self.assertEqual(receive_fixed_quote["execution_source"], "amm_fill")
            self.assertGreater(
                Decimal(receive_fixed_quote["fixed_rate"]) - Decimal(receive_fixed_quote["execution_opening_fee_rate"]),
                Decimal("0.04"),
            )

    def test_full_execution_ignores_dust_quote(self):
        market = BorosMarket(MarketInfo("binance_feb27", MarketTypeEnum.boros))
        market.load_event_data(str(self.root), "BINANCE-ETHUSDT-27FEB2026", "BINANCE", self.maturity)
        earliest_timestamp = market.trade_ledger["timestamp"].min()
        dust_mask = (
            (market.trade_ledger["timestamp"] == earliest_timestamp)
            & (market.trade_ledger["source_kind"] == "amm")
        )
        market.trade_ledger.loc[dust_mask, "abs_size_total"] = Decimal("1e-18")

        quote = market.peek_full_execution_quote(
            pd.Timestamp("2026-01-21 09:00:00"),
            required_trade_side=Side.LONG.name,
            prefer_higher_rate=False,
            max_delay_seconds=600,
            include_opening_fee_rate=True,
        )

        self.assertIsNotNone(quote)
        self.assertEqual(quote["execution_source"], "orderbook_fill")

    def test_full_execution_split_requires_meaningful_improvement(self):
        market = BorosMarket(MarketInfo("binance_feb27", MarketTypeEnum.boros))
        market.load_event_data(str(self.root), "BINANCE-ETHUSDT-27FEB2026", "BINANCE", self.maturity)
        market.min_split_rate_improvement = Decimal("0.01")
        market.min_split_size_improvement_ratio = Decimal("10")

        quote = market.peek_full_execution_quote(
            pd.Timestamp("2026-01-21 09:00:00"),
            required_trade_side=Side.LONG.name,
            prefer_higher_rate=False,
            max_delay_seconds=600,
            include_opening_fee_rate=True,
        )

        self.assertIsNotNone(quote)
        self.assertNotEqual(quote["execution_source"], "split_fill")

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
            min_time_to_maturity_seconds=60,
            max_signal_rate=Decimal("1"),
            expected_holding_seconds=60,
            min_expected_edge_after_cost=Decimal("-1"),
            max_execution_delay_seconds=600,
            max_pair_execution_skew_seconds=600,
        )
        actuator.set_price(pd.DataFrame(index=market_a.data.index.union(market_b.data.index)))
        actuator.run(False)

        self.assertGreaterEqual(len(actuator.actions), 4)
        self.assertEqual(actuator.actions[0].execution_source, "orderbook")
        self.assertGreater(actuator.actions[0].execution_fee_paid, Decimal(0))
        self.assertIn(("binance_feb27", "net_value"), actuator.account_status_df.columns)
        spread_df = pd.DataFrame(actuator.strategy.spread_history)
        self.assertTrue(spread_df["signal_ready"].all())
        self.assertIn("expected_edge_after_cost", spread_df.columns)
        self.assertIn("entry_allowed", spread_df.columns)

        output_dir = self.root / "outputs"
        export_convergence_result(
            actuator=actuator,
            strategy=actuator.strategy,
            output_dir=str(output_dir),
            markets=[market_a, market_b],
        )
        self.assertTrue((output_dir / "trade_ledger.csv").exists())
        self.assertTrue((output_dir / "summary.json").exists())
        with open(output_dir / "summary.json", "r", encoding="utf-8") as file:
            summary = json.load(file)
        self.assertGreater(Decimal(summary["total_execution_fees"]), Decimal(0))
        self.assertIn("total_pnl", summary)
        self.assertIn("total_explicit_costs", summary)
        self.assertIn("gross_pnl_before_explicit_costs", summary)
        self.assertIn("total_opening_fees", summary)
        self.assertIn("total_settlement_fees", summary)
        self.assertEqual(summary["settlement_index_model"], "decoded_findex")
        self.assertEqual(summary["mark_rate_model"], "trade_vwap_proxy")
        self.assertEqual(summary["protocol_alignment_mode"], "experimental_taker_only")
        self.assertGreaterEqual(Decimal(summary["total_explicit_costs"]), Decimal(summary["total_execution_fees"]))
        self.assertEqual(
            Decimal(summary["total_explicit_costs"]),
            Decimal(summary["total_opening_fees"])
            + Decimal(summary["total_closing_execution_fees"])
            + Decimal(summary["total_settlement_fees"]),
        )
        self.assertEqual(
            Decimal(summary["gross_pnl_before_explicit_costs"]),
            Decimal(summary["combined_realized_pnl"]) + Decimal(summary["total_explicit_costs"]),
        )
        self.assertIn("total_explicit_costs", summary["market_balances"]["binance_feb27"])

    def test_funding_convergence_full_execution_proto_runs(self):
        market_a_info = MarketInfo("binance_feb27", MarketTypeEnum.boros)
        market_b_info = MarketInfo("hyperliquid_feb27", MarketTypeEnum.boros)
        market_a = BorosMarket(market_a_info)
        market_b = BorosMarket(market_b_info)
        market_a.load_event_data(str(self.root), "BINANCE-ETHUSDT-27FEB2026", "BINANCE", self.maturity)
        market_b.load_event_data(str(self.root), "HYPERLIQUID-ETH-27FEB2026", "HYPERLIQUID", self.maturity)
        market_a.mark_rate_column = "mark_rate_full_proto"
        market_b.mark_rate_column = "mark_rate_full_proto"

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
            execution_mode=BorosExecutionMode.EVENT_REPLAY_FULL_PROTO,
            min_time_to_maturity_seconds=60,
            max_signal_rate=Decimal("1"),
            expected_holding_seconds=60,
            min_expected_edge_after_cost=Decimal("-1"),
        )
        actuator.set_price(pd.DataFrame(index=market_a.data.index.union(market_b.data.index)))
        actuator.run(False)

        self.assertGreaterEqual(len(actuator.actions), 4)
        self.assertTrue(actuator.actions[0].execution_source.endswith("_fill"))
        self.assertIn(actuator.actions[0].execution_source, {"amm_fill", "orderbook_fill", "split_fill"})
        self.assertIn(actuator.actions[0].execution_selection_reason, {"only_available_quote", "selected_best_all_in_rate"})
        self.assertGreaterEqual(actuator.actions[0].execution_option_count, 1)

    def test_funding_convergence_with_synthetic_perp_funding(self):
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
        funding_a = pd.DataFrame(
            [{"timestamp": datetime(2026, 1, 21, 9, 2, 30), "funding_rate": Decimal("0.001"), "period_seconds": 3600}]
        )
        funding_b = pd.DataFrame(
            [{"timestamp": datetime(2026, 1, 21, 9, 2, 30), "funding_rate": Decimal("0.0005"), "period_seconds": 3600}]
        )
        actuator.strategy = FundingConvergenceStrategy(
            market_a_info=market_a_info,
            market_b_info=market_b_info,
            notional=Decimal("100"),
            lookback=2,
            entry_threshold=Decimal("0.004"),
            exit_threshold=Decimal("0.005"),
            stop_loss=Decimal("10"),
            execution_mode=BorosExecutionMode.TX_REPLAY_BEST_EXEC,
            min_time_to_maturity_seconds=60,
            max_signal_rate=Decimal("1"),
            expected_holding_seconds=60,
            min_expected_edge_after_cost=Decimal("-1"),
            synthetic_perp_funding={
                "binance_feb27": funding_a,
                "hyperliquid_feb27": funding_b,
            },
        )
        actuator.set_price(pd.DataFrame(index=market_a.data.index.union(market_b.data.index)))
        actuator.run(False)

        self.assertEqual(actuator.strategy.total_perp_funding_pnl, Decimal("-0.05"))
        self.assertEqual(len(actuator.strategy.perp_funding_ledger), 2)

    def test_external_funding_loaders_shape(self):
        start = datetime(2026, 1, 21)
        end = datetime(2026, 1, 22)
        binance_payload = json.dumps(
            [
                {
                    "symbol": "ETHUSDT",
                    "fundingTime": 1768953600001,
                    "fundingRate": "0.00000552",
                    "markPrice": "2938.29662016",
                }
            ]
        ).encode("utf-8")
        hyperliquid_payload = json.dumps(
            [
                {
                    "coin": "ETH",
                    "fundingRate": "0.0000125",
                    "premium": "-0.0003077475",
                    "time": 1768953600063,
                }
            ]
        ).encode("utf-8")

        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self):
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch("demeter.boros_v4.helper.urlopen") as mocked_urlopen:
            mocked_urlopen.side_effect = [_MockResponse(binance_payload), _MockResponse(hyperliquid_payload)]
            binance = load_binance_funding_history("ETHUSDT", start, end)
            hyperliquid = load_hyperliquid_funding_history("ETH", start, end)
        self.assertIn("funding_rate", binance.columns)
        self.assertIn("annualized_rate", binance.columns)
        self.assertIn("funding_rate", hyperliquid.columns)
        self.assertIn("annualized_rate", hyperliquid.columns)
        self.assertGreater(len(binance.index), 0)
        self.assertGreater(len(hyperliquid.index), 0)

    def test_protocol_primitives_alignment(self):
        self.assertEqual(FixedFloatDirection.PAY_FIXED.to_side(), Side.LONG)
        self.assertEqual(FixedFloatDirection.RECEIVE_FIXED.to_side(), Side.SHORT)
        self.assertEqual(FixedFloatDirection.from_side(Side.LONG), FixedFloatDirection.PAY_FIXED)
        self.assertEqual(FixedFloatDirection.from_side(Side.SHORT), FixedFloatDirection.RECEIVE_FIXED)
        self.assertEqual(TimeInForce.GTC.name, "GTC")
        trade = Trade.from3(Side.LONG, Decimal("2"), Decimal("0.05"))
        self.assertEqual(trade.signed_size, Decimal("2"))
        self.assertEqual(trade.side(), Side.LONG)

    def test_funding_convergence_edge_gate_blocks_entries(self):
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
            min_time_to_maturity_seconds=60,
            max_signal_rate=Decimal("1"),
            expected_holding_seconds=3600,
            min_expected_edge_after_cost=Decimal("1000"),
        )
        actuator.set_price(pd.DataFrame(index=market_a.data.index.union(market_b.data.index)))
        actuator.run(False)

        self.assertEqual(len(actuator.actions), 0)

    def test_funding_convergence_execution_delay_gate_blocks_stale_future_fills(self):
        market_a_info = MarketInfo("binance_feb27", MarketTypeEnum.boros)
        market_b_info = MarketInfo("hyperliquid_feb27", MarketTypeEnum.boros)
        market_a = BorosMarket(market_a_info)
        market_b = BorosMarket(market_b_info)
        market_a.load_event_data(str(self.root), "BINANCE-ETHUSDT-27FEB2026", "BINANCE", self.maturity)
        market_b.load_event_data(str(self.root), "HYPERLIQUID-ETH-27FEB2026", "HYPERLIQUID", self.maturity)

        market_a.tx_ledger["timestamp"] = market_a.tx_ledger["timestamp"] + pd.Timedelta(hours=1)
        market_b.tx_ledger["timestamp"] = market_b.tx_ledger["timestamp"] + pd.Timedelta(hours=1)

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
            min_time_to_maturity_seconds=60,
            max_signal_rate=Decimal("1"),
            expected_holding_seconds=60,
            min_expected_edge_after_cost=Decimal("-1"),
            max_execution_delay_seconds=5 * 60,
        )
        actuator.set_price(pd.DataFrame(index=market_a.data.index.union(market_b.data.index)))
        actuator.run(False)

        self.assertEqual(len(actuator.actions), 0)
