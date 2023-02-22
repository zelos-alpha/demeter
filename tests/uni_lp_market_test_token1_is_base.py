import unittest

import demeter
from demeter import UniLpMarket, TokenInfo, UniV3Pool, UniV3PoolStatus, Broker, MarketInfo
from pandas import Series
from decimal import Decimal

from demeter.broker.uni_lp_helper import tick_to_quote_price

test_market = MarketInfo("market1")


class TestUniLpMarketToken1Base(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.eth = TokenInfo(name="eth", decimal=18)
        self.usdc = TokenInfo(name="usdc", decimal=6)
        self.pool = UniV3Pool(token0=self.eth, token1=self.usdc, fee=0.05, base_token=self.usdc)
        super(TestUniLpMarketToken1Base, self).__init__(*args, **kwargs)

    def get_broker(self) -> Broker:
        # 1066.091101419725805850594389
        broker = Broker()
        market = UniLpMarket(test_market, self.pool)
        broker.add_market(market)
        tick = -206604
        price = market.tick_to_price(tick)
        market.set_market_status(None, UniV3PoolStatus(None,
                                                       tick,
                                                       1107562474636574291,
                                                       18714189922,
                                                       58280013108171131649,
                                                       price))

        broker.set_balance(self.eth, 1)
        broker.set_balance(self.usdc, price)
        market.sqrt_price = demeter.broker.uni_lp_helper.tick_to_sqrtPriceX96(tick)

        # https://etherscan.io/address/0x4e68ccd3e89f51c3074ca5072bbac773960dfa36#readContract
        return broker

    @staticmethod
    def print_broker(broker):
        print("broker:", broker)
        uni_market: UniLpMarket = broker.markets[test_market]
        for k, v in uni_market.positions.items():
            print("=====begin print position=====")
            print(k)
            print(v)
            print("=====end======")
        # print("assets:", broker.get_account_status())

    def test_new(self):
        broker = self.get_broker()
        uni_market: UniLpMarket = broker.markets[test_market]
        print(broker)
        self.assertEqual(1, broker.assets[self.eth].balance)
        self.assertEqual(uni_market.market_status.price, broker.assets[self.usdc].balance)
        self.assertEqual(uni_market.quote_token, self.eth)
        self.assertEqual(uni_market.base_token, self.usdc)

    def test_add_Liquidity_by_tick(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        (new_position, base_used, quote_used, liquidity) = market.add_liquidity_by_tick(
            market.market_status.current_tick - 100,
            market.market_status.current_tick + 100)

        TestUniLpMarketToken1Base.print_broker(broker)
        self.assertEqual(0, broker.assets[self.eth].balance.quantize(Decimal('.0000001')))
        self.assertEqual(0, broker.assets[self.usdc].balance.quantize(Decimal('.00001')))
        self.assertEqual(6546548417233952, liquidity)

    def test_remove_position(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        quote_amt = broker.assets[self.eth].balance
        base_amt = broker.assets[self.usdc].balance
        (new_position, base_used, quote_used, liquidity) = market.add_liquidity(market.market_status.price - 100,
                                                                                market.market_status.price + 100,
                                                                                base_amt,
                                                                                quote_amt, )
        TestUniLpMarketToken1Base.print_broker(broker)
        market.remove_liquidity(new_position)
        print("===============================================================================")
        TestUniLpMarketToken1Base.print_broker(broker)
        self.assertEqual(quote_amt.quantize(Decimal('.00001')),
                         broker.assets[self.eth].balance.quantize(Decimal('.00001')))
        self.assertEqual(base_amt.quantize(Decimal('.00001')),
                         broker.assets[self.usdc].balance.quantize(Decimal('.00001')))
        self.assertEqual(len(market.positions), 0)

    def test_collect_fee(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(Decimal(1),
                                                                                         market.market_status.price,
                                                                                         market.market_status.current_tick - 10,
                                                                                         market.market_status.current_tick + 10)
        TestUniLpMarketToken1Base.print_broker(broker)
        eth_amount = 10000000000000000000
        usdc_amount = 10000000
        # row = Series(index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1"],
        #              data=[broker.pool_status.current_tick, liquidity * 100,
        #                    eth_amount,
        #                    usdc_amount])
        price = market.tick_to_price(market.market_status.current_tick)
        market.set_market_status(None, UniV3PoolStatus(None, market.market_status.current_tick, liquidity * 100,
                                                       eth_amount, usdc_amount, price))
        market.update()
        print("=========after a bar======================================================================")
        TestUniLpMarketToken1Base.print_broker(broker)

        self.assertTrue(Decimal("0.00005") == market.position(new_position).pending_amount0)
        self.assertTrue(Decimal("0.00005") == market.position(new_position).pending_amount1)

        fee0 = market.position(new_position).pending_amount0
        fee1 = market.position(new_position).pending_amount1
        balance0 = broker.assets[self.eth].balance
        balance1 = broker.assets[self.usdc].balance
        market.collect_fee(new_position)
        print("=========collect======================================================================")
        TestUniLpMarketToken1Base.print_broker(broker)
        self.assertEqual(fee0 + balance0, broker.assets[self.eth].balance)
        self.assertEqual(fee1 + balance1, broker.assets[self.usdc].balance)
        self.assertEqual(market.positions[new_position].pending_amount0, 0)

    def test_buy(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]

        token0_before = broker.assets[self.eth].balance
        token1_before = broker.assets[self.usdc].balance
        TestUniLpMarketToken1Base.print_broker(broker)
        market.buy(0.5)
        print("=========after buy======================================================================")
        TestUniLpMarketToken1Base.print_broker(broker)
        self.assertEqual(broker.assets[self.usdc].balance,
                         token1_before - market.market_status.price * Decimal(0.5) * (
                                 1 + market.pool_info.fee_rate))
        self.assertEqual(broker.assets[self.eth].balance, token0_before + Decimal(0.5))

    def test_sell(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]

        TestUniLpMarketToken1Base.print_broker(broker)
        token0_before = broker.assets[self.eth].balance
        token1_before = broker.assets[self.usdc].balance
        market.sell(1)
        print("=========after buy======================================================================")
        TestUniLpMarketToken1Base.print_broker(broker)
        self.assertEqual(broker.assets[market.token1].balance,
                         token1_before + market.market_status.price * Decimal(1) * (1 - market.pool_info.fee_rate))
        self.assertEqual(broker.assets[market.token0].balance, token0_before - Decimal(1))
