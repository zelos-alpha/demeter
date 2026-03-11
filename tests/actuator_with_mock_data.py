import unittest
from decimal import Decimal

import pandas as pd


from tests.utils import get_uni_v3_mock_data
from demeter import TokenInfo, Actuator, Strategy, Snapshot, MarketInfo
from demeter.uniswap import UniLpBalance, UniV3Pool, V3CoreLib, UniLpMarket
from demeter.uniswap.liquitidy_math import get_sqrt_ratio_at_tick

pd.options.display.max_columns = None
pd.options.display.max_rows = None
pd.set_option("display.width", 5000)

eth = TokenInfo(name="eth", decimal=18)
usdc = TokenInfo(name="usdc", decimal=6)
test_market = MarketInfo("uni_market")
tick_width = 500


class AddOnFirstTickStrategy(Strategy):
    def on_bar(self, snapshot: Snapshot):
        market: UniLpMarket = self.broker.markets[test_market]
        if snapshot.row_id == 0:
            tick = market.price_to_tick(snapshot.market_status[test_market].price)
            price_high = market.tick_to_price(tick - tick_width)
            price_low = market.tick_to_price(tick + tick_width)
            market.add_liquidity(price_low, price_high)


class TestActuator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.pool = UniV3Pool(usdc, eth, 0.05, usdc)
        super(TestActuator, self).__init__(*args, **kwargs)

    def test_load_clean_data(self):
        eth = TokenInfo(name="eth", decimal=18)
        usdc = TokenInfo(name="usdc", decimal=6)

        actuator: Actuator = Actuator()  # declare actuator
        actuator.strategy = AddOnFirstTickStrategy()

        broker = actuator.broker
        market = UniLpMarket(test_market, self.pool)
        center_tick = market.price_to_tick(1000)

        usdc_amount = 1000
        eth_amount = 1
        broker.add_market(market)
        broker.set_balance(usdc, usdc_amount)
        broker.set_balance(eth, eth_amount)

        token0_used, token1_used, pool_liquidity, position_info = V3CoreLib.new_position(
            self.pool,
            Decimal(usdc_amount * 100),
            Decimal(eth_amount * 100),
            center_tick - tick_width,
            center_tick + tick_width,
            get_sqrt_ratio_at_tick(center_tick),
        )
        market.data = get_uni_v3_mock_data(
            market,
            center_tick,
            usdc_amount * 10**usdc.decimal,
            eth_amount * 10**eth.decimal,
            pool_liquidity,
        )
        actuator.set_price(market.get_price_from_data())
        actuator.run()

        status: UniLpBalance = broker.get_account_status(actuator.token_prices.iloc[-1]).market_status[test_market]

        # share should be: position_liquidity / pool_total_liquidity == 0.01
        # but as we add liquidity with on bar, which means liquidity was added in the head of this minute.
        # so the liquidity we just provided should be added to total liquidity
        # so the share will be position_liquidity / (pool_total_liquidity+position_liquidity) == 1/(100+1)
        # the total fee will be: minute_swap_amount(1000) * fee(0.0005) *  share(1/(100+1)) * 5 times = usdc_fee(0.024752475247524754)
        self.assertEqual(status.quote_uncollected.quantize(Decimal("1.0000")), Decimal("0.0248"))
        self.assertEqual(status.base_uncollected.quantize(Decimal("1.0000000")), Decimal("0.0000248"))
