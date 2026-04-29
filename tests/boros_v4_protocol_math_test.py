import unittest
from decimal import Decimal
from unittest.mock import patch

from demeter.boros_v4.AMM import AMM
from demeter.boros_v4.PaymentLib import FIndex, PayFee, PaymentLib
from demeter.boros_v4.SwapMath import SwapMathParams
from demeter.boros_v4.Trade import Fill, Trade
from demeter.boros_v4.TradeModule import TradeModule
from demeter.boros_v4._typing import CancelData, OrderId, Side, TimeInForce


class _FakeAMM(AMM):
    def __init__(self):
        super().__init__(amm_id=1, market_id=1)
        self.fee_rate = Decimal("0.0005")

    def _swap_view(self, size_out: Decimal) -> Decimal:
        return Decimal("0.25") * size_out

    def _swap(self, swap_size_out: int) -> int:
        return int(Decimal("0.25") * Decimal(swap_size_out))


class BorosV4ProtocolMathTest(unittest.TestCase):
    def test_trade_and_fill_primitives_match_protocol_side_semantics(self):
        long_trade = Trade.from3(Side.LONG, Decimal("2"), Decimal("0.05"))
        short_trade = Trade.from3(Side.SHORT, Decimal("2"), Decimal("0.05"))

        self.assertEqual(long_trade.signed_size, Decimal("2"))
        self.assertEqual(long_trade.signed_cost, Decimal("0.10"))
        self.assertEqual(long_trade.side(), Side.LONG)

        self.assertEqual(short_trade.signed_size, Decimal("-2"))
        self.assertEqual(short_trade.signed_cost, Decimal("-0.10"))
        self.assertEqual(short_trade.side(), Side.SHORT)

        net_trade = long_trade + short_trade.opposite()
        self.assertEqual(net_trade.signed_size, Decimal("4"))
        self.assertEqual(net_trade.signed_cost, Decimal("0.20"))

        fill = Fill.from3(Side.SHORT, Decimal("3"), Decimal("0.04"))
        self.assertEqual(fill.to_trade().signed_size, Decimal("-3"))
        self.assertEqual(fill.to_trade().signed_cost, Decimal("-0.12"))

    def test_payment_lib_protocol_formulas(self):
        abs_size = PaymentLib.decimal_to_wad(Decimal("100"))
        fee_rate = PaymentLib.decimal_to_wad(Decimal("0.002"))
        time_to_mat = 7 * 24 * 3600
        floating_fee = PaymentLib.calc_floating_fee(abs_size, fee_rate, time_to_mat)
        expected_fee_floor = PaymentLib.decimal_to_wad(
            Decimal("100") * Decimal("0.002") * Decimal(time_to_mat) / Decimal(365 * 24 * 3600)
        )
        self.assertIn(floating_fee, (expected_fee_floor, expected_fee_floor + 1))

        signed_size = PaymentLib.decimal_to_wad(Decimal("10"))
        last_findex = FIndex(
            floating_index=PaymentLib.decimal_to_wad(Decimal("0.0100")),
            fee_index=PaymentLib.decimal_to_wad(Decimal("0.0010")),
        )
        current_findex = FIndex(
            floating_index=PaymentLib.decimal_to_wad(Decimal("0.0150")),
            fee_index=PaymentLib.decimal_to_wad(Decimal("0.0014")),
        )
        settlement = PaymentLib.calc_settlement(signed_size, last_findex, current_findex)
        self.assertIsInstance(settlement, PayFee)
        self.assertGreater(settlement.payment, 0)
        self.assertGreater(settlement.fees, 0)

        lower_fee_index = FIndex(
            floating_index=current_findex.floating_index,
            fee_index=PaymentLib.decimal_to_wad(Decimal("0.0008")),
        )
        negative_fee_settlement = PaymentLib.calc_settlement(signed_size, current_findex, lower_fee_index)
        self.assertLess(negative_fee_settlement.fees, 0)

    def test_swap_math_matches_protocol_fee_and_rate_conventions(self):
        params_long = SwapMathParams.create(
            amm=_FakeAMM(),
            user_side=Side.LONG,
            taker_fee_rate=Decimal("0.001"),
            amm_otc_fee_rate=Decimal("0.002"),
            amm_all_in_fee_rate=Decimal("0.003"),
            tick_step=1,
            n_ticks_to_try_at_once=5,
            time_to_mat=30 * 24 * 3600,
        )
        params_short = SwapMathParams.create(
            amm=_FakeAMM(),
            user_side=Side.SHORT,
            taker_fee_rate=Decimal("0.001"),
            amm_otc_fee_rate=Decimal("0.002"),
            amm_all_in_fee_rate=Decimal("0.003"),
            tick_step=1,
            n_ticks_to_try_at_once=5,
            time_to_mat=30 * 24 * 3600,
        )

        with patch("demeter.boros_v4.SwapMath.TickMath.get_rate_at_tick", return_value=0.05):
            self.assertAlmostEqual(float(params_long.convert_book_tick_to_base_rate(100)), 0.051, places=12)
            self.assertAlmostEqual(float(params_short.convert_book_tick_to_base_rate(100)), 0.049, places=12)

        self.assertEqual(params_long.convert_base_rate_to_amm_rate(Decimal("0.05")), Decimal("0.047"))
        self.assertEqual(params_short.convert_base_rate_to_amm_rate(Decimal("0.05")), Decimal("0.053"))

        abs_size = Decimal("10")
        expected_taker_fee = PaymentLib.wad_to_decimal(
            PaymentLib.calc_floating_fee(
                PaymentLib.decimal_to_wad(abs_size),
                PaymentLib.decimal_to_wad(Decimal("0.001")),
                30 * 24 * 3600,
            )
        )
        expected_otc_fee = PaymentLib.wad_to_decimal(
            PaymentLib.calc_floating_fee(
                PaymentLib.decimal_to_wad(abs_size),
                PaymentLib.decimal_to_wad(Decimal("0.002")),
                30 * 24 * 3600,
            )
        )

        self.assertEqual(params_long.calc_book_taker_fee(abs_size), expected_taker_fee)
        self.assertEqual(params_long.calc_amm_otc_fee(abs_size), expected_otc_fee)

        amm_cash_in, amm_fixed_cash = params_long.calc_swap_amm(Decimal("4"))
        self.assertGreater(amm_cash_in, amm_fixed_cash)
        self.assertGreater(amm_fixed_cash, Decimal(0))

    def test_trade_module_and_order_helpers_are_importable(self):
        module = TradeModule(ob_struct=None, amm=_FakeAMM())
        self.assertIsInstance(module, TradeModule)
        self.assertEqual(TimeInForce.GTC.name, "GTC")
        self.assertTrue(OrderId().is_zero())
        self.assertEqual(CancelData.empty(), CancelData())


if __name__ == "__main__":
    unittest.main()
