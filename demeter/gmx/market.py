import os.path
from demeter import RowData, MarketStatus
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Set, Dict, Tuple, Union
import pandas as pd
from orjson import orjson
from ..broker import Market, MarketInfo
from .typing import GmxDescription, TokenInfo, GmxBalance, BuyGlpAction, SellGlpAction
from .._typing import ChainType, DemeterError
from ..utils import to_decimal


class GmxMarket(Market):
    """
    GMX Market is the simulator for the GMX, here you can simulate some transactions
    """

    def __init__(self,
                 market_info: MarketInfo,
                 data: pd.DataFrame = None,
                 data_path: str = "./data"):
        super().__init__(market_info=market_info, data=data, data_path=data_path)
        self.glp_amount = Decimal("0.00")  # glp liquidity
        self.reward = Decimal("0.00")  # pending fee

    def __str__(self):
        from demeter.utils import orjson_default
        return orjson.dumps(self.description, default=orjson_default).decode()

    def description(self):
        return GmxDescription(
            type=type(self).__name__,
            name=self._market_info.name
        )

    def update(self):
        self._update_fee()

    def _update_fee(self):
        block_reward = Decimal(self.market_status.data.interval) * 60
        supply = Decimal(self.market_status.data.glp)
        reward = block_reward * self.glp_amount / supply
        self.reward += reward

    def buy_glp(self,
                token: TokenInfo,
                amount: Decimal | float):
        """
        token: which token to buy glp
        amount: how much token to buy glp
        """
        glp_amount = self._add_liquidity(token, amount)
        self.glp_amount += glp_amount
        self.broker.subtract_from_balance(token, amount)
        return glp_amount

    def sell_glp(self,
                 token: TokenInfo,
                 glp_amount: Decimal | float = 0):
        """
        sell glp to get token
        """
        if not glp_amount:
            glp_amount = self.glp_amount
        token_amount = self._remove_liquidity(token, glp_amount)
        self.glp_amount -= glp_amount
        self.broker.add_to_balance(token, token_amount)
        return token_amount

    def _add_liquidity(self,
                       token: TokenInfo,
                       amount: Decimal | float):
        glp_supply = Decimal(self.market_status.data.glp)
        aum = Decimal(self.market_status.data.aum)
        aum_in_usdg = aum * Decimal(10 ** -12)
        usdg_amount = self.buy_usdg(token, amount)  # token amount convert to usdg amount
        mint_amount = Decimal(usdg_amount) * glp_supply / aum_in_usdg  # 21907220720283934220233823 real 5%的浮动。
        self._record_action(
            BuyGlpAction(
                market=self.market_info,
                token=token.name,
                token_amount=amount,
                mint_amount=mint_amount,
            )
        )
        return mint_amount

    def _remove_liquidity(self,
                          token: TokenInfo,
                          glp_amount: Decimal | float):
        glp_supply = Decimal(self.market_status.data.glp)
        aum = Decimal(self.market_status.data.aum)
        aum_in_usdg = aum * Decimal(10 ** -12)
        usdg_amount = glp_amount / glp_supply * aum_in_usdg
        token_out = self.sell_usdg(token, usdg_amount)
        self._record_action(
            SellGlpAction(
                market=self.market_info,
                token=token.name,
                glp_amount=glp_amount,
                token_out=token_out
            )
        )
        return token_out

    def buy_usdg(self, token: TokenInfo, token_amount: Decimal | float):
        # function buyUSDG
        price = self.market_status.data[f"{token.name.lower()}_price"]
        usdg_amount = token_amount * price
        fee_basic_point = self.get_buy_usdg_fee_point(token, usdg_amount)
        amount_after_fee = self._collect_swap_fee(token, token_amount, fee_basic_point)
        mint_amount = Decimal(amount_after_fee) * price
        return mint_amount

    def sell_usdg(self, token: TokenInfo, usdg_amount: Decimal | float):
        redemption_amount = self.get_redemption_amount(token, usdg_amount)
        fee_basic_point = self.get_sell_usdg_fee_point(token, usdg_amount)
        amount_after_fee = self._collect_swap_fee(token, redemption_amount, fee_basic_point)
        return amount_after_fee

    def get_redemption_amount(self, token: TokenInfo, usdg_amount: Decimal | float):
        price = self.market_status.data[f"{token.name.lower()}_price"]
        redemption_amount = usdg_amount / Decimal(price)
        return redemption_amount

    def get_buy_usdg_fee_point(self,
                               token: TokenInfo,
                               usdg_amount: Decimal | float):
        # not consider
        return self.get_fee_basis_points()

    def get_sell_usdg_fee_point(self,
                                token: TokenInfo,
                                usdg_amount: Decimal | float):
        # not consider
        return self.get_fee_basis_points()

    def get_fee_basis_points(self):
        return 0

    def _collect_swap_fee(self,
                          token: TokenInfo,
                          token_amount: Decimal | float,
                          fee_point: Decimal | float):
        fee_amount = token_amount * fee_point / 10000
        after_fee_amount = token_amount - fee_amount
        return after_fee_amount

    def load_data(self, chain: ChainType, start_date: date, end_date: date) -> None:
        self.logger.info('start load files from {start_date} to {end_date}...')
        assert start_date <= end_date, f'start date {start_date} should earlier than end date {end_date}'
        df = pd.DataFrame()
        day = start_date
        while day <= end_date:
            data_path = os.path.join(self.data_path, f"{chain.name.lower()}_gmx_{day.strftime('%Y-%m-%d')}.csv")
            day_df = pd.read_csv(
                data_path,
                index_col=0,
                parse_dates=True,
                converters={
                    'glp_price': to_decimal,
                    'weth_price': to_decimal,
                    'wavax_price': to_decimal,
                    'glp': to_decimal,
                    'aum': to_decimal,
                }
            )
            if len(day_df.index) > 0:
                df = pd.concat([df, day_df])
            day = day + timedelta(days=1)
        self.data = df
        self.logger.info("data has been prepared")

    def get_price_from_data(self):
        if self.data is None:
            raise DemeterError("data has not set")
        # keep weth/wavax
        df_price = self.data[['weth_price', 'wavax_price']]
        df_price.rename(columns={'weth_price': 'WETH', 'wavax_price': 'WAVAX'}, inplace=True)
        return df_price

    def get_market_balance(self) -> GmxBalance:
        # market 有glp + weth/avax fee  change by chain config
        net_value = self.glp_amount * Decimal(self.market_status.data.glp_price) + self.reward * Decimal(self.market_status.data['wavax_price'])
        val = GmxBalance(
            net_value=net_value,
            reward=self.reward,
            glp=self.glp_amount
        )
        return val

    def set_market_status(  # 链上数据回测，gmx aave，跟踪
        self,
        data: MarketStatus,
        price: pd.Series,
    ):
        super().set_market_status(data, price)
        if data.data is None:
            data.data = self.data.loc[data.timestamp]
        self._market_status = data

    def check_market(self):
        super().check_market()

    def _resample(self, freq: str):
        self._data = self.data.resample(freq).first()