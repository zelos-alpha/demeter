import math
import os
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import Tuple, Dict

import numpy as np
import pandas as pd

from .. import MarketInfo, TokenInfo, DemeterError, MarketStatus
from ..broker import Market
from ._typing import ETH_MAINNET, oSQTH, WETH, Vault
from ..uniswap import UniLpMarket, PositionInfo
from ..utils import to_decimal
import random


class SqueethMarket(Market):

    def __init__(
            self,
            market_info: MarketInfo,
            squeeth_uni_pool: UniLpMarket,
            data: pd.DataFrame = None,
            data_path: str = "./data",
    ):
        super().__init__(market_info=market_info, data_path=data_path, data=data)
        self.network = ETH_MAINNET
        self._squeeth_uni_pool = squeeth_uni_pool
        self.vault: Dict[int, Vault] = {}

    TWAP_PERIOD = 7  # minutes, which is 420 seconds;
    MIN_DEPOSIT_AMOUNT = Decimal("0.5")  # eth
    # the collateralization ratio (CR) is checked with the numerator and denominator separately
    # a user is safe if - collateral value >= (COLLAT_RATIO_NUMER/COLLAT_RATIO_DENOM)* debt value
    CR_NUMERATOR = Decimal(3)
    CR_DENOMINATOR = Decimal(2)

    @property
    def osqth_amount(self):
        return self.broker.get_token_balance(oSQTH)

    @property
    def squeeth_uni_pool(self) -> UniLpMarket:
        return self._squeeth_uni_pool

    def load_data(self, start_date: date, end_date: date):
        self.logger.info(f"start load files from {start_date} to {end_date}...")
        df = pd.DataFrame()
        day = start_date
        if start_date > end_date:
            raise DemeterError(f"start date {start_date} should earlier than end date {end_date}")
        while day <= end_date:
            path = os.path.join(
                self.data_path,
                f"{self.network.chain.name.lower()}-squeeth-controller-{day.strftime('%Y-%m-%d')}.minute.csv",
            )
            day_df = pd.read_csv(
                path,
                converters={"norm_factor": to_decimal, "eth": to_decimal, "osqth": to_decimal},
            )
            df = pd.concat([df, day_df])
            day = day + timedelta(days=1)
        self.logger.info("load file complete, preparing...")

        df["block_timestamp"] = pd.to_datetime(df["block_timestamp"])
        df.set_index("block_timestamp", inplace=True)
        df = df.ffill()
        if pd.isnull(df.index[0]):
            raise DemeterError(
                f"start date {start_date} does not have available data, Consider start from previous day")

        self.data = df
        self.logger.info("data has been prepared")

    def set_market_status(self, market_status: MarketStatus | None, price: pd.Series | None):
        super().set_market_status(market_status, price)
        self._market_status = market_status

    def get_price_from_data(self) -> pd.DataFrame:
        """
        Extract token pair price from pool data.

        :return: a dataframe includes quote token price, and base token price will be set to 1
        :rtype: DataFrame

        """
        if self.data is None:
            raise DemeterError("data has not set")
        price_df = self._data[["eth", "osqth"]]
        return price_df

    # region short
    def open_deposit_mint(self,
                          deposit_eth_amount: Decimal,
                          osqth_mint_amount: Decimal,
                          vault_id: int = 0,
                          uni_position: PositionInfo | None = None) -> Tuple[int, Decimal]:
        """
        follow controller contract,  function _openDepositMint
        """
        if vault_id is None:
            vault_id = np.random.randint(10000, 100000)
        norm_factor = self.get_norm_factor()
        deposit_amount_with_fee = deposit_eth_amount
        if vault_id == 0:
            new_vault_id = random.randint(10000, 100000)
            vault_id = new_vault_id
            self.vault[new_vault_id] = Vault(new_vault_id)
        fee_amount = Decimal(0)
        if osqth_mint_amount > 0:
            fee_amount, deposit_amount_with_fee = self.get_fee(self.vault[vault_id],
                                                               osqth_mint_amount,
                                                               deposit_eth_amount)
            self.vault[vault_id].osqth_short_amount += osqth_mint_amount
            self.broker.add_to_balance(oSQTH, osqth_mint_amount)

        if deposit_eth_amount > 0:
            self.vault[vault_id].collateral_amount += deposit_amount_with_fee

        if uni_position is not None:
            self._deposit_uni_position(vault_id, uni_position)

        # check vault
        self._check_vault(vault_id, norm_factor)

        if fee_amount > 0:
            self.broker.subtract_from_balance(WETH, fee_amount)

        return vault_id, osqth_mint_amount

    def _check_vault(self, vault_id, norm_factor):
        is_safe, is_dust = self._get_vault_status(vault_id, norm_factor)
        if not is_safe:
            raise DemeterError("Vault collateral rate is not safe")
        if not is_dust:
            raise DemeterError("Vault collateral is below dust")

    def _get_vault_status(self, vault_id, norm_factor) -> Tuple[bool, bool]:
        eth_price = self._get_twap_price(WETH.name)
        if self.vault[vault_id].osqth_short_amount == 0:
            return True, False

        debt_value_in_eth = self.vault[vault_id].osqth_short_amount * norm_factor * eth_price
        total_collateral = self._get_effective_collateral(vault_id, norm_factor, eth_price)

        is_dust = total_collateral < SqueethMarket.MIN_DEPOSIT_AMOUNT
        is_above_water = total_collateral * SqueethMarket.CR_DENOMINATOR >= debt_value_in_eth * SqueethMarket.CR_NUMERATOR

        return is_above_water, is_dust

    def _get_effective_collateral(self, vault_id: int, norm_factor: Decimal, eth_price: Decimal):
        if self.vault[vault_id].uni_nft_id is not None:
            position_info = self.vault[vault_id].uni_nft_id
            nft_weth_amount, nft_squeeth_amount = self.squeeth_uni_pool.get_position_amount(position_info)
            fee_weth = self.squeeth_uni_pool.positions[position_info].pending_amount0
            fee_squeeth = self.squeeth_uni_pool.positions[position_info].pending_amount1
            nft_weth_amount += fee_weth
            nft_squeeth_amount += fee_squeeth
        else:
            nft_weth_amount = nft_squeeth_amount = Decimal(0)

        osqth_index_val_in_eth = nft_squeeth_amount * norm_factor / eth_price
        return nft_weth_amount + osqth_index_val_in_eth + self.vault[vault_id].collateral_amount

    def _get_twap_price(self, token: TokenInfo, now: datetime | None = None):
        if now is None:
            now = self._market_status.timestamp
        start = now - timedelta(minutes=SqueethMarket.TWAP_PERIOD - 1)
        if start < self.data.index[0]:
            start = self.data.index[0].to_pydatetime()
        # remember 1 minute has 1 data point
        prices: pd.Series = self.data[start:now][token.name]
        logged = prices.apply(lambda x: math.log(x, 1.0001))
        logged_sum = logged.sum()
        t_delta = now - start
        power = logged_sum / (1 + t_delta.seconds / 60)
        avg_price = math.pow(1.0001, power)

        return Decimal(avg_price)

    def get_fee(self, vault: Vault, deposit_eth_amount: Decimal, osqth_mint_amount: Decimal) -> Tuple[Decimal, Decimal]:
        # As current fee rate is 0
        return Decimal(0), deposit_eth_amount

    def deposit(self, vault_id, eth_value):
        self.vault[vault_id].collateral_amount += eth_value

    def deposit_uni_position(self, vault_id: int, uni_position_info: PositionInfo):
        self._deposit_uni_position(vault_id, uni_position_info)

    def _deposit_uni_position(self, vault_id: int, uni_position: PositionInfo):
        if uni_position not in self.squeeth_uni_pool.positions:
            raise DemeterError("Position is not in squeeth-eth pool")
        if self.squeeth_uni_pool.positions[uni_position].liquidity <= 0:
            raise DemeterError("Require liquidity in squeeth-eth pool")
        if self.vault[vault_id].uni_nft_id is not None:
            raise DemeterError("This vault already has a NFT collateral")
        self.vault[vault_id].uni_nft_id = uni_position
        self.squeeth_uni_pool.transfer_position_out(uni_position)

    def mint(self):
        pass

    def withdraw(self):
        pass

    def burn(self):
        pass

    def update(self):
        pass

    # endregion

    # region long
    def buy_squeeth(self, eth_amount=None, osqth_amount=None) -> Tuple[Decimal, Decimal, Decimal]:
        if eth_amount is None and osqth_amount is not None:
            eth_amount = osqth_amount * self._market_status["osqth"]
        self.broker.subtract_from_balance(WETH, eth_amount)
        fee, eth_amount, osqth_amount = self._squeeth_uni_pool.buy(eth_amount)
        self.broker.add_to_balance(oSQTH, osqth_amount)
        return fee, eth_amount, osqth_amount

    def sell_squeeth(self, eth_amount=None, osqth_amount=None) -> Tuple[Decimal, Decimal, Decimal]:
        if osqth_amount is None and eth_amount is not None:
            osqth_amount = osqth_amount / self._market_status["osqth"]
        self.broker.subtract_from_balance(oSQTH, osqth_amount)
        fee, eth_amount, osqth_amount = self._squeeth_uni_pool.buy(eth_amount)
        self.broker.add_to_balance(WETH, eth_amount)
        return fee, eth_amount, osqth_amount

    # endregion
    def get_norm_factor(self) -> Decimal:
        """Maybe I should calculate this myself, as transactions are too few in a day"""
        return self._market_status["norm_factor"]

    # -------------------------------------------------------
    # short cut methods
    # -------------------------------------------------------
    def long_open(self):
        # buy
        pass

    def long_close(self):
        # sell
        pass

    def short_open(self):
        # deposit
        # mint
        # sell
        pass

    def short_close(self):
        # buy
        # withdraw
        pass
