import unittest
from datetime import datetime, date
from decimal import Decimal

import pandas as pd

from demeter import Broker, MarketInfo, MarketTypeEnum, DemeterError
from demeter.deribit import DeribitOptionMarket, DeribitMarketStatus
from demeter.deribit.helper import round_decimal
from io import StringIO

dp_market = MarketInfo("TestMarket", MarketTypeEnum.deribit_option)


class DeribitOptionTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(DeribitOptionTest, self).__init__(*args, **kwargs)

    def test_round_decimal(self):
        self.assertEqual(Decimal("123500000"), round_decimal("123456789", 5))
        self.assertEqual(Decimal("123000000"), round_decimal("123456789", 6))
        self.assertEqual(Decimal("120"), round_decimal("123", 1))
        self.assertEqual(Decimal("123"), round_decimal("123", 0))
        self.assertEqual(Decimal("1.2"), round_decimal("1.23456789", -1))
        self.assertEqual(Decimal("1.2346"), round_decimal("1.23456789", -4))

    def get_broker(self):
        broker = Broker()
        market = DeribitOptionMarket(dp_market, DeribitOptionMarket.ETH)
        broker.add_market(market)
        data_csv = """
instrument_name,time,actual_time,state,type,k,t,exec_time,vega,theta,rho,gamma,delta,underlying_price,settlement_price,min_price,max_price,mark_price,mark_iv,last_price,interest_rate,bid_iv,best_bid_price,best_bid_amount,ask_iv,best_ask_price,best_ask_amount,asks,bids
ETH-22SEP23-1600-C,2023-09-01 06:00:00,2023-09-01 06:00:38.752,open,CALL,1600,21 days 02:00:00,2023-09-22 08:00:00,1.42317,-1.05567,0.60142,0.00289,0.67817,1651.94,,0.021,0.0795,0.0479,31.28,,0,27.93,0.045,70,33.75,0.05,145,"[[0.05, 145]]","[[0.045, 70], [0.0445, 75]]"
ETH-22SEP23-1650-C,2023-09-01 06:00:00,2023-09-01 06:00:39.232,open,CALL,1650,21 days 02:00:00,2023-09-22 08:00:00,1.58174,-1.10083,0.46945,0.00342,0.52071,1651.94,,0.008,0.058,0.0287,29.35,0.0285,0,28.61,0.028,51,29.13,0.0285,5,"[[0.0285, 5], [0.029, 605], [0.0295, 197], [0.03, 40], [0.0305, 18]]","[[0.028, 51], [0.0275, 585], [0.027, 248], [0.0265, 24]]"
ETH-22SEP23-1700-C,2023-09-01 06:00:00,2023-09-01 06:00:38.755,open,CALL,1700,21 days 02:00:00,2023-09-22 08:00:00,1.47652,-1.01999,0.32235,0.00322,0.35396,1651.94,,0.0012,0.042,0.0161,29.13,0.016,0,28.43,0.0155,446,29.55,0.0165,450,"[[0.0165, 450], [0.017, 780], [0.0175, 91], [0.018, 35], [0.025, 10700]]","[[0.0155, 446], [0.015, 879], [0.0145, 50]]"
                """
        data = pd.read_csv(StringIO(data_csv))
        data.set_index('instrument_name', inplace=True)
        market.set_market_status(
            DeribitMarketStatus(timestamp=datetime(2023, 9, 1, 6), data=data),
            price=pd.Series([1651.94], index=["eth"]),
        )

        broker.set_balance(DeribitOptionMarket.ETH, 1)
        return broker

    def test_load_data(self):
        market = DeribitOptionMarket(dp_market, DeribitOptionMarket.ETH, data_path="data")
        market.load_data(date(2024, 2, 15), date(2024, 2, 16))
        self.assertEqual(market.data.shape[0], 33812)
        self.assertEqual(market.data.shape[1], 24)
        for idx, row in market.data.groupby(level=0):
            pass

    def test_trade_fee(self):
        market = DeribitOptionMarket(dp_market, DeribitOptionMarket.ETH)
        self.assertEqual(market.get_trade_fee(Decimal("1"), Decimal("0.0009")), Decimal("0.000113"))

    def test_init_market(self):
        broker = self.get_broker()
        self.assertTrue(len(broker.markets[dp_market].market_status.data.index), 3)
        pass

    def check_buy(
        self,
        market,
        msg_to_check,
        instrument_name: str,
        amount: float | Decimal,
        price_in_token: float | None = None,
        price_in_usd: float | None = None,
    ):
        try:
            market.buy(instrument_name=instrument_name, amount=amount, price_in_token=price_in_token, price_in_usd=price_in_usd)
            self.assertTrue(False, "no exception")
        except DemeterError as e:
            self.assertIn(msg_to_check, str(e))

    def test_buy(self):
        broker = self.get_broker()
        market: DeribitOptionMarket = broker.markets.default
        self.check_buy(market, "in current orderbook", "ETH-22SEP23-ERROR-C", 1)
        self.check_buy(market, "amount should greater than min amount", "ETH-22SEP23-1600-C", 0.01)
        self.check_buy(market, "min amount", "ETH-22SEP23-1600-C", 100000)

