from datetime import date
from decimal import Decimal, ROUND_DOWN
from typing import List, Set

import pandas as pd
from orjson import orjson

from demeter import MarketStatus
from ._typing import GmxDescription, GmxBalance, BuyGlpAction, SellGlpAction, PRICE_PRECISION
from .helper import load_gmx_v1_data, get_price_from_data
from .._typing import TokenInfo, ChainType
from ..broker import Market, MarketInfo
from ..utils import get_formatted_predefined, get_formatted_from_dict, STYLE, console_text


class GmxMarket(Market):
    """
    GMX Market is the simulator for the GMX, here you can simulate some transactions
    """

    def __init__(
        self,
        market_info: MarketInfo,
        tokens: List[TokenInfo] = None,
    ):
        super().__init__(market_info=market_info)
        tokens = tokens if tokens is not None else []
        self.glp_amount = Decimal("0.00")  # glp liquidity
        self.glp_decimal = 18
        self.reward = Decimal("0.00")  # pending fee
        self.mint_burn_fee_basis_points = 25
        self.tax_basis_points = 60
        self._tokens: Set[TokenInfo] = set()
        self.add_token(tokens)

    def add_token(self, token_info: TokenInfo | List[TokenInfo]):
        """
        Add one or an array of token to aave back test.

        :param token_info: tokens to add
        :type token_info: TokenInfo | List[TokenInfo]
        """
        if not isinstance(token_info, list):
            token_info = [token_info]
        for t in token_info:
            self._tokens.add(t)

    def __str__(self):
        from demeter.utils import orjson_default

        return orjson.dumps(self.description, default=orjson_default).decode()

    def description(self):
        return GmxDescription(
            type=type(self).__name__,
            name=self._market_info.name,
        )

    def update(self):
        self._update_fee()

    def _update_fee(self):
        block_reward = Decimal(self.market_status.data.interval) * 60
        supply = Decimal(self.market_status.data.glp)
        reward = block_reward * self.glp_amount / supply
        self.reward += reward

    def buy_glp(self, token: TokenInfo, amount: Decimal | float):
        """
        token: which token to buy glp
        amount: how much token to buy glp
        """
        glp_amount = self._add_liquidity(token, amount)
        self.glp_amount += glp_amount
        self.broker.subtract_from_balance(token, amount)
        return glp_amount

    def sell_glp(self, token: TokenInfo, glp_amount: Decimal | float = 0):
        """
        sell glp to get token
        """
        if not glp_amount:
            glp_amount = self.glp_amount
        token_amount = self._remove_liquidity(token, glp_amount)
        self.glp_amount -= glp_amount
        self.broker.add_to_balance(token, token_amount)
        return token_amount

    def _add_liquidity(self, token: TokenInfo, amount: Decimal | float):
        glp_supply = Decimal(self.market_status.data.glp)
        aum = Decimal(self.market_status.data.aum)
        aum_in_usdg = aum / Decimal(10**12)
        aum_in_usdg = aum_in_usdg.quantize(Decimal("0"), rounding=ROUND_DOWN)
        usdg_amount = self.buy_usdg(token, amount)  # token amount convert to usdg amount
        mint_amount = usdg_amount * glp_supply / aum_in_usdg
        mint_amount = mint_amount.quantize(Decimal("0"), rounding=ROUND_DOWN)
        self._record_action(
            BuyGlpAction(
                market=self.market_info,
                token=token.name,
                token_amount=amount,
                mint_amount=mint_amount,
            )
        )
        return mint_amount / 10**self.glp_decimal

    def _remove_liquidity(self, token: TokenInfo, glp_amount: Decimal | float):
        glp_supply = Decimal(self.market_status.data.glp)
        aum = Decimal(self.market_status.data.aum)
        aum_in_usdg = aum / Decimal(10**12)
        aum_in_usdg = aum_in_usdg.quantize(Decimal("0"), rounding=ROUND_DOWN)
        usdg_amount = glp_amount * 10**self.glp_decimal / glp_supply * aum_in_usdg
        usdg_amount = usdg_amount.quantize(Decimal("0"), rounding=ROUND_DOWN)
        token_out = self.sell_usdg(token, usdg_amount) / 10**token.decimal
        self._record_action(
            SellGlpAction(market=self.market_info, token=token.name, glp_amount=glp_amount, token_out=token_out)
        )
        return token_out

    def buy_usdg(self, token: TokenInfo, token_amount: Decimal | float):
        # function buyUSDG
        price = self.market_status.data[f"{token.name.lower()}_price"]
        usdg_amount = token_amount * 10**token.decimal * price / 10**30
        usdg_amount = usdg_amount.quantize(Decimal("0"), rounding=ROUND_DOWN)
        fee_basic_point = self.get_buy_usdg_fee_point(token, usdg_amount)
        amount_after_fee = self._collect_swap_fee(token, token_amount, fee_basic_point)
        mint_amount = Decimal(amount_after_fee) * 10**token.decimal * price / 10**30
        mint_amount = mint_amount.quantize(Decimal("0"), rounding=ROUND_DOWN)
        return mint_amount

    def sell_usdg(self, token: TokenInfo, usdg_amount: Decimal | float):
        redemption_amount = self.get_redemption_amount(token, usdg_amount)
        fee_basic_point = self.get_sell_usdg_fee_point(token, usdg_amount)
        amount_after_fee = self._collect_swap_fee(token, redemption_amount, fee_basic_point)
        return amount_after_fee

    def get_redemption_amount(self, token: TokenInfo, usdg_amount: Decimal | float):
        price = Decimal(self.market_status.data[f"{token.name.lower()}_price"]) / PRICE_PRECISION
        redemption_amount = usdg_amount / Decimal(price)
        return redemption_amount

    def get_buy_usdg_fee_point(self, token: TokenInfo, usdg_amount: Decimal | float):
        # not consider
        return self.get_fee_basis_points(token, usdg_amount, True)

    def get_sell_usdg_fee_point(self, token: TokenInfo, usdg_amount: Decimal | float):
        # not consider
        return self.get_fee_basis_points(token, usdg_amount, False)

    def get_fee_basis_points(self, token: TokenInfo, usdg_amount: Decimal | float, increase: bool):
        initial_amount = Decimal(self.market_status.data[f"{token.name.lower()}_usdg"])
        next_amount = initial_amount + usdg_amount
        if not increase:
            next_amount = 0 if usdg_amount > initial_amount else initial_amount - usdg_amount
        target_amount = self.get_target_amount(token)
        if target_amount == 0:
            return self.mint_burn_fee_basis_points
        initial_diff = (
            initial_amount - target_amount if initial_amount > target_amount else target_amount - initial_amount
        )
        next_diff = next_amount - target_amount if next_amount > target_amount else target_amount - next_amount
        if next_diff < initial_diff:
            rebate_bps = self.tax_basis_points * initial_diff / target_amount
            return 0 if rebate_bps > self.mint_burn_fee_basis_points else self.mint_burn_fee_basis_points - rebate_bps
        average_diff = (initial_diff + next_diff) / 2
        if average_diff > target_amount:
            average_diff = target_amount
        tax_bps = self.tax_basis_points * average_diff / target_amount
        return self.mint_burn_fee_basis_points + int(tax_bps)

    def get_target_amount(self, token: TokenInfo):
        total_token_weights = 0
        for _token in self._tokens:
            total_token_weights += self.market_status.data[f"{_token.name.lower()}_weight"]
        supply = Decimal(self.market_status.data["usdg"])
        weight = self.market_status.data[f"{token.name.lower()}_weight"]
        return weight * supply / total_token_weights

    def _collect_swap_fee(self, token: TokenInfo, token_amount: Decimal | float, fee_point: Decimal | float):
        fee_amount = token_amount * fee_point / 10000
        after_fee_amount = token_amount - fee_amount
        return after_fee_amount

    def get_market_balance(self) -> GmxBalance:
        # market 有glp + weth/avax fee  change by chain config
        net_value = (
            self.glp_amount * Decimal(self.market_status.data.glp_price)
            + self.reward * Decimal(self.market_status.data["wavax_price"]) / PRICE_PRECISION
        )
        val = GmxBalance(net_value=net_value, reward=self.reward, glp=self.glp_amount)
        return val

    def set_market_status(self, data: MarketStatus, price: pd.Series):
        # 链上数据回测，gmx aave，跟踪
        super().set_market_status(data, price)
        if data.data is None:
            data.data = self.data.loc[data.timestamp]
        self._market_status = data

    def check_market(self):
        super().check_market()

    def _resample(self, freq: str):
        self._data = self.data.resample(freq).first()

    def formatted_str(self):
        value = get_formatted_predefined(f"{self.market_info.name}({type(self).__name__})", STYLE["header3"]) + "\n"
        token_dict = {"tokens": ",".join([t.name for t in self._tokens])}
        value += get_formatted_from_dict(token_dict) + "\n"
        balance = self.get_market_balance()
        value += (
            get_formatted_from_dict(
                {
                    "net_value": console_text.format_value(balance.net_value),
                    "reward": console_text.format_value(balance.reward),
                    "glp": console_text.format_value(balance.glp),
                }
            )
            + "\n"
        )

        return value

    def load_data(self, chain: ChainType, start_date: date, end_date: date):
        self._data = load_gmx_v1_data(chain, start_date, end_date, self.data_path)

    def get_price_from_data(self) -> pd.DataFrame:
        return get_price_from_data(self.data)
