import math
import os
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import Tuple, Dict

import numpy as np
import pandas as pd

from .. import MarketInfo, TokenInfo, DemeterError, MarketStatus, DECIMAL_0
from ..broker import Market
from ._typing import ETH_MAINNET, oSQTH, WETH, Vault, SqueethChain
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
        self._network = ETH_MAINNET
        self._squeeth_uni_pool = squeeth_uni_pool
        self.vault: Dict[int, Vault] = {}

    TWAP_PERIOD = 7  # minutes, which is 420 seconds;
    MIN_DEPOSIT_AMOUNT = Decimal("0.5")  # eth
    # the collateralization ratio (CR) is checked with the numerator and denominator separately
    # a user is safe if - collateral value >= (COLLAT_RATIO_NUMER/COLLAT_RATIO_DENOM)* debt value
    CR_NUMERATOR = Decimal(3)
    CR_DENOMINATOR = Decimal(2)
    REDUCE_DEBT_BOUNTY = Decimal("0.02")
    LIQUIDATION_BOUNTY = Decimal("0.1")
    MIN_COLLATERAL = Decimal("0.5")  # eth

    @property
    def osqth_balance(self):
        """
        Get balance of osqth
        """
        return self.broker.get_token_balance(oSQTH)

    @property
    def squeeth_uni_pool(self) -> UniLpMarket:
        return self._squeeth_uni_pool

    @property
    def network(self) -> SqueethChain:
        """
        Get chain config of this market.
        """
        return self._network

    def load_data(self, start_date: date, end_date: date):
        """
        Load data from .minute.csv, then update index and fill null data.


        """
        self.logger.info(f"start load files from {start_date} to {end_date}...")
        df = pd.DataFrame()
        day = start_date
        if start_date > end_date:
            raise DemeterError(f"start date {start_date} should earlier than end date {end_date}")
        while day <= end_date:
            path = os.path.join(
                self.data_path,
                f"{self._network.chain.name.lower()}-squeeth-controller-{day.strftime('%Y-%m-%d')}.minute.csv",
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
                f"start date {start_date} does not have available data, Consider start from previous day"
            )

        self.data = df
        self.logger.info("data has been prepared")

    def set_market_status(self, market_status: MarketStatus | None, price: pd.Series | None):
        super().set_market_status(market_status, price)
        if market_status.data is None:
            market_status.data = self.data.loc[market_status.timestamp]
        self._market_status = market_status

    def get_price_from_data(self) -> pd.DataFrame:
        """
        Extract token price from relative uniswap pool. All price is based in usd
        """
        if self.data is None:
            raise DemeterError("data has not set")
        price_df = self._data[[WETH.name, oSQTH.name]].copy()
        price_df[oSQTH.name] = price_df[oSQTH.name] * price_df[WETH.name]
        return price_df

    # region short
    def open_deposit_mint(
        self,
        deposit_eth_amount: Decimal,
        osqth_mint_amount: Decimal,
        vault_id: int = 0,
        uni_position: PositionInfo | None = None,
    ) -> Tuple[int, Decimal]:
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
            fee_amount, deposit_amount_with_fee = self.get_fee(
                self.vault[vault_id], osqth_mint_amount, deposit_eth_amount
            )
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
        is_above_water = (
            total_collateral * SqueethMarket.CR_DENOMINATOR >= debt_value_in_eth * SqueethMarket.CR_NUMERATOR
        )

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

    def _withdraw_collateral(self, vault_id: int, amount: Decimal | None = None):
        if vault_id not in self.vault:
            raise DemeterError(f"{vault_id} not exist")
        if amount is None or amount > self.vault[vault_id].collateral_amount:
            amount = self.vault[vault_id].collateral_amount

        self.vault[vault_id].collateral_amount -= amount
        self.broker.add_to_balance(WETH, amount)
        self._check_vault(vault_id, self.get_norm_factor())

    def _withdraw_uni_position(self, vault_id: int, uni_position: PositionInfo):
        if vault_id not in self.vault:
            raise DemeterError(f"{vault_id} not exist")
        if self.vault[vault_id].uni_nft_id != uni_position:
            raise DemeterError(f"{uni_position} is not deposit in vault {vault_id}")
        self.vault[vault_id].uni_nft_id = None
        self.squeeth_uni_pool.transfer_position_in(uni_position)
        self._check_vault(vault_id, self.get_norm_factor())

    def burn_and_withdraw(self, vault_id: int, osqth_burn_amount: Decimal, withdraw_eth_amount: Decimal):
        if vault_id not in self.vault:
            raise DemeterError(f"{vault_id} not exist")
        vault = self.vault[vault_id]
        if osqth_burn_amount > 0:
            if vault.osqth_short_amount >= osqth_burn_amount:
                vault.osqth_short_amount -= osqth_burn_amount
            else:
                vault.osqth_short_amount = 0
        if withdraw_eth_amount > 0:
            self._withdraw_collateral(vault_id, withdraw_eth_amount)

        self._check_vault(vault_id, self.get_norm_factor())

    # def update(self):
    #     pass

    # endregion

    # region long
    def buy_squeeth(self, osqth_amount=None, eth_amount=None) -> Tuple[Decimal, Decimal, Decimal]:
        if osqth_amount is None and eth_amount is not None:
            osqth_amount = eth_amount * self._market_status.data["osqth"]
        fee, eth_amount, osqth_amount = self._squeeth_uni_pool.buy(osqth_amount)
        return fee, eth_amount, osqth_amount

    def sell_squeeth(self, osqth_amount=None, eth_amount=None) -> Tuple[Decimal, Decimal, Decimal]:
        if osqth_amount is None and eth_amount is not None:
            osqth_amount = eth_amount / self._market_status.data["osqth"]
        fee, eth_amount, osqth_amount = self._squeeth_uni_pool.sell(osqth_amount)
        return fee, eth_amount, osqth_amount

    # endregion

    # region liquidate
    def liquidate(self, vault_id: int) -> Decimal:
        if vault_id not in self.vault:
            raise DemeterError(f"{vault_id} not exist")
        norm_factor = self.get_norm_factor()
        vault = self.vault[vault_id]
        is_safe, is_dust = self._get_vault_status(vault_id, norm_factor)
        if not is_safe:
            raise DemeterError("Can not liquidate safe vault")
        # try to save target vault before liquidation by reducing debt
        bounty: Decimal = self._reduce_debt(vault_id, True)

        is_safe, is_dust = self._get_vault_status(vault_id, self.get_norm_factor())
        if is_safe:
            # should transfer bounty to liquidater
            return DECIMAL_0

        vault.collateral_amount += bounty
        debt_amount, collateral_paid = self._liquidate(vault, vault.osqth_short_amount, self.get_norm_factor())
        return debt_amount

    def _liquidate(self, vault: Vault, max_debt_amount, norm_factor) -> Tuple[Decimal, Decimal]:
        liquidate_amount, collateral_to_pay = self._get_liquidation_result(
            max_debt_amount, vault.osqth_short_amount, vault.collateral_amount
        )
        # if the liquidator didn't specify enough wPowerPerp to burn, revert.
        if max_debt_amount < liquidate_amount:
            raise DemeterError("Need full liquidation")

        vault.osqth_short_amount -= liquidate_amount
        vault.collateral_amount -= collateral_to_pay

        is_safe, is_dust = self._get_vault_status(vault.id, norm_factor)
        if is_dust:
            raise DemeterError("Dust vault left")

        return liquidate_amount, collateral_to_pay

    def _get_liquidation_result(
        self, max_osqth_amount, vault_short_amount, vault_collateral_amount
    ) -> Tuple[Decimal, Decimal]:
        final_liquidate_amount, collateral_to_pay = self._get_single_liquidation_amount(
            max_osqth_amount, vault_short_amount / 2
        )

        if vault_collateral_amount > collateral_to_pay:
            if vault_collateral_amount - collateral_to_pay < SqueethMarket.MIN_COLLATERAL:
                # the vault is left with dust after liquidation, allow liquidating full vault
                # calculate the new liquidation amount and collateral again based on the new limit
                final_liquidate_amount, collateral_to_pay = self._get_single_liquidation_amount(
                    max_osqth_amount, vault_short_amount
                )

        # check if final collateral to pay is greater than vault amount.
        # if so the system only pays out the amount the vault has, which may not be profitable
        if collateral_to_pay > vault_collateral_amount:
            final_liquidate_amount = vault_short_amount
            collateral_to_pay = vault_collateral_amount

        return final_liquidate_amount, collateral_to_pay

    def _get_single_liquidation_amount(
        self, max_input_osqth: Decimal, max_liquidatable_osqth: Decimal
    ) -> Tuple[Decimal, Decimal]:
        final_amount = max_liquidatable_osqth if max_input_osqth > max_liquidatable_osqth else max_input_osqth

        osqth_price = self._get_twap_price(oSQTH)
        collateral_to_pay: Decimal = final_amount * osqth_price

        # add 10% bonus for liquidators
        collateral_to_pay += collateral_to_pay * SqueethMarket.LIQUIDATION_BOUNTY

        return final_amount, collateral_to_pay

    def _reduce_debt(self, vault_id: int, pay_bounty: bool) -> Decimal:
        vault = self.vault[vault_id]

        if vault.uni_nft_id is None:
            return DECIMAL_0

        withdrawn_eth_amount, withdrawn_osqth_amount = self._redeem_uni_token(vault.uni_nft_id)
        burn_amount, excess, bounty = self._get_reduce_debt_result_in_vault(
            vault, withdrawn_eth_amount, withdrawn_osqth_amount, pay_bounty
        )
        if excess > 0:
            self.broker.add_to_balance(oSQTH, excess)

        return bounty

    def _get_reduce_debt_result_in_vault(self, vault: Vault, nft_eth_amount, nft_osqth_amount, pay_bounty):
        bounty = 0
        if pay_bounty:
            bounty = self._get_reduce_debt_bounty(nft_eth_amount, nft_osqth_amount)

        burn_amount = nft_osqth_amount
        osqth_excess = 0
        if nft_osqth_amount > vault.osqth_short_amount:
            osqth_excess = nft_osqth_amount - vault.osqth_short_amount
            burn_amount = vault.osqth_short_amount

        vault.osqth_short_amount -= burn_amount
        vault.uni_nft_id = None
        vault.collateral_amount += nft_eth_amount
        vault.collateral_amount -= bounty

        return burn_amount, osqth_excess, bounty

    def _get_reduce_debt_bounty(self, eth_withdrawn: Decimal, osqth_reduced: Decimal) -> Decimal:
        price = self._get_twap_price(oSQTH)
        return (osqth_reduced * price + eth_withdrawn) * Decimal(SqueethMarket.REDUCE_DEBT_BOUNTY)

    def _redeem_uni_token(self, position_info: PositionInfo) -> Tuple[Decimal, Decimal]:
        weth_get, osqth_get = self.squeeth_uni_pool.remove_liquidity(position_info)
        return weth_get, osqth_get

    def reduce_debt(self):
        pass

    # endregion
    def get_norm_factor(self) -> Decimal:
        """Maybe I should calculate this myself, as transactions are too few in a day"""
        return self._market_status.data["norm_factor"]
