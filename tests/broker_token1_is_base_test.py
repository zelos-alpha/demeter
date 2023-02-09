import unittest
from demeter import UniLpMarket, TokenInfo, UniV3Pool, UniV3PoolStatus
from pandas import Series
from decimal import Decimal

from demeter.broker.uni_lp_helper import tick_to_quote_price


class TestBroker(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.eth = TokenInfo(name="eth", decimal=18)
        self.usdc = TokenInfo(name="usdc", decimal=6)
        self.pool = UniV3Pool(token0=self.eth, token1=self.usdc, fee=0.05, base_token=self.usdc)
        super(TestBroker, self).__init__(*args, **kwargs)

    def get_one_broker(self) -> UniLpMarket:
        # 1066.091101419725805850594389
        broker = UniLpMarket(self.pool)
        tick = -206604
        price = broker.tick_to_price(tick)
        broker.pool_status = UniV3PoolStatus(None, tick, Decimal("1107562474636574291"),
                                             Decimal("58280013108171131649"), Decimal("18714189922"), price)
        broker.set_asset(self.eth, 1)
        broker.set_asset(self.usdc, price)
        # https://etherscan.io/address/0x4e68ccd3e89f51c3074ca5072bbac773960dfa36#readContract
        return broker

    @staticmethod
    def print_broker(broker, positions=[]):
        if positions:
            for p in positions:
                print("=====begin print position=====")
                print(p)
                print(broker.positions[p])
                print("=====end======")
        print("broker:", broker)

    def test_new(self):
        broker = self.get_one_broker()
        print(broker)
        self.assertEqual(1, broker.asset0.balance)
        self.assertEqual(broker.pool_status.price, broker.asset1.balance)

    def test_add_Liquidity_by_tick(self):
        broker = self.get_one_broker()
        # add liquidity with same tick range, should use all the balance
        (new_position, base_used, quote_used, liquidity) = broker._add_liquidity_by_tick(broker.asset0.balance,
                                                                                         broker.asset1.balance,
                                                                                         broker.pool_status.current_tick - 100,
                                                                                         broker.pool_status.current_tick + 100)
        TestBroker.print_broker(broker, [new_position, ])
        self.assertEqual(0, broker.asset0.balance.quantize(Decimal('.0000001')))
        self.assertEqual(0, broker.asset1.balance.quantize(Decimal('.00001')))

    def test_remove_position(self):
        broker = self.get_one_broker()
        token0_amt = broker.asset0.balance
        token1_amt = broker.asset1.balance
        (new_position, base_used, quote_used, liquidity) = broker.add_liquidity(broker.pool_status.price - 100,
                                                                                broker.pool_status.price + 100,
                                                                                token1_amt,
                                                                                token0_amt, )
        TestBroker.print_broker(broker, [new_position, ])
        broker.remove_liquidity(new_position)
        print("===============================================================================")
        TestBroker.print_broker(broker)
        self.assertEqual(token0_amt.quantize(Decimal('.00001')), broker.asset0.balance.quantize(Decimal('.00001')))
        self.assertEqual(token1_amt.quantize(Decimal('.00001')), broker.asset1.balance.quantize(Decimal('.00001')))
        self.assertEqual(len(broker.positions), 0)

    def test_collect_fee(self):
        broker = self.get_one_broker()
        (new_position, base_used, quote_used, liquidity) = broker._add_liquidity_by_tick(Decimal(1),
                                                                                         broker.pool_status.price,
                                                                                         broker.pool_status.current_tick - 10,
                                                                                         broker.pool_status.current_tick + 10)
        TestBroker.print_broker(broker, [new_position])
        eth_amount = Decimal("10000000000000000000")
        usdc_amount = Decimal("10000000")
        row = Series(index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1"],
                     data=[broker.pool_status.current_tick, liquidity * 100,
                           eth_amount,
                           usdc_amount])
        price = broker.tick_to_price(broker.pool_status.current_tick)
        broker.pool_status = UniV3PoolStatus(None, broker.pool_status.current_tick, liquidity * 100,
                                             eth_amount, usdc_amount, price)
        broker.update()
        print("=========after a bar======================================================================")
        TestBroker.print_broker(broker, [new_position])

        self.assertTrue(Decimal("0.00005") == broker.position(new_position).pending_amount0)
        self.assertTrue(Decimal("0.00005") == broker.position(new_position).pending_amount1)

        fee0 = broker.position(new_position).pending_amount0
        fee1 = broker.position(new_position).pending_amount1
        balance0 = broker.asset0.balance
        balance1 = broker.asset1.balance
        broker.collect_fee(new_position)
        print("=========collect======================================================================")
        TestBroker.print_broker(broker, [new_position])
        self.assertEqual(fee0 + balance0, broker.asset0.balance)
        self.assertEqual(fee1 + balance1, broker.asset1.balance)
        self.assertEqual(broker.position(new_position).pending_amount0, 0)
        self.assertEqual(broker.position(new_position).pending_amount0, 0)

    def test_buy(self):
        broker = self.get_one_broker()
        token0_before = broker.asset0.balance
        token1_before = broker.asset1.balance
        TestBroker.print_broker(broker)
        broker.buy(0.5)
        print("=========after buy======================================================================")
        TestBroker.print_broker(broker)
        self.assertEqual(broker.asset1.balance,
                         token1_before - broker.pool_status.price * Decimal(0.5) * (1 + broker.pool_info.fee_rate))
        self.assertEqual(broker.asset0.balance, token0_before + Decimal(0.5))

    def test_sell(self):
        broker = self.get_one_broker()
        TestBroker.print_broker(broker)
        token0_before = broker.asset0.balance
        token1_before = broker.asset1.balance
        broker.sell(1)
        print("=========after buy======================================================================")
        TestBroker.print_broker(broker)
        self.assertEqual(broker.asset1.balance,
                         token1_before + broker.pool_status.price * Decimal(1) * (1 - broker.pool_info.fee_rate))
        self.assertEqual(broker.asset0.balance, token0_before - Decimal(1))
