import unittest
from datetime import date
from decimal import Decimal

import pandas as pd

import demeter
from demeter import TokenInfo, Broker, MarketInfo, ChainType, MarketStatus
from demeter.uniswap import UniLpMarket, UniV3Pool, UniV3PoolStatus, UniswapMarketStatus

test_market = MarketInfo("market1")


class TestUniLpMarket(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.eth = TokenInfo(name="eth", decimal=18)
        self.usdc = TokenInfo(name="usdc", decimal=6)
        self.pool = UniV3Pool(self.usdc, self.eth, 0.05, self.usdc)
        super(TestUniLpMarket, self).__init__(*args, **kwargs)

    def test_price(self):
        broker = self.get_broker()
        # print(broker.markets[test_market].tick_to_price(206600))
        self.assertEqual(
            broker.markets[test_market].tick_to_price(206600).quantize(Decimal("1.00000")), Decimal("1066.41096")
        )

    def get_broker(self):
        broker = Broker()
        market = UniLpMarket(test_market, self.pool)
        broker.add_market(market)
        tick = 200000
        price = market.tick_to_price(tick)
        market.set_market_status(
            UniswapMarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[840860039126296093, 18714189922, 58280013108171131649, tick, price],
                    index=["inAmount0", "inAmount1", "currentLiquidity", "closeTick", "price"],
                ),
            ),
            price=None,
        )

        broker.set_balance(self.eth, 1)
        broker.set_balance(self.usdc, price)
        market.sqrt_price = demeter.uniswap.helper.tick_to_sqrt_price_x96(tick)
        return broker

    def check_type(self, broker):
        self.assertTrue(type(broker.assets[self.usdc].balance) is Decimal)
        self.assertTrue(type(broker.assets[self.usdc].decimal) is int)

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
        # print(broker)
        uni_market: UniLpMarket = broker.markets[test_market]
        self.assertEqual(uni_market.market_status.data.price, broker.assets[self.usdc].balance)
        self.assertEqual(1, broker.assets[self.eth].balance)
        self.assertEqual(uni_market.token0, self.usdc)
        self.assertEqual(uni_market.token1, self.eth)
        self.assertEqual(uni_market.quote_token, self.usdc)
        self.assertEqual(uni_market.base_token, self.eth)
        self.check_type(broker)

    def test_add_Liquidity(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        (new_position, base_used, quote_used, liquidity) = market.add_liquidity(
            market.market_status.data.price - 100,
            market.market_status.data.price + 100,
            broker.assets[self.usdc].balance,
            broker.assets[self.eth].balance,
        )
        self.assertEqual(new_position.lower_tick, 199526)
        self.assertEqual(new_position.upper_tick, 200496)
        self.assertEqual(liquidity, 1854454578816266)
        TestUniLpMarket.print_broker(broker)

    def test_add_Liquidity_default_param(self):
        """
        verify market will use all balance if amount param is null
        :return:
        :rtype:
        """
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        (new_position, base_used, quote_used, liquidity) = market.add_liquidity(
            market.market_status.data.price - 100,
            market.market_status.data.price + 100,
            broker.assets[self.usdc].balance,
            broker.assets[self.eth].balance,
        )
        broker2 = self.get_broker()
        market2: UniLpMarket = broker2.markets[test_market]
        (new_position2, base_used2, quote_used2, liquidity2) = market2.add_liquidity(
            market2.market_status.data.price - 100, market2.market_status.data.price + 100
        )
        self.assertEqual(base_used, base_used2)
        self.assertEqual(quote_used, quote_used2)

    def test_add_Liquidity_by_tick(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        (new_position, base_used, quote_used, liquidity) = market.add_liquidity_by_tick(199526, 200496)
        broker2 = self.get_broker()
        market2: UniLpMarket = broker2.markets[test_market]
        (new_position2, base_used2, quote_used2, liquidity2) = market2.add_liquidity(
            market2.market_status.data.price - 100, market2.market_status.data.price + 100
        )
        self.assertEqual(new_position, new_position2)
        self.assertEqual(liquidity, liquidity2)

    def test_add_Liquidity_by_tick_private(self):
        broker = self.get_broker()
        # should use all the balance
        market: UniLpMarket = broker.markets[test_market]
        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(
            market.market_status.data.price / 2,
            Decimal(0.5),
            market.market_status.data.closeTick - 100,
            market.market_status.data.closeTick + 100,
        )
        TestUniLpMarket.print_broker(broker)
        self.assertEqual(0.5, round(broker.assets[self.eth].balance, 4))

    def test_add_Liquidity_by_tick_again(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        # should use all the balance
        (new_position1, base_used1, quote_used1, liquidity1) = market._add_liquidity_by_tick(
            market.market_status.data.price / 2,
            Decimal(0.5),
            market.market_status.data.closeTick - 100,
            market.market_status.data.closeTick + 100,
        )
        TestUniLpMarket.print_broker(broker)
        self.assertEqual(0.5, round(broker.assets[self.eth].balance, 4))
        (new_position2, base_used2, quote_used2, liquidity2) = market._add_liquidity_by_tick(
            market.market_status.data.price / 2,
            Decimal(0.5),
            market.market_status.data.closeTick - 100,
            market.market_status.data.closeTick + 100,
        )
        TestUniLpMarket.print_broker(broker)
        self.assertEqual(base_used1, base_used2)
        self.assertEqual(quote_used1, quote_used2)
        self.assertEqual(liquidity1, liquidity2)
        self.assertEqual(new_position1, new_position2)
        self.assertEqual(liquidity1 + liquidity2, market.positions[new_position1].liquidity)

    def test_item_as_property(self):
        broker = self.get_broker()
        self.assertEqual(broker.markets[test_market], broker.markets.market1)
        self.assertEqual(broker.assets[self.usdc], broker.assets.USDC)
        self.assertEqual(broker.assets[self.eth], broker.assets.ETH)

    def test_print_broker(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        # should use all the balance
        market._add_liquidity_by_tick(
            market.market_status.data.price,
            Decimal(1),
            market.market_status.data.closeTick - 1000,
            market.market_status.data.closeTick + 1000,
        )

        print(broker.formatted_str())

    def test_add_Liquidity_use_all_balance(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets.market1
        # should use all the balance
        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(
            market.market_status.data.price,
            Decimal(1),
            market.market_status.data.closeTick - 1000,
            market.market_status.data.closeTick + 1000,
        )

        # print(new_position, base_used, quote_used, liquidity)
        # TestUniLpMarket.print_broker(broker)
        self.assertEqual(0, broker.assets[self.usdc].balance.quantize(Decimal(".000001")))
        self.assertEqual(0, broker.assets[self.eth].balance.quantize(Decimal(".0000001")))
        self.assertEqual(new_position.lower_tick, 199000)
        self.assertEqual(new_position.upper_tick, 201000)
        self.assertEqual(market.positions[new_position].liquidity, 931398660035583)
        self.assertEqual(liquidity, 931398660035583)

    def test_remove_position(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        token0_amt = broker.assets[self.usdc].balance
        token1_amt = broker.assets[self.eth].balance
        (new_position, base_used, quote_used, liquidity) = market.add_liquidity_by_tick(
            market.market_status.data.closeTick - 100, market.market_status.data.closeTick + 100, token0_amt, token1_amt
        )
        TestUniLpMarket.print_broker(broker)
        market.remove_liquidity(new_position)
        print("============liquidity has removed===================================================================")
        TestUniLpMarket.print_broker(broker)
        self.assertEqual(
            token0_amt.quantize(Decimal(".000001")), broker.assets[self.usdc].balance.quantize(Decimal(".000001"))
        )
        self.assertEqual(
            token1_amt.quantize(Decimal(".000001")), broker.assets[self.eth].balance.quantize(Decimal(".000001"))
        )
        self.assertEqual(len(market.positions), 0)

    def test_collect_fee(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]
        # should use all the balance
        (new_position, base_used, quote_used, liquidity) = market._add_liquidity_by_tick(
            market.market_status.data.price,
            Decimal(1),
            market.market_status.data.closeTick - 10,
            market.market_status.data.closeTick + 10,
        )
        TestUniLpMarket.print_broker(broker)
        eth_amount = 10000000000000000000
        usdc_amount = 10000000
        market.set_market_status(
            UniswapMarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[
                        market.market_status.data.closeTick,
                        liquidity * 100,
                        usdc_amount,
                        eth_amount,
                        market.tick_to_price(market.market_status.data.closeTick),
                    ],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )
        print("=========after a bar======================================================================")
        market.update()
        TestUniLpMarket.print_broker(broker)
        self.assertEqual(
            Decimal("0.000049504950495049504950495049504950495"), market.get_position(new_position).pending_amount0
        )
        self.assertEqual(
            Decimal("0.000049504950495049504950495049504950495"), market.get_position(new_position).pending_amount1
        )
        fee0 = market.get_position(new_position).pending_amount0
        fee1 = market.get_position(new_position).pending_amount1
        balance0 = broker.assets[self.usdc].balance
        balance1 = broker.assets[self.eth].balance
        market.collect_fee(new_position)
        print("=========collect======================================================================")
        TestUniLpMarket.print_broker(broker)
        self.assertEqual(fee0 + balance0, broker.assets[self.usdc].balance)
        self.assertEqual(fee1 + balance1, broker.assets[self.eth].balance)
        self.assertEqual(market.get_position(new_position).pending_amount0, 0)
        self.assertEqual(market.get_position(new_position).pending_amount0, 0)

    def test_buy(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]

        token0_before = broker.assets[self.usdc].balance
        token1_before = broker.assets[self.eth].balance
        TestUniLpMarket.print_broker(broker)
        market.buy(Decimal("0.5"))
        print("=========after buy======================================================================")
        TestUniLpMarket.print_broker(broker)
        self.assertEqual(broker.assets[self.eth].balance.quantize(Decimal(".000001")), token1_before + Decimal("0.5"))

        self.assertEqual(
            broker.assets[self.usdc].balance,
            token0_before - market.market_status.data.price * Decimal("0.5") / (1 - market.pool_info.fee_rate),
        )

    def test_sell(self):
        broker = self.get_broker()
        market: UniLpMarket = broker.markets[test_market]

        TestUniLpMarket.print_broker(broker)
        token0_before = broker.assets[self.usdc].balance
        token1_before = broker.assets[self.eth].balance
        market.sell(1)
        print("=========after buy======================================================================")
        TestUniLpMarket.print_broker(broker)
        self.assertEqual(
            broker.assets[self.usdc].balance,
            token0_before + market.market_status.data.price * Decimal(1) * (1 - market.pool_info.fee_rate),
        )
        self.assertEqual(broker.assets[self.eth].balance, token1_before - Decimal(1))

    def test_net_value(self):
        """
        Test net value before and after add liquidity
        """
        pool0p3 = UniV3Pool(self.usdc, self.eth, 0.3, self.usdc)
        broker = Broker(pool0p3)
        market = UniLpMarket(test_market, self.pool)
        broker.add_market(market)

        broker.set_balance(self.usdc, 2000)
        broker.set_balance(self.eth, 1)
        price = Decimal(1100)
        tick = market.price_to_tick(price)
        old_net_value = price * broker.assets[self.eth].balance + broker.assets[self.usdc].balance
        pos = market.add_liquidity_by_tick(market.price_to_tick(1200), market.price_to_tick(1000), tick=tick)
        market.set_market_status(
            UniswapMarketStatus(timestamp=None, data=UniV3PoolStatus(price=price, currentLiquidity=0)), None
        )
        status = broker.get_account_status({self.usdc.name: Decimal(1), self.eth.name: price})
        print(pos)
        print(status)
        self.assertEqual(old_net_value, round(status.net_value, 4))

    def test_net_value_with_different_pool_price(self):
        """
        Test net value if pool price and extern price is different
        """
        pool0p3 = UniV3Pool(self.usdc, self.eth, 0.3, self.usdc)
        broker = Broker(pool0p3)
        market = UniLpMarket(test_market, self.pool)
        broker.add_market(market)

        broker.set_balance(self.usdc, 2000)
        broker.set_balance(self.eth, 1)
        pool_price = Decimal(1100)
        extern_price = Decimal(2200)
        tick = market.price_to_tick(pool_price)
        old_net_value = extern_price * broker.assets[self.eth].balance + broker.assets[self.usdc].balance
        pos = market.add_liquidity_by_tick(market.price_to_tick(1200), market.price_to_tick(1000), tick=tick)
        market.set_market_status(
            UniswapMarketStatus(timestamp=None, data=UniV3PoolStatus(price=pool_price, currentLiquidity=0)), None
        )
        status = broker.get_account_status({self.usdc.name: Decimal(1), self.eth.name: extern_price})
        print(pos)
        print(status)
        self.assertEqual(Decimal("4201.1246"), round(status.net_value, 4))  # Impermanent loss

    def test_net_value2(self):
        """
        price will be provided via status
        :return:
        :rtype:
        """
        pool0p3 = UniV3Pool(self.usdc, self.eth, 0.3, self.usdc)
        broker = Broker(pool0p3)
        market = UniLpMarket(test_market, self.pool)
        broker.add_market(market)

        broker.set_balance(self.usdc, 1100)
        broker.set_balance(self.eth, 1)
        price = Decimal(1100)
        old_net_value = price * broker.assets[self.eth].balance + broker.assets[self.usdc].balance
        print(old_net_value)
        tick = market.price_to_tick(price)
        market.set_market_status(
            UniswapMarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[tick, Decimal(0), Decimal(0), Decimal(0), price],
                    index=["closeTick", "currentLiquidity", "inAmount0", "inAmount1", "price"],
                ),
            ),
            price=None,
        )
        pos = market.add_liquidity(1000, 1200)
        price_map = {self.usdc.name: Decimal(1), self.eth.name: price}
        status = broker.get_account_status(price_map)
        self.assertEqual(market.get_market_balance().net_value, market.get_market_balance(price_map).net_value)
        print(pos)
        print(status)
        self.assertEqual(old_net_value, round(status.net_value, 4))

    def test_get_price(self):
        market = UniLpMarket(test_market, self.pool)
        market.data_path = "data"
        market.load_data(
            ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", date(2023, 8, 15), date(2023, 8, 15)
        )
        prices: pd.DataFrame = market.get_price_from_data()
        self.assertEqual(len(prices.index), 1440)
        self.assertEqual(prices.columns[0], "ETH")
        self.assertEqual(prices.columns[1], "USDC")
        self.assertEqual(prices.iloc[100]["USDC"], 1)
        print("test_get_price")
        print(prices)

    def test_even_rebalance_buy(self):
        broker = self.get_broker()
        broker.set_balance(self.usdc, 3000)
        market: UniLpMarket = broker.markets.market1
        market.even_rebalance()
        self.assertEqual(
            broker.get_token_balance(self.usdc).quantize(Decimal("0.001")),
            (broker.get_token_balance(self.eth) * market.market_status.data.price).quantize(Decimal("0.001")),
        )
        pass

    def test_even_rebalance_sell(self):
        broker = self.get_broker()
        broker.set_balance(self.eth, 10)
        market: UniLpMarket = broker.markets.market1
        market.even_rebalance()
        self.assertEqual(
            broker.get_token_balance(self.usdc), broker.get_token_balance(self.eth) * market.market_status.data.price
        )
        pass
