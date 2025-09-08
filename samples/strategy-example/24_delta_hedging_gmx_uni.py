import pickle
from datetime import date, datetime
from decimal import Decimal
from math import sqrt

import numpy as np
import pandas as pd
from scipy import linalg

from demeter import ChainType, Strategy, TokenInfo, Actuator, MarketInfo, Snapshot, AtTimeTrigger, MarketTypeEnum
from demeter.gmx import GmxV2Market
from demeter.gmx._typing2 import GmxV2Pool
from demeter.uniswap import UniV3Pool, UniLpMarket, V3CoreLib
from demeter.uniswap.helper import base_unit_price_to_sqrt_price_x96

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)

H = Decimal("1.2")  # upper tick range
L = Decimal("0.8")  # lower tick range


def calc_delta_neutral_v2(ph, pl, delta=0.0):
    # -1 * V_u_gmx + (V_e_uni + V_u_uni) * liq * V_e_uni_percent = 0
    # 0 * V_u_gmx + V_e_uni - V_u_uni * uni_amount_constraint = 0
    # V_u_gmx + V_e_uni + V_u_uni = 1

    V_e_uni_percent = (1 - 1 / ph ** 0.5)
    V_u_uni_percent = (1 - pl ** 0.5)
    uni_amount_cons = V_e_uni_percent / V_u_uni_percent  # V_e_uni / V_u_uni
    liq = 1 / (2 - 1 / sqrt(ph) - sqrt(pl))

    params = np.array([[-1, liq * V_e_uni_percent, liq * V_e_uni_percent], [0, 1, -uni_amount_cons], [1, 1, 1]])
    results = np.array([delta, 0, 1])
    V_u_gmx, V_e_uni, V_u_uni = linalg.solve(params, results)
    return V_u_gmx, V_e_uni, V_u_uni


class DeltaHedgingStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.gmx_leverage = 2
        self.last_collect_fee0 = 0
        self.last_collect_fee1 = 0
        V_u_gmx, V_e_uni, V_u_uni = calc_delta_neutral_v2(float(H), float(L))
        self.usdc_gmx_pos = Decimal(V_u_gmx)
        self.eth_uni_lp = Decimal(V_e_uni)
        self.usdc_uni_lp = Decimal(V_u_uni)

    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime.combine(start_date, datetime.min.time()), do=self.change_position)
        self.triggers.append(new_trigger)

    def reset_funds(self):
        # withdraw all positions
        mb = market_uni.get_market_balance()
        self.last_collect_fee0 += mb.base_uncollected
        self.last_collect_fee1 += mb.quote_uncollected
        market_uni.remove_all_liquidity()
        for key, position in market_gmx.position_list.items():
            market_gmx.decrease_position(
                initialCollateralToken=position.collateralToken,
                initialCollateralDeltaAmount=position.collateralAmount,
                sizeDeltaUsd=position.sizeInUsd,
                isLong=position.isLong
            )
        market_uni.sell(broker.assets[eth].balance)

    def change_position(self, snapshot: Snapshot):
        self.reset_funds()

        pos_h = H * snapshot.prices[eth.name]
        pos_l = L * snapshot.prices[eth.name]
        self.h = pos_h
        self.l = pos_l
        total_cash = self.get_cash_net_value(snapshot.prices)
        self.last_net_value = total_cash

        gmx_usdc, uni_usdc, uni_usdc2eth = total_cash * self.usdc_gmx_pos, total_cash * self.usdc_uni_lp, total_cash * self.eth_uni_lp
        # work
        market_gmx.increase_position(
            initialCollateralToken=usdc,
            initialCollateralDeltaAmount=float(gmx_usdc),
            sizeDeltaUsd=float(gmx_usdc * snapshot.prices[usdc.name]),
            isLong=False
        )

        market_uni.buy(uni_usdc2eth / snapshot.prices[eth.name])  # usdc => eth
        market_uni.add_liquidity(pos_l, pos_h)

        # result monitor
        print("Position changed", snapshot.timestamp)
        pass

    def get_cash_net_value(self, price: pd.Series):
        return Decimal(sum([asset.balance * price[asset.name] for asset in broker.assets.values()]))

    def get_current_net_value(self, price):
        cash = self.get_cash_net_value(price)
        lp_value = 0
        sqrt_price = base_unit_price_to_sqrt_price_x96(
            price[eth.name], market_uni.pool_info.token0.decimal, market_uni.pool_info.token1.decimal, market_uni.pool_info.is_token0_quote
        )
        for pos_key, pos in market_uni.positions.items():
            amount0, amount1 = V3CoreLib.get_token_amounts(market_uni.pool_info, pos_key, sqrt_price, pos.liquidity)
            lp_value += amount0 * price[usdc.name] + amount1 * price[eth.name]
        gmx_status = market_gmx.get_market_balance()

        return cash + gmx_status.net_value + lp_value

    def on_bar(self, snapshot: Snapshot):
        if not self.last_net_value * Decimal("0.96") < self.get_current_net_value(snapshot.prices) < self.last_net_value * Decimal("1.04"):
            self.change_position(snapshot)
        elif not self.l <= snapshot.prices[eth.name] <= self.h:
            self.change_position(snapshot)


if __name__ == "__main__":
    start_date = date(2025, 7, 1)
    end_date = date(2025, 7, 2)
    file_name = f"delta_hedging_gmx_uni"

    market_key_uni = MarketInfo("uni")
    market_key_gmx = MarketInfo("gmx", MarketTypeEnum.gmx_v2)

    usdc = TokenInfo(name="usdc", decimal=6, address="0xaf88d065e77c8cc2239327c5edb3a432268e5831")  # TokenInfo(name='usdc', decimal=6)
    eth = TokenInfo(name="weth", decimal=18, address="0x82af49447d8a07e3bd95bd0d56f35241523fbab1")  # TokenInfo(name='eth', decimal=18)
    uni_pool = UniV3Pool(usdc, eth, 0.05, usdc)
    market_token = TokenInfo(name="market_token", decimal=18, address='0x70d95587d40a2caf56bd97485ab3eec10bee6336')
    gmx_pool = GmxV2Pool(eth, usdc, eth, market_token)
    actuator = Actuator()
    broker = actuator.broker

    market_uni = UniLpMarket(market_key_uni, uni_pool)  # uni_market:UniLpMarket, positions: 1, total liquidity: 376273903830523
    market_uni.data_path = "../data/"
    market_uni.load_data(ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", start_date, end_date)
    broker.add_market(market_uni)  # add market

    market_gmx = GmxV2Market(market_key_gmx, gmx_pool, data_path="../data")
    market_gmx.data_path = "../data/"
    market_gmx.load_data(ChainType.arbitrum, '0x70d95587d40a2caf56bd97485ab3eec10bee6336', start_date, end_date)
    broker.add_market(market_gmx)  # add market

    broker.set_balance(usdc, 1000)  # set balance
    broker.set_balance(eth, 0)  # set balance

    actuator.strategy = DeltaHedgingStrategy()
    actuator.set_price(market_uni.get_price_from_data())

    actuator.run()
    df = actuator.account_status_df
    df["price"] = actuator.token_prices[eth.name]
    df.to_csv(file_name + ".csv")
    with open(file_name + ".pkl", "wb") as outfile1:
        pickle.dump(actuator._action_list, outfile1)
