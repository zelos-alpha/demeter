import unittest
from demeter import Broker, TokenInfo, PoolBaseInfo, PoolStatus
from pandas import Series
from decimal import Decimal

from demeter.broker.helper import tick_to_quote_price


class TestBroker(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.eth = TokenInfo(name="eth", decimal=18)
        self.usdc = TokenInfo(name="usdc", decimal=6)
        self.pool = PoolBaseInfo(token0=self.eth, token1=self.usdc, fee=0.05, base_token=self.usdc)
        super(TestBroker, self).__init__(*args, **kwargs)

    def get_one_broker(self) -> Broker:
        # 1066.091101419725805850594389
        broker = Broker(self.pool)
        tick = -206604
        price = broker.tick_to_price(tick)
        broker.pool_status = PoolStatus(None, tick, Decimal("1107562474636574291"),
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
        # 围绕tick对称添加. 应该用光
        (new_position, base_used, quote_used) = broker._Broker__add_liquidity(broker.asset0.balance,
                                                                              broker.asset1.balance,
                                                                              broker.pool_status.current_tick - 100,
                                                                              broker.pool_status.current_tick + 100,
                                                                              broker.pool_status.current_tick)
        TestBroker.print_broker(broker, [new_position, ])
        self.assertEqual(0, float("{:.4f}".format(broker.asset0.balance)))
        self.assertEqual(0, float("{:.4f}".format(broker.asset1.balance)))

    def test_remove_position(self):
        broker = self.get_one_broker()
        token0_amt = broker.asset0.balance
        token1_amt = broker.asset1.balance
        (new_position, base_used, quote_used) = broker.add_liquidity(broker.pool_status.price - 100,
                                                                     broker.pool_status.price + 100,
                                                                     token1_amt,
                                                                     token0_amt, )
        TestBroker.print_broker(broker, [new_position, ])
        broker.remove_liquidity(new_position)
        print("===============================================================================")
        TestBroker.print_broker(broker)
        self.assertEqual(token0_amt, broker.asset0.balance)
        self.assertEqual(token1_amt, broker.asset1.balance)
        self.assertEqual(len(broker.positions), 0)

    def test_collect_fee(self):
        broker = self.get_one_broker()
        # 围绕tick对称添加. 应该用光
        (new_position, base_used, quote_used) = broker._Broker__add_liquidity(Decimal(1),
                                                                              broker.pool_status.price,
                                                                              broker.pool_status.current_tick - 10,
                                                                              broker.pool_status.current_tick + 10,
                                                                              broker.pool_status.current_tick)
        TestBroker.print_broker(broker, [new_position])
        eth_amount = Decimal("10000000000000000000")
        usdc_amount = Decimal("10000000")
        row = Series(index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1"],
                     data=[broker.pool_status.current_tick, new_position.liquidity * 100,
                           eth_amount,
                           usdc_amount])
        price = broker.tick_to_price(broker.pool_status.current_tick)
        broker.pool_status = PoolStatus(None, broker.pool_status.current_tick, new_position.liquidity * 100,
                                        eth_amount, usdc_amount, price)
        broker.update()
        print("=========after a bar======================================================================")
        TestBroker.print_broker(broker, [new_position])

        self.assertTrue(Decimal("0.00005") == broker.position(new_position).uncollected_fee_token0)
        self.assertTrue(Decimal("0.00005") == broker.position(new_position).uncollected_fee_token1)

        fee0 = broker.position(new_position).uncollected_fee_token0
        fee1 = broker.position(new_position).uncollected_fee_token1
        balance0 = broker.asset0.balance
        balance1 = broker.asset1.balance
        broker.collect_fee(new_position)
        print("=========collect======================================================================")
        TestBroker.print_broker(broker, [new_position])
        self.assertEqual(fee0 + balance0, broker.asset0.balance)
        self.assertEqual(fee1 + balance1, broker.asset1.balance)
        self.assertEqual(broker.position(new_position).uncollected_fee_token0, 0)
        self.assertEqual(broker.position(new_position).uncollected_fee_token0, 0)

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
