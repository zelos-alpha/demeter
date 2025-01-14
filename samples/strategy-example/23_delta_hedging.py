import pickle
from datetime import date, datetime
from decimal import Decimal
from math import sqrt

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from demeter import ChainType, Strategy, TokenInfo, Actuator, MarketInfo, Snapshot, AtTimeTrigger, MarketTypeEnum
from demeter.aave import AaveV3Market
from demeter.uniswap import UniV3Pool, UniLpMarket, V3CoreLib
from demeter.uniswap.helper import base_unit_price_to_sqrt_price_x96

pd.options.display.max_columns = None
pd.set_option("display.width", 5000)

H = Decimal("1.2")  # upper tick range
L = Decimal("0.8")  # lower tick range
AAVE_POLYGON_USDC_ALPHA = Decimal("0.7")  # borrow rate


def optimize_delta_netural(ph, pl, alpha, delta=0.0):
    uni_amount_con = (1 - 1 / ph**0.5) / (1 - pl**0.5)

    liq = 1 / (2 - 1 / sqrt(ph) - sqrt(pl))

    # add constrains
    cons = (
        {"type": "eq", "fun": lambda x: x[0] + x[1] - 1},  # V_U_A + V_U_init = 1
        {"type": "eq", "fun": lambda x: x[2] * uni_amount_con - x[3]},  # uniswap providing constrain
        {"type": "eq", "fun": lambda x: (1 - 1 / ph**0.5) * (x[2] + x[3]) * liq - (x[5] + x[3]) - delta},  # delta netural
        # ineq
        {"type": "ineq", "fun": lambda x: x[1] + x[5] - x[2]},  # amount relation for usdc
        {"type": "ineq", "fun": lambda x: x[4] - x[3]},  # amount relation for eth
        {"type": "ineq", "fun": lambda x: alpha * x[0] - x[5] - x[4]},  # relation for aave
        # all x >= 0
        {"type": "ineq", "fun": lambda x: x[0]},
        {"type": "ineq", "fun": lambda x: x[1]},
        {"type": "ineq", "fun": lambda x: x[2]},
        {"type": "ineq", "fun": lambda x: x[3]},
        {"type": "ineq", "fun": lambda x: x[4]},
        {"type": "ineq", "fun": lambda x: x[5]},
    )

    init_x = np.array((0, 0, 0, 0, 0, 0))
    # # Method Nelder-Mead cannot handle constraints.
    res = minimize(lambda x: -(x[2] + x[3]), init_x, method="SLSQP", constraints=cons)

    return res.fun, res.x


class DeltaHedgingStrategy(Strategy):
    def __init__(self):
        super().__init__()
        optimize_res = optimize_delta_netural(float(H), float(L), float(AAVE_POLYGON_USDC_ALPHA))
        V_U_A, V_U_init, V_U_uni, V_E_uni, V_E_lend, V_U_lend = optimize_res[1]

        self.usdc_aave_supply = Decimal(V_U_A)
        self.usdc_uni_init = Decimal(V_U_init)
        self.eth_uni_lp = Decimal(V_E_uni)
        self.usdc_uni_lp = Decimal(V_U_uni)
        self.eth_aave_borrow = Decimal(V_E_lend)
        self.usdc_aave_borrow = Decimal(V_U_lend)
        print("V_U_A: ", self.usdc_aave_supply)
        print("V_U_init: ", self.usdc_uni_init)
        print("V_U_uni: ", self.usdc_uni_lp)
        print("V_E_uni: ", self.eth_uni_lp)
        print("V_E_lend: ", self.eth_aave_borrow)
        print("V_U_lend: ", self.usdc_aave_borrow)
        self.last_collect_fee0 = 0
        self.last_collect_fee1 = 0

    def initialize(self):
        new_trigger = AtTimeTrigger(time=datetime.combine(start_date, datetime.min.time()), do=self.change_position)
        self.triggers.append(new_trigger)

    def reset_funds(self):
        # withdraw all positions

        mb = market_uni.get_market_balance()

        self.last_collect_fee0 += mb.base_uncollected
        self.last_collect_fee1 += mb.quote_uncollected
        market_uni.remove_all_liquidity()
        for b_key in market_aave.borrow_keys:
            swap_amount = market_aave.get_borrow(b_key).amount - broker.assets[eth].balance
            if swap_amount > 0:
                market_uni.buy(swap_amount * (1 + market_uni.pool_info.fee_rate))
            market_aave.repay(b_key)
        for s_key in market_aave.supply_keys:
            market_aave.withdraw(s_key)
        market_uni.sell(broker.assets[eth].balance)

    def change_position(self, row_data: Snapshot):
        self.reset_funds()

        pos_h = H * row_data.prices[eth.name]
        pos_l = L * row_data.prices[eth.name]
        self.h = pos_h
        self.l = pos_l
        total_cash = self.get_cash_net_value(row_data.prices)

        # work
        aave_supply_value = total_cash * self.usdc_aave_supply
        aave_borrow_value = aave_supply_value * AAVE_POLYGON_USDC_ALPHA

        market_aave.supply(usdc, aave_supply_value)
        market_aave.borrow(eth, aave_borrow_value / row_data.prices[eth.name])

        self.last_net_value = total_cash

        market_uni.sell(self.usdc_aave_borrow * total_cash / row_data.prices[eth.name])  # eth => usdc

        market_uni.add_liquidity(pos_l, pos_h)

        # result monitor
        print("Position changed", row_data.timestamp)
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
        aave_status = market_aave.get_market_balance()

        return cash + aave_status.net_value + lp_value

    def on_bar(self, row_data: Snapshot):
        if not self.last_net_value * Decimal("0.96") < self.get_current_net_value(row_data.prices) < self.last_net_value * Decimal("1.04"):
            self.change_position(row_data)
        elif not self.l <= row_data.prices[eth.name] <= self.h:
            self.change_position(row_data)


if __name__ == "__main__":
    start_date = date(2023, 8, 14)
    end_date = date(2023, 8, 17)
    file_name = f"delta_hedging"

    market_key_uni = MarketInfo("uni")
    market_key_aave = MarketInfo("aave", MarketTypeEnum.aave_v3)

    usdc = TokenInfo(name="usdc", decimal=6, address="0x2791bca1f2de4661ed88a30c99a7a9449aa84174")  # TokenInfo(name='usdc', decimal=6)
    eth = TokenInfo(name="weth", decimal=18, address="0x7ceb23fd6bc0add59e62ac25578270cff1b9f619")  # TokenInfo(name='eth', decimal=18)
    pool = UniV3Pool(usdc, eth, 0.05, usdc)
    actuator = Actuator()
    broker = actuator.broker

    market_uni = UniLpMarket(market_key_uni, pool)  # uni_market:UniLpMarket, positions: 1, total liquidity: 376273903830523
    market_uni.data_path = "../data/"
    market_uni.load_data(ChainType.polygon.name, "0x45dda9cb7c25131df268515131f647d726f50608", start_date, end_date)
    broker.add_market(market_uni)  # add market

    market_aave = AaveV3Market(market_key_aave, "../../tests/aave_risk_parameters/polygon.csv", [usdc, eth])
    market_aave.data_path = "../data/"
    market_aave.load_data(ChainType.polygon, [usdc, eth], start_date, end_date)
    broker.add_market(market_aave)  # add market

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
