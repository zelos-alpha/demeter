import unittest
from decimal import Decimal
import pandas as pd
import demeter
from demeter import TokenInfo, Broker, MarketInfo, MarketStatus
from demeter.uniswap import UniLpMarket, UniV3Pool, UniV3PoolStatus, helper, PositionInfo

test_market = MarketInfo("market1")


class TestUniLpMarketToken1Quote(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.eth = TokenInfo(name="eth", decimal=18)
        self.usdc = TokenInfo(name="usdc", decimal=6)
        self.pool = UniV3Pool(token0=self.eth, token1=self.usdc, fee=0.05, quote_token=self.usdc)
        super(TestUniLpMarketToken1Quote, self).__init__(*args, **kwargs)

    def get_broker(self) -> Broker:
        # 1066.091101419725805850594389
        broker = Broker()
        market = UniLpMarket(test_market, self.pool)
        broker.add_market(market)
        tick = -206600
        price = market.tick_to_price(tick)
        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[1107562474636574291, 18714189922, 58280013108171131649, tick, price],
                    index=["inAmount0", "inAmount1", "currentLiquidity", "closeTick", "price"],
                ),
            ),
            price=None,
        )
        broker.set_balance(self.eth, 1)
        broker.set_balance(self.usdc, price)
        market.sqrt_price = demeter.uniswap.helper.tick_to_sqrt_price_x96(tick)

        # https://etherscan.io/address/0x4e68ccd3e89f51c3074ca5072bbac773960dfa36#readContract
        return broker

    @staticmethod
    def print_broker(broker):
        print("broker:", broker)
        uni_market: UniLpMarket = broker.markets[test_market]
        for k, v in uni_market.positions.items():
            print("=====begin print get_position=====")
            print(k)
            print(v)
            print("=====end======")
        # print("assets:", broker.get_account_status())

    def test_new(self):
        broker = self.get_broker()
        uni_market: UniLpMarket = broker.markets[test_market]
        print(broker)
        self.assertEqual(1, broker.assets[self.eth].balance)
        self.assertEqual(uni_market.market_status.data.price, broker.assets[self.usdc].balance)
        self.assertEqual(uni_market.quote_token, self.usdc)
        self.assertEqual(uni_market.base_token, self.eth)

    def test_add_Liquidity_by_tick(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        (new_position, base_used, quote_used, liquidity) = market.add_liquidity_by_tick(
            market.market_status.data.closeTick - 100, market.market_status.data.closeTick + 100
        )

        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(0, broker.assets[self.eth].balance.quantize(Decimal(".0000001")))
        self.assertEqual(0, broker.assets[self.usdc].balance.quantize(Decimal(".00001")))
        self.assertEqual(6547857793831120, liquidity)

    def test_remove_position(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        quote_amt = broker.assets[self.eth].balance
        base_amt = broker.assets[self.usdc].balance
        (new_position, base_used, quote_used, liquidity) = market.add_liquidity(
            market.market_status.data.price - 100,
            market.market_status.data.price + 100,
            base_amt,
            quote_amt,
        )
        TestUniLpMarketToken1Quote.print_broker(broker)
        market.remove_liquidity(new_position)
        print("===============================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(
            quote_amt.quantize(Decimal(".00001")), broker.assets[self.eth].balance.quantize(Decimal(".00001"))
        )
        self.assertEqual(
            base_amt.quantize(Decimal(".00001")), broker.assets[self.usdc].balance.quantize(Decimal(".00001"))
        )
        self.assertEqual(len(market.positions), 0)

    def test_collect_fee(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(
            Decimal(1),
            market.market_status.data.price,
            market.market_status.data.closeTick - 10,
            market.market_status.data.closeTick + 10,
        )
        TestUniLpMarketToken1Quote.print_broker(broker)
        eth_amount = 10000000000000000000
        usdc_amount = 10000000
        # row = Series(index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1"],
        #              data=[broker.pool_status.current_tick, liquidity * 100,
        #                    eth_amount,
        #                    usdc_amount])
        price = market.tick_to_price(market.market_status.data.closeTick)
        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[market.market_status.data.closeTick, liquidity * 100, eth_amount, usdc_amount, price],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )
        market.update()
        print("=========after a bar======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)

        self.assertEqual(
            Decimal("0.000049504950495049504950495049504950495"), market.get_position(new_position).pending_amount0
        )
        self.assertEqual(
            Decimal("0.000049504950495049504950495049504950495"), market.get_position(new_position).pending_amount1
        )

        fee0 = market.get_position(new_position).pending_amount0
        fee1 = market.get_position(new_position).pending_amount1
        balance0 = broker.assets[self.eth].balance
        balance1 = broker.assets[self.usdc].balance
        market.collect_fee(new_position)
        print("=========collect======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(fee0 + balance0, broker.assets[self.eth].balance)
        self.assertEqual(fee1 + balance1, broker.assets[self.usdc].balance)
        self.assertEqual(market.positions[new_position].pending_amount0, 0)

    def test_collect_fee_down(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        current_tick = market.market_status.data.closeTick
        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(
            Decimal(1), market.market_status.data.price, current_tick - 100, current_tick - 10
        )
        TestUniLpMarketToken1Quote.print_broker(broker)
        eth_amount = 10000000000000000000
        usdc_amount = 10000000
        price = market.tick_to_price(current_tick)
        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[current_tick, liquidity * 100, eth_amount, usdc_amount, price],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )
        market.last_tick = current_tick - 120
        market.update()
        print("=========after a bar======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)

        self.assertEqual(
            Decimal("0.000037128712871287128712871287128712871"), market.get_position(new_position).pending_amount0
        )
        self.assertEqual(
            Decimal("0.000037128712871287128712871287128712871"), market.get_position(new_position).pending_amount1
        )

        fee0 = market.get_position(new_position).pending_amount0
        fee1 = market.get_position(new_position).pending_amount1
        balance0 = broker.assets[self.eth].balance
        balance1 = broker.assets[self.usdc].balance
        market.collect_fee(new_position)
        print("=========collect======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(fee0 + balance0, broker.assets[self.eth].balance)
        self.assertEqual(fee1 + balance1, broker.assets[self.usdc].balance)
        self.assertEqual(market.positions[new_position].pending_amount0, 0)

    def test_collect_fee_in_out(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(
            Decimal(1),
            market.market_status.data.price,
            market.market_status.data.closeTick - 100,
            market.market_status.data.closeTick - 10,
        )
        TestUniLpMarketToken1Quote.print_broker(broker)
        eth_amount = 10000000000000000000
        usdc_amount = 10000000

        current = market.market_status.data.closeTick
        price = market.tick_to_price(market.market_status.data.closeTick)
        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[current, liquidity * 100, eth_amount, usdc_amount, price],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )
        market.last_tick = current - 50
        market.update()
        print("=========after a bar======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)

        self.assertEqual(
            Decimal("0.000039603960396039603960396039603960396"), market.get_position(new_position).pending_amount0
        )
        self.assertEqual(
            Decimal("0.000039603960396039603960396039603960396"), market.get_position(new_position).pending_amount1
        )

        fee0 = market.get_position(new_position).pending_amount0
        fee1 = market.get_position(new_position).pending_amount1
        balance0 = broker.assets[self.eth].balance
        balance1 = broker.assets[self.usdc].balance
        market.collect_fee(new_position)
        print("=========collect======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(fee0 + balance0, broker.assets[self.eth].balance)
        self.assertEqual(fee1 + balance1, broker.assets[self.usdc].balance)
        self.assertEqual(market.positions[new_position].pending_amount0, 0)

    def test_collect_fee_up(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        current_tick = market.market_status.data.closeTick

        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(
            Decimal(1), market.market_status.data.price, current_tick - 100, current_tick - 10
        )
        TestUniLpMarketToken1Quote.print_broker(broker)
        eth_amount = 10000000000000000000
        usdc_amount = 10000000
        price = market.tick_to_price(current_tick)
        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[current_tick - 120, liquidity * 100, eth_amount, usdc_amount, price],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )
        market.last_tick = current_tick
        market.update()
        print("=========after a bar======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)

        self.assertEqual(
            Decimal("0.000037128712871287128712871287128712871"), market.get_position(new_position).pending_amount0
        )
        self.assertEqual(
            Decimal("0.000037128712871287128712871287128712871"), market.get_position(new_position).pending_amount1
        )

        fee0 = market.get_position(new_position).pending_amount0
        fee1 = market.get_position(new_position).pending_amount1
        balance0 = broker.assets[self.eth].balance
        balance1 = broker.assets[self.usdc].balance
        market.collect_fee(new_position)
        print("=========collect======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(fee0 + balance0, broker.assets[self.eth].balance)
        self.assertEqual(fee1 + balance1, broker.assets[self.usdc].balance)
        self.assertEqual(market.positions[new_position].pending_amount0, 0)

    def test_collect_fee_up_update_twice(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        current_tick = market.market_status.data.closeTick

        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(
            Decimal(1), market.market_status.data.price, current_tick - 100, current_tick - 10
        )
        TestUniLpMarketToken1Quote.print_broker(broker)
        eth_amount = 10000000000000000000
        usdc_amount = 10000000

        price = market.tick_to_price(current_tick)

        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[current_tick, liquidity * 100, eth_amount, usdc_amount, price],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )

        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[current_tick - 120, liquidity * 100, eth_amount, usdc_amount, price],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )
        market.update()
        print("=========after a bar======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)

        self.assertEqual(
            Decimal("0.000037128712871287128712871287128712871"), market.get_position(new_position).pending_amount0
        )
        self.assertEqual(
            Decimal("0.000037128712871287128712871287128712871"), market.get_position(new_position).pending_amount1
        )

        fee0 = market.get_position(new_position).pending_amount0
        fee1 = market.get_position(new_position).pending_amount1
        balance0 = broker.assets[self.eth].balance
        balance1 = broker.assets[self.usdc].balance
        market.collect_fee(new_position)
        print("=========collect======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(fee0 + balance0, broker.assets[self.eth].balance)
        self.assertEqual(fee1 + balance1, broker.assets[self.usdc].balance)
        self.assertEqual(market.positions[new_position].pending_amount0, 0)

    def test_collect_fee_no_fee(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(
            Decimal(1),
            market.market_status.data.price,
            market.market_status.data.closeTick - 100,
            market.market_status.data.closeTick - 10,
        )
        TestUniLpMarketToken1Quote.print_broker(broker)
        eth_amount = 10000000000000000000
        usdc_amount = 10000000
        price = market.tick_to_price(market.market_status.data.closeTick)
        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[market.market_status.data.closeTick - 120, liquidity * 100, eth_amount, usdc_amount, price],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )
        market.last_tick = market.market_status.data.closeTick - 110
        market.update()
        print("=========after a bar======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)

        self.assertTrue(Decimal("0") == market.get_position(new_position).pending_amount0)
        self.assertTrue(Decimal("0") == market.get_position(new_position).pending_amount1)

        fee0 = market.get_position(new_position).pending_amount0
        fee1 = market.get_position(new_position).pending_amount1
        balance0 = broker.assets[self.eth].balance
        balance1 = broker.assets[self.usdc].balance
        market.collect_fee(new_position)
        print("=========collect======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(fee0 + balance0, broker.assets[self.eth].balance)
        self.assertEqual(fee1 + balance1, broker.assets[self.usdc].balance)
        self.assertEqual(market.positions[new_position].pending_amount0, 0)

    def test_collect_fee_same_tick(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        current_tick = market.market_status.data.closeTick
        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(
            Decimal(1), market.market_status.data.price, current_tick - 100, current_tick - 10
        )
        TestUniLpMarketToken1Quote.print_broker(broker)
        eth_amount = 10000000000000000000
        usdc_amount = 10000000

        price = market.tick_to_price(current_tick)
        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[current_tick, liquidity * 100, eth_amount, usdc_amount, price],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )
        market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[current_tick - 100, liquidity * 100, eth_amount, usdc_amount, price],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )
        market.update()
        print("=========after a bar======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)

        self.assertEqual(
            Decimal("0.000044554455445544554455445544554455446"), market.get_position(new_position).pending_amount0
        )
        self.assertEqual(
            Decimal("0.000044554455445544554455445544554455446"), market.get_position(new_position).pending_amount1
        )

        fee0 = market.get_position(new_position).pending_amount0
        fee1 = market.get_position(new_position).pending_amount1
        balance0 = broker.assets[self.eth].balance
        balance1 = broker.assets[self.usdc].balance
        market.collect_fee(new_position)
        print("=========collect======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(fee0 + balance0, broker.assets[self.eth].balance)
        self.assertEqual(fee1 + balance1, broker.assets[self.usdc].balance)
        self.assertEqual(market.positions[new_position].pending_amount0, 0)

    def test_buy(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]

        token0_before = broker.assets[self.eth].balance
        token1_before = broker.assets[self.usdc].balance
        TestUniLpMarketToken1Quote.print_broker(broker)
        buy_amount = Decimal("0.5")
        market.buy(buy_amount)
        print("=========after buy======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(
            broker.assets[self.usdc].balance,
            token1_before - market.market_status.data.price * buy_amount / (1 - market.pool_info.fee_rate),
        )
        self.assertEqual(broker.assets[self.eth].balance.quantize(Decimal("0.000001")), token0_before + buy_amount)

    def test_sell(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]

        TestUniLpMarketToken1Quote.print_broker(broker)
        token0_before = broker.assets[self.eth].balance
        token1_before = broker.assets[self.usdc].balance
        market.sell(1)
        print("=========after buy======================================================================")
        TestUniLpMarketToken1Quote.print_broker(broker)
        self.assertEqual(
            broker.assets[market.token1].balance,
            token1_before + market.market_status.data.price * Decimal(1) * (1 - market.pool_info.fee_rate),
        )
        self.assertEqual(broker.assets[market.token0].balance, token0_before - Decimal(1))

    def test_estimate_liquidity(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]

        print(market.estimate_liquidity(Decimal(1), PositionInfo(-206800, -206400)))
        print(market.estimate_liquidity(Decimal(1), PositionInfo(-207001, -206601)))
        print(market.estimate_liquidity(Decimal(1), PositionInfo(-206599, -206199)))
