import os
from datetime import date, timedelta, datetime
from decimal import Decimal
from orjson import orjson
from typing import Tuple, Dict

import numpy as np
import pandas as pd

from ._typing import (
    ETH_MAINNET,
    oSQTH,
    WETH,
    Vault,
    SqueethChain,
    SqueethBalance,
    USDC,
    VaultKey,
    AddVaultAction,
    UpdateCollateralAction,
    UpdateShortAction,
    DepositLpAction,
    WithdrawLpAction,
    ReduceDebtAction,
    LiquidationAction,
    SqueethDescription,
)
from .helper import calc_twap_price, vault_to_dataframe
from .. import MarketInfo, TokenInfo, DemeterError, MarketStatus, DECIMAL_0, UnitDecimal
from ..broker import Market
from ..uniswap import UniLpMarket, PositionInfo
from ..utils import (
    to_decimal,
    float_param_formatter,
    get_formatted_predefined,
    STYLE,
    get_formatted_from_dict,
    console_text,
)


class SqueethMarket(Market):
    """
    | Simulation of squeeth market. Support long and short.
    | In long, you can buy or sell squeeth.
    | In short, you can deposit eth or uniswap lp token to mint squeeth, if collateral is low, vault will be liquidated.

    :param market_info: key of this market
    :type market_info: MarketInfo
    :param squeeth_uni_pool: Instance of oSQTH-ETH uniswap pool, Squeeth depends on this pool to swap.
    :type squeeth_uni_pool: UniLpMarket
    :param data: pool data for back test. downloaded by demeter-fetch
    :type data: pd.DataFrame
    :param data_path: path to load pool data
    :type data_path: str
    """

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
        self.vault: Dict[VaultKey, Vault] = {}
        self._max_vault_id = 0

    TWAP_PERIOD = 7  # minutes, which is 420 seconds;
    MIN_DEPOSIT_AMOUNT = Decimal("0.5")  # eth
    # the collateralization ratio (CR) is checked with the numerator and denominator separately
    # a user is safe if - collateral value >= (COLLAT_RATIO_NUMER/COLLAT_RATIO_DENOM)* debt value
    CR_NUMERATOR = Decimal(3)
    CR_DENOMINATOR = Decimal(2)
    REDUCE_DEBT_BOUNTY = Decimal("0.02")
    LIQUIDATION_BOUNTY = Decimal("0.1")
    INDEX_SCALE = Decimal(1e4)

    def __str__(self):
        from demeter.utils import orjson_default

        return orjson.dumps(self.description, default=orjson_default).decode()

    @property
    def description(self):
        """
        Get a brief description of this market
        """
        return SqueethDescription(type(self).__name__, self._market_info.name)

    @property
    def osqth_balance(self) -> Decimal:
        """
        Get balance of osqth in your broker account
        :return: osqth balance
        :rtype: Decimal
        """
        return self.broker.get_token_balance(oSQTH)

    @property
    def squeeth_uni_pool(self) -> UniLpMarket:
        """
        Instance of oSQTH-ETH uniswap pool
        :return: oSQTH-ETH uniswap pool
        :rtype: UniLpMarket
        """
        return self._squeeth_uni_pool

    @property
    def network(self) -> SqueethChain:
        """
        Get chain config of this market. Currently, squeeth is only available on Ethereum
        :return: chain config
        :rtype: SqueethChain
        """
        return self._network

    def get_collat_ratio_and_liq_price(self, vault_key: VaultKey) -> Tuple[Decimal, Decimal]:
        """
        | Get collateral ratio and liquidation price of a vault.
        | forked from useGetCollatRatioAndLiqPrice function in hooks.ts

        :param vault_key: key of vault
        :type vault_key: VaultKey
        :return: collateral ratio and liquidation price
        :rtype: Tuple[Decimal, Decimal]
        """
        nf = self.get_norm_factor()
        collateral_in_eth = self._get_effective_collateral_in_eth(vault_key)
        eth_price = self.get_twap_price(WETH)

        debt_amount_in_index = self.vault[vault_key].osqth_short_amount * nf / SqueethMarket.INDEX_SCALE * eth_price
        if debt_amount_in_index == 0:
            return DECIMAL_0, DECIMAL_0
        r_squeeth = self.vault[vault_key].osqth_short_amount * nf / SqueethMarket.INDEX_SCALE
        return collateral_in_eth / debt_amount_in_index, collateral_in_eth / (r_squeeth * Decimal("1.5"))

    def get_market_balance(self) -> SqueethBalance:
        """
        Get current status, including positions, balances

        :param price: external price, is set to none, will use price in current market status
        :type price: pd.Series | Dict[str, Decimal]
        :return: MarketBalance
        :rtype: SqueethBalance
        """
        current_data = self._market_status.data
        price = {oSQTH.name: current_data[oSQTH.name] * current_data[WETH.name], WETH.name: current_data[WETH.name]}

        long_amount = self.osqth_balance
        short_amount = Decimal(sum([x.osqth_short_amount for x in self.vault.values()]))
        short_value = short_amount * price[oSQTH.name]
        eth_price = self.get_twap_price(WETH)
        collateral_eth = Decimal(
            sum(self._get_effective_collateral_in_eth(VaultKey(v.id)) for v in self.vault.values())
        )
        collateral_value = collateral_eth * price[WETH.name]
        short_in_eth = short_amount * self.get_norm_factor() * eth_price / SqueethMarket.INDEX_SCALE
        return SqueethBalance(
            # squeeth token is hold by broker. so net value is only calculated from short position
            net_value=collateral_value - short_value,
            collateral_amount=collateral_eth,
            osqth_long_amount=long_amount,
            osqth_short_amount=short_amount,
            osqth_net_amount=long_amount - short_amount,
            vault_count=len(self.vault),
            delta=Decimal(2) * price[WETH.name],
            gamma=Decimal(2),
            collateral_value=collateral_value,
            osqth_short_in_eth=short_in_eth,
            collateral_ratio=collateral_eth / short_in_eth if short_in_eth != DECIMAL_0 else 0,
        )

    def get_denormalized_mark(self) -> Decimal:
        """
        Get denormalized mark price,
        :return:
        """
        eth_price = self.get_twap_price(WETH)
        osqth_price = self.get_twap_price(oSQTH)
        return eth_price * osqth_price / self.get_norm_factor() * Decimal(1e14)

    def get_index(self) -> Decimal:
        """
        Get index price
        :return:
        """
        self.get_twap_price(WETH)
        return self.get_twap_price(WETH) ** 2 * Decimal(1e10)

    def load_data(self, start_date: date, end_date: date):
        """
        Load data from .minute.csv, then update index and fill null data.

        :param start_date: start test date
        :type start_date: date
        :param end_date: end test date
        :type end_date: date
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
                converters={"norm_factor": to_decimal, "WETH": to_decimal, "OSQTH": to_decimal},
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

    def set_market_status(self, market_status: MarketStatus, price: pd.Series | None):
        """
        Set current status (normalize factor, price in uniswap pool) to Market

        :param market_status: market data
        :type market_status: MarketStatus
        :param price: price of token at this moment
        :type price: pd.Series
        """

        super().set_market_status(market_status, price)
        if market_status.data is None:
            market_status.data = self.data.loc[market_status.timestamp]
        self._market_status = market_status

    def get_price_from_data(self) -> pd.DataFrame:
        """
        Extract token price from relative uniswap pool. All price is quoted in usd
        """
        if self.data is None:
            raise DemeterError("data has not set")
        price_df = self._data[[WETH.name, oSQTH.name]].copy()
        price_df[oSQTH.name] = price_df[oSQTH.name] * price_df[WETH.name]
        return price_df

    def formatted_str(self):
        """
        Return a brief description of this market in pretty format. Used for print in console.
        """
        value = get_formatted_predefined(f"{self.market_info.name}({type(self).__name__})", STYLE["header3"]) + "\n"
        balance: SqueethBalance = self.get_market_balance()

        value += (
            get_formatted_from_dict(
                {
                    "net_value": console_text.format_value(balance.net_value),
                    "collateral_amount": console_text.format_value(balance.collateral_amount),
                    "collateral_value": console_text.format_value(balance.collateral_value),
                    "osqth_long_amount": console_text.format_value(balance.osqth_long_amount),
                    "osqth_short_amount": console_text.format_value(balance.osqth_short_amount),
                    "osqth_short_in_eth": console_text.format_value(balance.osqth_short_in_eth),
                    "osqth_net_amount": console_text.format_value(balance.osqth_net_amount),
                    "collateral_ratio": console_text.format_value(balance.collateral_ratio),
                }
            )
            + "\n"
        )
        value += get_formatted_predefined("Vaults", STYLE["key"]) + "\n"
        vault_df = vault_to_dataframe(self.vault)
        value += vault_df.to_string() + "\n" if len(vault_df.index) > 0 else "Empty DataFrame\n"

        return value

    # region short

    @float_param_formatter
    def collateral_amount_to_osqth(
        self, collateral_amount: Decimal | float, collateral_rate: Decimal | float = CR_DENOMINATOR
    ) -> Decimal:
        """
        Calculate osqth amount based on eth amount. Forked from useGetShortAmountFromDebt in hook.ts

        :param collateral_amount: eth amount to collateral
        :type collateral_amount: Decimal | float
        :param collateral_rate: collateral rate, default is 2
        :type collateral_rate: Decimal | float
        :return: osqth amount
        :rtype: Decimal
        """
        eth_price = self.get_twap_price(WETH)
        norm_factor = self.get_norm_factor()
        debt_amount = collateral_amount / collateral_rate
        collateral_in_osqth = debt_amount * SqueethMarket.INDEX_SCALE / norm_factor / eth_price
        return collateral_in_osqth

    @float_param_formatter
    def open_deposit_mint_by_collat_rate(
        self,
        deposit_eth_amount: Decimal | float,
        collateral_rate: Decimal | float = CR_DENOMINATOR,
        vault_key: VaultKey | None = None,
        uni_position: PositionInfo | None = None,
    ) -> Tuple[VaultKey, Decimal]:
        """
        open deposit and mint osqth, you can decide mint amount by collateral_rate,

        :param deposit_eth_amount: eth amount to collate
        :type deposit_eth_amount: Decimal
        :param collateral_rate: collateral_rate
        :type collateral_rate: Decimal
        :param vault_key: vault key, if set to None, will create a new vault. or else append collateral to existing vault
        :type vault_key: VaultKey
        :param uni_position: Uniswap liquid position of osqth-weth pool. You can deposit this position to raise collateral rate
        :type uni_position: PositionInfo
        :return: vault created, and osqth mint amount
        :rtype: Tuple[VaultKey, Decimal]:
        """
        osqth_amount = self.collateral_amount_to_osqth(deposit_eth_amount, collateral_rate)
        return self.open_deposit_mint(deposit_eth_amount, osqth_amount, vault_key, uni_position)

    @float_param_formatter
    def open_deposit_mint(
        self,
        deposit_eth_amount: Decimal | float,
        osqth_mint_amount: Decimal | float = DECIMAL_0,
        vault_key: VaultKey | None = None,
        uni_position: PositionInfo | None = None,
    ) -> Tuple[VaultKey, Decimal]:
        """
        open deposit and mint osqth, Forked function _openDepositMint in controller.sol,

        :param deposit_eth_amount: eth amount to collate
        :type deposit_eth_amount: Decimal
        :param osqth_mint_amount: osqth mint amount
        :type osqth_mint_amount: Decimal
        :param vault_key: vault key, if set to None, will create a new vault. or else append collateral to existing vault
        :type vault_key: VaultKey
        :param uni_position: Uniswap liquid position of osqth-weth pool. You can deposit this position to raise collateral rate
        :type uni_position: PositionInfo
        :return: vault created, and osqth mint amount
        :rtype: Tuple[VaultKey, Decimal]:
        """

        norm_factor = self.get_norm_factor()
        deposit_amount_with_fee = deposit_eth_amount
        if vault_key is None:
            self._max_vault_id += 1
            vault_key = VaultKey(self._max_vault_id)
            self.vault[vault_key] = Vault(vault_key.id)
            self._record_action(
                AddVaultAction(
                    market=self.market_info,
                    vault_id=vault_key.id,
                    vault_count=len(self.vault),
                )
            )
        fee_amount = Decimal(0)
        if osqth_mint_amount > DECIMAL_0:
            fee_amount, deposit_amount_with_fee = self._get_fee(
                self.vault[vault_key], deposit_eth_amount, osqth_mint_amount
            )
            self.vault[vault_key].osqth_short_amount += osqth_mint_amount
            self.broker.add_to_balance(oSQTH, osqth_mint_amount)
            self._record_action(
                UpdateShortAction(
                    market=self._market_info,
                    vault_id=vault_key.id,
                    short_amount=UnitDecimal(osqth_mint_amount, oSQTH.name),
                    short_after=UnitDecimal(self.vault[vault_key].osqth_short_amount, oSQTH.name),
                )
            )

        if deposit_eth_amount > 0:
            self.deposit(vault_key, deposit_amount_with_fee)

        if uni_position is not None:
            self._deposit_uni_position(vault_key, uni_position)

        # check vault
        self._check_vault(vault_key, norm_factor)

        if fee_amount > 0:
            self.broker.subtract_from_balance(WETH, fee_amount)

        return vault_key, osqth_mint_amount

    def _check_vault(self, vault_key: VaultKey, norm_factor: Decimal):
        """
        Check vault is safe (collateral is above 150%), or is above minimal collateral amount(0.5eth)

        :param vault_key: Which vault to operate.
        :type vault_key: VaultKey
        :param norm_factor: normalize factor
        :type norm_factor: Decimal
        :return:
        """
        is_safe, is_dust = self.get_vault_status(vault_key, norm_factor)
        if not is_safe:
            raise DemeterError("Vault collateral rate is not safe")
        if is_dust:
            raise DemeterError("Vault collateral is below dust")

    def get_vault_status(
        self, vault_key: VaultKey, norm_factor: Decimal, twap_eth_price: Decimal | None = None
    ) -> Tuple[bool, bool]:
        """
        Check vault is safe (collateral is above 150%), or is above minimal collateral amount(0.5eth)

        :param vault_key: Which vault to operate.
        :type vault_key: VaultKey
        :param norm_factor: normalize factor
        :type norm_factor: Decimal
        :param twap_eth_price: twap eth price.
        :type twap_eth_price: Decimal
        :return: vault status, is safe, is below min-amount
        :rtype: Tuple[bool, bool]
        """
        if twap_eth_price is None:
            twap_eth_price = self.get_twap_price(WETH)
        if self.vault[vault_key].osqth_short_amount == 0:
            return True, False

        debt_value_in_eth = (
            self.vault[vault_key].osqth_short_amount * norm_factor * twap_eth_price / SqueethMarket.INDEX_SCALE
        )
        total_collateral = self._get_effective_collateral_in_eth(vault_key, norm_factor, twap_eth_price)

        is_dust = total_collateral < SqueethMarket.MIN_DEPOSIT_AMOUNT
        is_above_water = (
            total_collateral * SqueethMarket.CR_DENOMINATOR >= debt_value_in_eth * SqueethMarket.CR_NUMERATOR
        )

        return is_above_water, is_dust

    def _get_effective_collateral_in_eth(
        self, vault_key: VaultKey, norm_factor: Decimal | None = None, eth_price: Decimal | None = None
    ) -> Decimal:
        """
        | Get total collateral amount, including: eth deposited, uniswap lp value(eth and osqth)
        | Note: Osqth amount is converted to eth by index price.
        """
        if self.vault[vault_key].uni_nft_id is None:
            return self.vault[vault_key].collateral_amount
        if norm_factor is None:
            norm_factor = self.get_norm_factor()
        if eth_price is None:
            eth_price = self.get_twap_price(WETH)
        position_info = self.vault[vault_key].uni_nft_id
        nft_weth_amount, nft_squeeth_amount = self.squeeth_uni_pool.get_position_amount(position_info)
        fee_weth = self.squeeth_uni_pool.positions[position_info].pending_amount0
        fee_squeeth = self.squeeth_uni_pool.positions[position_info].pending_amount1
        nft_weth_amount += fee_weth
        nft_squeeth_amount += fee_squeeth
        # IMPORTANT:
        # According to _getEffectiveCollateral function in controller.sol,
        # we calculate osqth amount to eth amount by index price,
        # so it's different to net value calculated by uniswap pool(who uses mark price).
        osqth_index_val_in_eth = nft_squeeth_amount / SqueethMarket.INDEX_SCALE * norm_factor * eth_price

        return nft_weth_amount + osqth_index_val_in_eth + self.vault[vault_key].collateral_amount

    def get_twap_price(self, token: TokenInfo, now: datetime | None = None) -> Decimal:
        """
        | Get twap(time weighted average price) price, Just like what uniswap oracle contract did.
        | Depends on price stored in self.data

        :param token: Which token to calculate
        :type token: TokenInfo
        :param now: end time.
        :type now: datetime
        :return: twap price
        :rtype: Decimal
        """
        # for test case
        if self._market_status.timestamp is None:
            return self._market_status.data[token.name]
        if now is None:
            now = self._market_status.timestamp
        start = now - timedelta(minutes=SqueethMarket.TWAP_PERIOD - 1)
        if start < self.data.index[0]:
            start = self.data.index[0].to_pydatetime()
        # remember 1 minute has 1 data point
        prices: pd.Series = self.data[start:now][token.name]
        return calc_twap_price(prices)

    def _get_fee(
        self, vault: Vault, deposit_eth_amount: Decimal, osqth_mint_amount: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """
        Get fee of deposit, currently fee rate is 0 and unlikely to change, so this part is omitted.
        """
        return Decimal(0), deposit_eth_amount

    @float_param_formatter
    def deposit(self, vault_key: VaultKey, eth_value: Decimal | float):
        """
        Deposit eth to current vault

        :param vault_key: Vault key
        :type vault_key: VaultKey
        :param eth_value: Eth amount to collate
        :type eth_value: Decimal
        """
        self.vault[vault_key].collateral_amount += eth_value
        self.broker.subtract_from_balance(WETH, eth_value)
        self._record_action(
            UpdateCollateralAction(
                market=self.market_info,
                vault_id=vault_key.id,
                collateral_amount=UnitDecimal(eth_value, WETH.name),
                collateral_after=UnitDecimal(self.vault[vault_key].collateral_amount, WETH.name),
                fee=UnitDecimal(DECIMAL_0, WETH.name),
            )
        )

    def deposit_uni_position(self, vault_key: VaultKey, uni_position_info: PositionInfo):
        """
        Deposit uniswap lp position to vault. After deposit, position will be transferred to this market.
        and its net value will not be counted in uniswap market.

        :param vault_key: Vault key
        :type vault_key: VaultKey
        :param uni_position_info: Uniswap lp position
        :type uni_position_info: PositionInfo
        """
        self._deposit_uni_position(vault_key, uni_position_info)

    def _deposit_uni_position(self, vault_key: VaultKey, uni_position: PositionInfo):
        if uni_position not in self.squeeth_uni_pool.positions:
            raise DemeterError("Position is not in squeeth-eth pool")
        if self.squeeth_uni_pool.positions[uni_position].liquidity <= 0:
            raise DemeterError("Require liquidity in squeeth-eth pool")
        if self.vault[vault_key].uni_nft_id is not None:
            raise DemeterError("This vault already has a NFT collateral")
        self.vault[vault_key].uni_nft_id = uni_position
        # transfer lp position to current market.
        self.squeeth_uni_pool.transfer_position_out(uni_position)
        self._record_action(
            DepositLpAction(
                market=self.market_info,
                vault_id=vault_key.id,
                position=uni_position,
            )
        )

    def _withdraw_collateral(self, vault_key: VaultKey, amount: Decimal | None = None):
        if vault_key not in self.vault:
            raise DemeterError(f"{vault_key.id} not exist")
        if amount is None or amount > self.vault[vault_key].collateral_amount:
            amount = self.vault[vault_key].collateral_amount

        self.vault[vault_key].collateral_amount -= amount
        self.broker.add_to_balance(WETH, amount)
        self._check_vault(vault_key, self.get_norm_factor())
        self._record_action(
            UpdateCollateralAction(
                market=self.market_info,
                vault_id=vault_key.id,
                collateral_amount=UnitDecimal(DECIMAL_0 - amount, WETH.name),
                collateral_after=UnitDecimal(self.vault[vault_key].collateral_amount, WETH.name),
                fee=UnitDecimal(DECIMAL_0, WETH.name),
            )
        )

    def withdraw_uni_position(self, vault_key: VaultKey, uni_position: PositionInfo):
        """
        Withdraw uniswap lp position.

        :param vault_key: Vault key
        :type vault_key: VaultKey
        :param uni_position_info: Uniswap lp position
        :type uni_position_info: PositionInfo
        """
        if vault_key not in self.vault:
            raise DemeterError(f"{vault_key.id} not exist")
        if self.vault[vault_key].uni_nft_id != uni_position:
            raise DemeterError(f"{uni_position} is not deposit in vault {vault_key.id}")
        self.vault[vault_key].uni_nft_id = None
        self.squeeth_uni_pool.transfer_position_in(uni_position)
        self._check_vault(vault_key, self.get_norm_factor())
        self._record_action(
            WithdrawLpAction(
                market=self.market_info,
                vault_id=vault_key.id,
                position=uni_position,
            )
        )

    @float_param_formatter
    def burn_and_withdraw(
        self, vault_key: VaultKey, osqth_burn_amount: Decimal | float, withdraw_eth_amount: Decimal | float
    ):
        """
        Burn osqth and withdraw. uniswap lp position is not handled here.

        :param vault_key: Vault key
        :type vault_key: VaultKey
        :param osqth_burn_amount: osqth to burn
        :type osqth_burn_amount: Decimal
        :param withdraw_eth_amount: eth to withdraw
        :type withdraw_eth_amount: Decimal
        :return:
        """
        if vault_key not in self.vault:
            raise DemeterError(f"{vault_key.id} not exist")
        vault = self.vault[vault_key]
        if osqth_burn_amount > 0:
            if vault.osqth_short_amount >= osqth_burn_amount:
                removed_amount = osqth_burn_amount
                vault.osqth_short_amount -= osqth_burn_amount
            else:
                removed_amount = vault.osqth_short_amount
                vault.osqth_short_amount = 0
            self.broker.subtract_from_balance(oSQTH, removed_amount)
            self._record_action(
                UpdateShortAction(
                    market=self.market_info,
                    vault_id=vault_key.id,
                    short_amount=UnitDecimal(DECIMAL_0 - removed_amount, oSQTH.name),
                    short_after=UnitDecimal(vault.osqth_short_amount, oSQTH.name),
                )
            )

        if withdraw_eth_amount > 0:
            self._withdraw_collateral(vault_key, withdraw_eth_amount)

        self._check_vault(vault_key, self.get_norm_factor())

    # endregion

    # region long
    @float_param_formatter
    def buy_squeeth(
        self, osqth_amount: float | Decimal | None = None, eth_amount: float | Decimal | None = None
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Buy osqth, you can specify osqth amount to buy. or how many eth to swap to osqth

        :param osqth_amount: osqth amount to buy
        :type osqth_amount: Decimal
        :param eth_amount: eth amount to swap to osqth
        :type eth_amount: Decimal
        :return: swap fee, eth spent, osqth got
        :rtype: Tuple[Decimal, Decimal, Decimal]
        """
        if osqth_amount is None and eth_amount is not None:
            osqth_amount = eth_amount / self._market_status.data["OSQTH"]
        fee, eth_amount, osqth_amount = self._squeeth_uni_pool.buy(osqth_amount)

        return fee, eth_amount, osqth_amount

    @float_param_formatter
    def sell_squeeth(
        self, osqth_amount: float | Decimal | None = None, eth_amount: float | Decimal | None = None
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Sell osqth, you can specify osqth amount to sell. or how many eth to get

        :param osqth_amount: osqth amount to sell
        :type osqth_amount: Decimal
        :param eth_amount: eth amount to got
        :type eth_amount: Decimal
        :return: swap fee,  osqth sold,eth got,
        :rtype: Tuple[Decimal, Decimal, Decimal]
        """
        if osqth_amount is None and eth_amount is not None:
            osqth_amount = eth_amount / self._market_status.data["OSQTH"]
        fee, osqth_amount, eth_amount = self._squeeth_uni_pool.sell(osqth_amount)
        return fee, osqth_amount, eth_amount

    # endregion

    # region liquidate

    def update(self):
        """
        Check and trigger liquidation
        """
        norm_factor = self.get_norm_factor()
        eth_price = self.get_twap_price(WETH)
        for vk, v in self.vault.items():
            is_above_water, is_dust = self.get_vault_status(vk, norm_factor, eth_price)
            if not is_above_water:
                self.liquidate(vk)

    def liquidate(self, vault_key: VaultKey) -> Decimal:
        """
        | liquidate if collateral ratio is blow 150%.
        | liquidate process will first try to redeem unswap lp position, then burn collected osqth, and deposit collected eth.
        | if the vault is still not safe, will liquidate 50% osqth debt. you will have to pay corresponding collateral, and liquidate bounty.
        | If after liquidation, collateral is blow minial amount(0.5eth), will liquidate all debt.

        :param vault_key: vault key
        :type vault_key: VaultKey
        :return: Liquidated debt amount
        :rtype: Decimal
        """
        if vault_key not in self.vault:
            raise DemeterError(f"{vault_key.id} not exist")
        norm_factor = self.get_norm_factor()
        vault = self.vault[vault_key]
        is_safe, is_dust = self.get_vault_status(vault_key, norm_factor)
        if is_safe:
            raise DemeterError("Can not liquidate safe vault")
        # try to save target vault before liquidation by reducing debt
        osqth_burn_amount, osqth_excess, bounty, eth_collected = self._reduce_debt(vault_key, True)

        is_safe, is_dust = self.get_vault_status(vault_key, self.get_norm_factor())
        if is_safe:
            # should transfer bounty to liquidater
            return DECIMAL_0

        vault.collateral_amount += bounty  # add bounty back, will re-calculate liq bounty
        debt_amount, collateral_paid = self._liquidate(vault, vault.osqth_short_amount, self.get_norm_factor())
        return debt_amount

    def _liquidate(self, vault: Vault, max_debt_amount: Decimal, norm_factor: Decimal) -> Tuple[Decimal, Decimal]:
        liquidate_amount, collateral_to_pay = self._get_liquidation_result(
            max_debt_amount, vault.osqth_short_amount, vault.collateral_amount
        )
        # if the liquidator didn't specify enough wPowerPerp to burn, revert.
        if max_debt_amount < liquidate_amount:
            raise DemeterError("Need full liquidation")

        vault.osqth_short_amount -= liquidate_amount
        vault.collateral_amount -= collateral_to_pay

        is_safe, is_dust = self.get_vault_status(VaultKey(vault.id), norm_factor)
        if is_dust:
            raise DemeterError("Dust vault left")
        self._record_action(
            LiquidationAction(
                market=self.market_info,
                vault_id=vault.id,
                liquidate_amount=UnitDecimal(liquidate_amount, oSQTH.name),
                short_amount_after=UnitDecimal(vault.osqth_short_amount, oSQTH.name),
                collateral_to_pay=UnitDecimal(collateral_to_pay, WETH.name),
                collateral_after=UnitDecimal(vault.collateral_amount, WETH.name),
            )
        )
        return liquidate_amount, collateral_to_pay

    def _get_liquidation_result(
        self, max_osqth_amount: Decimal, vault_short_amount: Decimal, vault_collateral_amount: Decimal
    ) -> Tuple[Decimal, Decimal]:
        final_liquidate_amount, collateral_to_pay = self._get_single_liquidation_amount(
            max_osqth_amount, vault_short_amount / 2
        )

        if vault_collateral_amount > collateral_to_pay:
            if vault_collateral_amount - collateral_to_pay < SqueethMarket.MIN_DEPOSIT_AMOUNT:
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

        osqth_price = self.get_twap_price(oSQTH)
        collateral_to_pay: Decimal = final_amount * osqth_price

        # add 10% bonus for liquidators
        collateral_to_pay += collateral_to_pay * SqueethMarket.LIQUIDATION_BOUNTY

        return final_amount, collateral_to_pay

    def _reduce_debt(self, vault_key: VaultKey, pay_bounty: bool) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        """
        Redeem uni lp, and burn those osqth, to save the account
        """
        vault = self.vault[vault_key]

        if vault.uni_nft_id is None:
            return DECIMAL_0, DECIMAL_0, DECIMAL_0, DECIMAL_0
        position = vault.uni_nft_id
        withdrawn_eth_amount, withdrawn_osqth_amount = self._redeem_uni_token(position)
        osqth_burn_amount, osqth_excess, bounty = self._get_reduce_debt_result_in_vault(
            vault, withdrawn_eth_amount, withdrawn_osqth_amount, pay_bounty
        )
        if osqth_excess > 0:
            self.broker.add_to_balance(oSQTH, osqth_excess)

        self._record_action(
            ReduceDebtAction(
                market=self.market_info,
                vault_id=vault_key.id,
                position=position,
                withdrawn_eth_amount=UnitDecimal(withdrawn_eth_amount, WETH.name),
                withdrawn_osqth_amount=UnitDecimal(withdrawn_osqth_amount, oSQTH.name),
                burn_amount=UnitDecimal(osqth_burn_amount, oSQTH.name),
                excess=UnitDecimal(osqth_excess, oSQTH.name),
                bounty=UnitDecimal(bounty, WETH.name),
                short_amount_after=UnitDecimal(vault.osqth_short_amount, oSQTH.name),
                collateral_after=UnitDecimal(vault.collateral_amount, WETH.name),
            )
        )
        return osqth_burn_amount, osqth_excess, bounty, withdrawn_eth_amount

    def _get_reduce_debt_result_in_vault(
        self, vault: Vault, nft_eth_amount: Decimal, nft_osqth_amount: Decimal, pay_bounty: bool
    ):
        bounty = DECIMAL_0
        if pay_bounty:
            bounty = self._get_reduce_debt_bounty(nft_eth_amount, nft_osqth_amount)

        burn_amount = nft_osqth_amount
        osqth_excess = DECIMAL_0
        if nft_osqth_amount > vault.osqth_short_amount:
            osqth_excess = nft_osqth_amount - vault.osqth_short_amount
            burn_amount = vault.osqth_short_amount

        vault.osqth_short_amount -= burn_amount
        vault.uni_nft_id = None
        vault.collateral_amount += nft_eth_amount
        vault.collateral_amount -= bounty

        return burn_amount, osqth_excess, bounty

    def _get_reduce_debt_bounty(self, eth_withdrawn: Decimal, osqth_reduced: Decimal) -> Decimal:
        price = self.get_twap_price(oSQTH)
        return (osqth_reduced * price + eth_withdrawn) * Decimal(SqueethMarket.REDUCE_DEBT_BOUNTY)

    def _redeem_uni_token(self, position_info: PositionInfo) -> Tuple[Decimal, Decimal]:
        self.squeeth_uni_pool.remove_liquidity(position_info, collect=False)
        weth_get, osqth_get = self.squeeth_uni_pool.collect_fee(position_info, collect_to_user=False)
        return weth_get, osqth_get

    # endregion
    def get_norm_factor(self) -> Decimal:
        """
        Get current normalize factor. It is downloaded from event log in squeeth contract.

        :return: normalize factor at current time
        :rtype: Decimal
        """
        # Maybe I should calculate this myself, as transactions are too few in a day
        return self._market_status.data["norm_factor"]

    def _resample(self, freq: str):
        self._data = self.data.resample(freq).first()
