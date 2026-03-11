import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from demeter import Actuator, MarketInfo, MarketStatus, MarketTypeEnum, USD
from demeter.boros_v4 import BorosMarket, FixedFloatDirection, SimpleFixedFloatStrategy, load_boros_data, load_boros_tx_ledger
from demeter.broker import ActionTypeEnum


TESTS_DIR = Path(__file__).resolve().parent
DEMO_TRADE_PATH = TESTS_DIR / "fixtures" / "boros" / "demo_market_trades.csv"
DEMO_LOG_PATH = TESTS_DIR / "fixtures" / "boros" / "demo_logs.txt"


class BorosV4BacktestTest(unittest.TestCase):
    def test_load_boros_data(self):
        data = load_boros_data(
            trade_path=str(DEMO_TRADE_PATH),
            log_path=str(DEMO_LOG_PATH),
            market_name="boros_demo",
            venue="BINANCE",
            maturity=date(2025, 7, 1),
        )
        self.assertEqual(len(data.index), 6)
        self.assertEqual(data.index[0], pd.Timestamp("2025-07-01 00:00:00"))
        self.assertEqual(data["trade_count"].iloc[3], 1)
        self.assertEqual(data["mark_rate"].iloc[3], Decimal("0.0570"))
        self.assertEqual(data["venue"].iloc[0], "BINANCE")
        self.assertIn("floating_index", data.columns)

    def test_load_boros_tx_ledger(self):
        ledger = load_boros_tx_ledger(str(DEMO_TRADE_PATH), str(DEMO_LOG_PATH))
        self.assertEqual(len(ledger.index), 6)
        self.assertEqual(ledger.iloc[0]["tx_hash"], "0xboros0001")
        self.assertEqual(ledger.iloc[-1]["minute"], pd.Timestamp("2025-07-01 00:05:00"))
        self.assertEqual(ledger.iloc[2]["trade_rate_vwap"], Decimal("0.0560"))

    def test_boros_market_open_and_close(self):
        market = BorosMarket(MarketInfo("boros_demo", MarketTypeEnum.boros))
        market.load_data(
            trade_path=str(DEMO_TRADE_PATH),
            log_path=str(DEMO_LOG_PATH),
            venue="BINANCE",
            maturity=date(2025, 7, 1),
        )
        price = pd.Series({"USD": Decimal(1)})

        market.set_market_status(MarketStatus(pd.Timestamp("2025-07-01 00:00:00")), price)
        position = market.open_fixed_float(Decimal("100"), FixedFloatDirection.PAY_FIXED)
        self.assertEqual(position.position_id, 1)
        self.assertTrue(market.has_open_position)

        market.set_market_status(MarketStatus(pd.Timestamp("2025-07-01 00:03:00")), price)
        realized = market.close_position()
        self.assertFalse(market.has_open_position)
        self.assertNotEqual(realized, Decimal(0))
        self.assertEqual(len(market.positions), 1)

    def test_execution_opening_fee_rate_overrides_proxy(self):
        market = BorosMarket(MarketInfo("boros_demo", MarketTypeEnum.boros))
        market.load_data(
            trade_path=str(DEMO_TRADE_PATH),
            log_path=str(DEMO_LOG_PATH),
            venue="BINANCE",
            maturity=date(2025, 7, 1),
        )
        price = pd.Series({"USD": Decimal(1)})
        market.set_market_status(MarketStatus(pd.Timestamp("2025-07-01 00:00:00")), price)
        status_data = market.market_status.data.copy()
        status_data["opening_fee_rate_annualized_proxy"] = Decimal("100")
        market.market_status.data = status_data

        position = market.open_fixed_float(
            Decimal("100"),
            FixedFloatDirection.PAY_FIXED,
            execution_fee_paid=Decimal(0),
            execution_opening_fee_rate=Decimal(0),
            execution_source="amm",
        )
        self.assertEqual(position.entry_opening_fee_cost, Decimal(0))

    def test_actuator_runs_simple_fixed_float_strategy(self):
        market = BorosMarket(MarketInfo("boros_demo", MarketTypeEnum.boros))
        market.load_data(
            trade_path=str(DEMO_TRADE_PATH),
            log_path=str(DEMO_LOG_PATH),
            venue="BINANCE",
            maturity=datetime(2025, 7, 1, 0, 5),
        )

        actuator = Actuator()
        actuator.broker.add_market(market)
        actuator.broker.set_balance(USD, Decimal("1000"))
        actuator.strategy = SimpleFixedFloatStrategy(
            notional=Decimal("100"),
            lookback=2,
            entry_threshold=Decimal("0.002"),
            exit_threshold=Decimal("0.0005"),
        )
        actuator.set_price(market.get_price_from_data())
        actuator.run(False)

        self.assertGreaterEqual(len(actuator.actions), 2)
        self.assertEqual(actuator.actions[0].action_type, ActionTypeEnum.boros_open_fixed_float)
        self.assertEqual(actuator.actions[-1].action_type, ActionTypeEnum.boros_close_fixed_float)
        self.assertIn(("boros_demo", "net_value"), actuator.account_status_df.columns)
