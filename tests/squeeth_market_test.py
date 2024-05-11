from datetime import datetime, date
from decimal import Decimal
from unittest import TestCase

import pandas as pd

from demeter import MarketStatus, TokenInfo, Broker, MarketInfo, MarketTypeEnum
from demeter.squeeth import SqueethBalance, VaultKey
from demeter.squeeth.market import SqueethMarket
from demeter.uniswap import UniLpMarket, UniV3Pool, UniswapMarketStatus, UniLpBalance

weth = TokenInfo("weth", 18)
oSQTH = TokenInfo("osqth", 18)

osqth_pool = MarketInfo("Uni", MarketTypeEnum.uniswap_v3)
squeeth_key = MarketInfo("Squeeth", MarketTypeEnum.squeeth)

d4 = Decimal("0.0001")
OSQTH_ETH = Decimal("18.65573666468601")  # osqth/eth, osqth is base
ETH_OSQTH = Decimal("0.05360281493964960270664351043")
OSQTH_OF_1_ETH = Decimal("18.78742045363579454725969526")
TICK = 29263  # uni_market.price_to_tick(0.0536)


class TestSqueethMarket(TestCase):
    def test_get_twap_price(self):
        t = pd.date_range(datetime(2024, 1, 1), datetime(2024, 1, 1, 0, 7), freq="min")
        data = pd.DataFrame(
            index=t,
            data={
                "norm_factor": [0, 0, 0, 0, 0, 0, 0, 0],
                "ETH": [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007],
                "OSQTH": [100, 101, 102, 103, 104, 105, 106, 107],
            },
        )
        market = SqueethMarket(squeeth_key, None, data)
        market.set_market_status(MarketStatus(datetime(2024, 1, 1, 0, 7)), None)
        price = market.get_twap_price(TokenInfo("eth", 18))
        self.assertEqual(price, 1003.9980079631864)

    def get_broker(self):
        broker = Broker()
        uni_market = UniLpMarket(
            osqth_pool,
            UniV3Pool(weth, oSQTH, 0.3, weth),
        )
        squeeth_market = SqueethMarket(squeeth_key, uni_market)
        broker.add_market(uni_market)
        broker.add_market(squeeth_market)
        price = uni_market.tick_to_price(TICK)  # Decimal('0.05360281493964960270664351043')
        uni_market.set_market_status(
            UniswapMarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[0, 0, 0, Decimal(TICK), Decimal(price)],
                    index=["inAmount0", "inAmount1", "currentLiquidity", "closeTick", "price"],
                ),
            ),
            price=None,
        )
        squeeth_market.set_market_status(
            MarketStatus(
                timestamp=None,
                data=pd.Series(
                    data=[Decimal("0.2894"), Decimal("1839.2227"), ETH_OSQTH],
                    index=["norm_factor", "WETH", "OSQTH"],
                ),
            ),
            price=None,
        )
        broker.set_balance(weth, 10)
        broker.set_balance(oSQTH, OSQTH_ETH * 10)  # almost 1:1 in value
        return broker

    def test_get_twap_price_short(self):
        t = pd.date_range(datetime(2024, 1, 1), datetime(2024, 1, 1, 0, 7), freq="min")
        data = pd.DataFrame(
            index=t,
            data={
                "norm_factor": [0, 0, 0, 0, 0, 0, 0, 0],
                "ETH": [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007],
                "OSQTH": [100, 101, 102, 103, 104, 105, 106, 107],
            },
        )
        market = SqueethMarket(squeeth_key, None, data)
        market.set_market_status(MarketStatus(datetime(2024, 1, 1, 0, 1)), None)
        price = market.get_twap_price(TokenInfo("eth", 18))
        self.assertEqual(price, 1000.49987506246)

    def test_load_data(self):
        market = SqueethMarket(squeeth_key, None)
        market.load_data(date(2023, 8, 14), date(2023, 8, 17))
        self.assertEqual(len(market.data.index), 5760)
        self.assertEqual(market.data.head(1).index[0], datetime(2023, 8, 14))
        self.assertEqual(market.data.tail(1).index[0], datetime(2023, 8, 17, 23, 59))
        pass

    def test_get_price(self):
        market = SqueethMarket(squeeth_key, None)
        market.load_data(date(2023, 8, 14), date(2023, 8, 17))
        price_df = market.get_price_from_data()
        self.assertTrue(isinstance(price_df.iloc[0]["WETH"], Decimal))
        self.assertEqual(price_df.iloc[0]["WETH"], Decimal("1839.222732716025"))
        self.assertEqual(price_df.iloc[0]["OSQTH"], Decimal("98.64923946816276798066711581"))
        pass

    # region long
    def test_long_buy(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        from_amount = OSQTH_ETH * Decimal(1)
        fee, eth_amount, osqth_amount = market.buy_squeeth(from_amount)
        self.assertEqual(osqth_amount, from_amount)
        self.assertEqual(eth_amount.quantize(d4), Decimal(1).quantize(d4))
        self.assertEqual(fee.quantize(d4), Decimal("0.003").quantize(d4))
        self.assertEqual(broker.get_token_balance(weth).quantize(d4), (10 - fee - eth_amount).quantize(d4))
        self.assertEqual(broker.get_token_balance(oSQTH).quantize(d4), (OSQTH_ETH * 10 + osqth_amount).quantize(d4))
        self.assertEqual(market.osqth_balance.quantize(d4), (OSQTH_ETH * 10 + osqth_amount).quantize(d4))

    def test_long_sell(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        from_amount = OSQTH_ETH * Decimal(1)
        fee, eth_amount, osqth_amount = market.sell_squeeth(from_amount)
        # self.assertEqual(osqth_amount, from_amount)
        self.assertEqual(eth_amount.quantize(d4), Decimal("0.997").quantize(d4))
        self.assertEqual(fee.quantize(d4), Decimal("0.003").quantize(d4))
        self.assertEqual(broker.get_token_balance(weth).quantize(d4), Decimal(10.997).quantize(d4))
        self.assertEqual(broker.get_token_balance(oSQTH).quantize(d4), (OSQTH_ETH * 10 - from_amount).quantize(d4))

    def test_status(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        balance: SqueethBalance = market.get_market_balance()
        self.assertEqual(balance.osqth_short_amount, Decimal(0))
        self.assertEqual(balance.net_value, Decimal(0))
        self.assertEqual(balance.osqth_long_amount, OSQTH_ETH * 10)
        self.assertEqual(balance.gamma, Decimal(2))
        pass

    # endregion
    # region short
    def test_get_mint_amount(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        amount1 = market.collateral_amount_to_osqth(2, 2)
        self.assertEqual(amount1, OSQTH_OF_1_ETH)

    def test_deposit_mint_by_collat_rate(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        vault_key, osqth_mint_amount = market.open_deposit_mint_by_collat_rate(2, 2)
        self.assertEqual(osqth_mint_amount, OSQTH_OF_1_ETH)
        self.assertEqual(market.vault[vault_key].collateral_amount, Decimal(2))
        self.assertEqual(broker.get_token_balance(weth), Decimal(8))
        self.assertEqual(market.vault[vault_key].osqth_short_amount, osqth_mint_amount)
        self.assertEqual(broker.get_token_balance(oSQTH), osqth_mint_amount + OSQTH_ETH * 10)
        # index and mark is not same
        self.assertNotEqual(osqth_mint_amount, OSQTH_ETH)

    def test_deposit_mint_by_collat_rate_not_exist_vault(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        try:
            vault_key, osqth_mint_amount = market.open_deposit_mint_by_collat_rate(2, 2, VaultKey(2))
        except Exception as e:
            self.assertIn("VaultKey", str(e))

    def test_deposit_mint_multiple_times(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        amount1 = market.collateral_amount_to_osqth(2, 4)

        vault_key, osqth_mint_amount = market.open_deposit_mint(2, amount1)
        self.assertEqual(osqth_mint_amount, OSQTH_OF_1_ETH / 2)
        self.assertEqual(market.vault[vault_key].osqth_short_amount, osqth_mint_amount)
        self.assertEqual(broker.get_token_balance(oSQTH), osqth_mint_amount + OSQTH_ETH * 10)

        vault_key, osqth_mint_amount2 = market.open_deposit_mint(0, amount1, vault_key)
        vault = market.vault[vault_key]
        self.assertEqual(vault.collateral_amount, 2)
        self.assertEqual(market.vault[vault_key].osqth_short_amount, osqth_mint_amount * 2)
        self.assertEqual(
            broker.get_token_balance(oSQTH).quantize(d4), (osqth_mint_amount * 2 + OSQTH_ETH * 10).quantize(d4)
        )
        # append collateral
        vault_key, osqth_mint_amount2 = market.open_deposit_mint(2, amount1, vault_key)
        vault = market.vault[vault_key]
        self.assertEqual(vault.collateral_amount, 4)
        self.assertEqual(market.vault[vault_key].osqth_short_amount, amount1 * 3)
        self.assertEqual(
            broker.get_token_balance(oSQTH).quantize(d4), (osqth_mint_amount * 3 + OSQTH_ETH * 10).quantize(d4)
        )

    def test_collateral_rate(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        amount1 = market.collateral_amount_to_osqth(2, 2)

        vault_key, osqth_mint_amount = market.open_deposit_mint(2, amount1)
        self.assertEqual(osqth_mint_amount, OSQTH_OF_1_ETH)
        self.assertEqual(market.vault[vault_key].osqth_short_amount, osqth_mint_amount)
        self.assertEqual(broker.get_token_balance(oSQTH), osqth_mint_amount + OSQTH_ETH * 10)

        ratio, price = market.get_collat_ratio_and_liq_price(vault_key)
        self.assertEqual(ratio, Decimal(2))
        self.assertEqual(price.quantize(d4), Decimal("2452.2969").quantize(d4))

    def test_get_balance(self):
        broker = self.get_broker()
        broker.set_balance(oSQTH, Decimal(0))
        market: SqueethMarket = broker.markets[squeeth_key]
        amount1 = market.collateral_amount_to_osqth(2, 2)

        vault_key, osqth_mint_amount = market.open_deposit_mint(2, amount1)

        mb: SqueethBalance = market.get_market_balance()
        self.assertEqual(mb.collateral_amount, Decimal(2))
        self.assertEqual(mb.osqth_long_amount, OSQTH_OF_1_ETH)
        self.assertEqual(mb.osqth_short_amount, OSQTH_OF_1_ETH)
        self.assertEqual(mb.osqth_net_amount, Decimal(0))
        self.assertEqual(mb.collateral_ratio, Decimal(2))
        self.assertEqual(mb.vault_count, 1)

    def test_deposit(self):
        broker = self.get_broker()
        broker.set_balance(oSQTH, Decimal(0))
        market: SqueethMarket = broker.markets[squeeth_key]
        amount1 = market.collateral_amount_to_osqth(2, 2)

        vault_key, osqth_mint_amount = market.open_deposit_mint(2, amount1)
        market.deposit(vault_key, eth_value=2)
        mb: SqueethBalance = market.get_market_balance()
        self.assertEqual(mb.collateral_amount, Decimal(4))
        self.assertEqual(mb.collateral_ratio, Decimal(4))
        self.assertEqual(broker.get_token_balance(weth), Decimal(6))

    def test_withdraw(self):
        broker = self.get_broker()
        broker.set_balance(oSQTH, Decimal(0))
        market: SqueethMarket = broker.markets[squeeth_key]
        amount1 = market.collateral_amount_to_osqth(4, 4)

        vault_key, osqth_mint_amount = market.open_deposit_mint(4, amount1)
        market.burn_and_withdraw(vault_key, 0, 2)
        mb: SqueethBalance = market.get_market_balance()
        self.assertEqual(mb.collateral_amount, Decimal(2))
        self.assertEqual(mb.osqth_long_amount, OSQTH_OF_1_ETH)
        self.assertEqual(mb.osqth_short_amount, OSQTH_OF_1_ETH)
        self.assertEqual(mb.osqth_net_amount, Decimal(0))
        self.assertEqual(mb.collateral_ratio, Decimal(2))
        self.assertEqual(mb.vault_count, 1)
        self.assertEqual(broker.get_token_balance(weth), Decimal(8))

    def test_burn_and_withdraw(self):
        broker = self.get_broker()
        broker.set_balance(oSQTH, Decimal(0))
        market: SqueethMarket = broker.markets[squeeth_key]
        vault_key, osqth_mint_amount = market.open_deposit_mint_by_collat_rate(2, 2)
        market.burn_and_withdraw(vault_key, osqth_mint_amount, 2)
        mb: SqueethBalance = market.get_market_balance()
        self.assertEqual(mb.collateral_amount, Decimal(0))
        self.assertEqual(mb.osqth_long_amount, Decimal(0))
        self.assertEqual(mb.osqth_short_amount, Decimal(0))
        self.assertEqual(mb.collateral_ratio, Decimal(0))
        self.assertEqual(mb.vault_count, 1)
        self.assertEqual(broker.get_token_balance(weth), Decimal(10))

    def test_withdraw_collateral_ratio_low(self):
        broker = self.get_broker()
        broker.set_balance(oSQTH, Decimal(0))
        market: SqueethMarket = broker.markets[squeeth_key]
        vault_key, osqth_mint_amount = market.open_deposit_mint_by_collat_rate(2, 2)
        try:
            market.burn_and_withdraw(vault_key, 0, 2)
        except Exception as e:
            self.assertIn("Vault collateral rate is not safe", str(e))

    # endregion

    # region lp
    # add lp

    def test_add_lp(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        vault_key, osqth_mint_amount = market.open_deposit_mint_by_collat_rate(2, 2)
        pos_key, base_used, quote_used, liquidity = market.squeeth_uni_pool.add_liquidity_by_tick(
            TICK - 1000, TICK + 1000, 3, 9999
        )
        market.deposit_uni_position(vault_key, pos_key)

    # balance with lp
    def test_add_lp_balance(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        vault_key, osqth_mint_amount = market.open_deposit_mint_by_collat_rate(2, 2)
        pos_key, base_used, quote_used, liquidity = market.squeeth_uni_pool.add_liquidity_by_tick(
            TICK - 1000, TICK + 1000, 3, 9999
        )
        quote_used_in_eth = (
            quote_used / SqueethMarket.INDEX_SCALE * market.get_norm_factor() * market.get_twap_price(weth)
        )
        uni_balance: UniLpBalance = market.squeeth_uni_pool.get_market_balance()
        net_value_in_uni = uni_balance.net_value
        self.assertEqual(net_value_in_uni.quantize(d4), (base_used + quote_used * ETH_OSQTH).quantize(d4))

        market.deposit_uni_position(vault_key, pos_key)
        self.assertEqual(market.squeeth_uni_pool.positions[pos_key].transferred, True)
        self.assertEqual(market.vault[vault_key].uni_nft_id, pos_key)
        # nft has been transferred to squeeth, so net value is zero
        uni_balance: UniLpBalance = market.squeeth_uni_pool.get_market_balance()
        self.assertEqual(uni_balance.net_value, Decimal(0))
        self.assertEqual(uni_balance.position_count, 0)

        market_balance: SqueethBalance = market.get_market_balance()
        self.assertEqual(market_balance.osqth_long_amount, OSQTH_ETH * 10 - quote_used + OSQTH_OF_1_ETH)
        self.assertEqual(market_balance.collateral_amount.quantize(d4), (Decimal(5) + quote_used_in_eth).quantize(d4))

        pass

    # safe with lp
    def test_safe_with_lp(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        pos_key, base_used, quote_used, liquidity = market.squeeth_uni_pool.add_liquidity_by_tick(
            TICK - 1000, TICK + 1000, 3, 9999
        )
        vault_key, osqth_mint_amount = market.open_deposit_mint_by_collat_rate(2, 2, uni_position=pos_key)
        market.burn_and_withdraw(vault_key, 0, 2)
        market_balance: SqueethBalance = market.get_market_balance()
        quote_used_in_eth = (
            quote_used / SqueethMarket.INDEX_SCALE * market.get_norm_factor() * market.get_twap_price(weth)
        )
        self.assertEqual(market_balance.collateral_amount.quantize(d4), (Decimal(3) + quote_used_in_eth).quantize(d4))

    # remove lp
    def test_remove_lp(self):
        broker = self.get_broker()
        market: SqueethMarket = broker.markets[squeeth_key]
        pos_key, base_used, quote_used, liquidity = market.squeeth_uni_pool.add_liquidity_by_tick(
            TICK - 1000, TICK + 1000, 3, 9999
        )
        vault_key, osqth_mint_amount = market.open_deposit_mint_by_collat_rate(2, 2, uni_position=pos_key)
        market.withdraw_uni_position(vault_key, pos_key)
        market_balance: SqueethBalance = market.get_market_balance()
        self.assertEqual(market_balance.collateral_amount, Decimal(2))

        uni_balance: UniLpBalance = market.squeeth_uni_pool.get_market_balance()
        quote_used_in_eth = quote_used * ETH_OSQTH
        self.assertEqual(uni_balance.net_value.quantize(d4), (quote_used_in_eth + base_used).quantize(d4))
        self.assertEqual(uni_balance.position_count, 1)
        pass

    # endregion
    # region liquidation

    # endregion
