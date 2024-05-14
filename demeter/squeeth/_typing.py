from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple

from demeter import TokenInfo, ChainType, BaseAction, UnitDecimal
from demeter.broker import MarketBalance, ActionTypeEnum
from demeter.uniswap import PositionInfo

oSQTH = TokenInfo("oSQTH", 18)
WETH = TokenInfo("weth", 18)
USDC = TokenInfo("usdc", 6)


@dataclass
class SqueethChain:
    """
    Chain config of squeeth

    :param chain: Chan type
    :type chain: ChainType
    :param controller: controller contract address
    :type controller: str
    :param eth_quote_currency_pool: eth-usdc pool in uniswap,
    :type eth_quote_currency_pool: str
    :param eth_quote_currency: quote currency, on ethereum is usdc
    :type eth_quote_currency: TokenInfo
    :param squeeth_uni_pool: eth-squeeth pool in squeeth
    :type squeeth_uni_pool: str

    """
    chain: ChainType
    controller: str
    eth_quote_currency_pool: str
    eth_quote_currency: TokenInfo
    squeeth_uni_pool: str


ETH_MAINNET = SqueethChain(
    chain=ChainType.ethereum,
    controller="0x64187ae08781b09368e6253f9e94951243a493d5",
    eth_quote_currency_pool="0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
    eth_quote_currency=TokenInfo("USDC", 6),
    squeeth_uni_pool="0x82c427adfdf2d245ec51d8046b41c4ee87f0d29c",
)


@dataclass
class Vault:
    """
    Squeeth short position

    :param id: key of vault
    :type id: int
    :param collateral_amount: eth amount in collateral
    :type collateral_amount: Decimal
    :param osqth_short_amount: osqth debt amount
    :type osqth_short_amount: Decimal
    :param uni_nft_id: uniswap lp position in collateral
    :type uni_nft_id: PositionInfo
    """
    id: int
    collateral_amount: Decimal = Decimal(0)
    osqth_short_amount: Decimal = Decimal(0)
    uni_nft_id: PositionInfo | None = None


@dataclass
class SqueethBalance(MarketBalance):
    """
    Balance of squeeth market


    :param collateral_amount: collateral amount in eth, including eth and uniswap lp
    :type collateral_amount: UnitDecimal
    :param collateral_value: collateral value in usd,
    :type collateral_value: UnitDecimal
    :param osqth_long_amount: osqth amount in broker
    :type osqth_long_amount: UnitDecimal
    :param osqth_short_amount: osqth debt
    :type osqth_short_amount: UnitDecimal
    :param osqth_short_in_eth: debt in eth. calculated by index price
    :type osqth_short_in_eth: UnitDecimal
    :param osqth_net_amount: long amount - short amount
    :type osqth_net_amount: UnitDecimal
    :param collateral_ratio: collateral ratio
    :type collateral_ratio: Decimal
    :param vault_count: vault count
    :type vault_count: int
    :param delta: delta
    :type delta: Decimal
    :param gamma: gamma
    :type gamma: Decimal
    """
    collateral_amount: UnitDecimal
    collateral_value: UnitDecimal
    osqth_long_amount: UnitDecimal
    osqth_short_amount: UnitDecimal
    osqth_short_in_eth: UnitDecimal
    osqth_net_amount: UnitDecimal
    collateral_ratio: Decimal
    vault_count: int
    delta: Decimal
    gamma: Decimal


class VaultKey(NamedTuple):
    """
    Vault key

    :param id: vault id
    :type id: int
    """

    # I have to use a Namedtuple as vault key other than int,
    # so it will not be converted into Decimal when used as a function param

    id: int


@dataclass
class VaultAction(BaseAction):
    """
    Base action of short trade

    :param vault_id: vault id
    :type vault_id: int

    """
    vault_id: int


@dataclass
class AddVaultAction(VaultAction):
    """
    Add vault action, throws when you create a new vault.

    :param vault_count: vault count
    :type vault_count: int
    """
    vault_count: int

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_open_vault


@dataclass
class UpdateCollateralAction(VaultAction):
    """
    Update collateral with eth

    :param collateral_amount: eth amount to collate, when withdrawing, amount is negative
    :type collateral_amount: UnitDecimal
    :param collateral_after: collateral amount after deposit/withdraw
    :type collateral_after: UnitDecimal
    :param fee: fee, current it's always zero
    :type fee: UnitDecimal

    """
    collateral_amount: UnitDecimal
    collateral_after: UnitDecimal
    fee: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_update_collateral


@dataclass
class UpdateShortAction(VaultAction):
    """
    Update osqth debt

    :param short_amount: osqth amount to borrow, when repaying, amount is negative
    :type short_amount: UnitDecimal
    :param short_after: debt amount after
    :type short_after: UnitDecimal

    """

    short_amount: UnitDecimal
    short_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_update_short


@dataclass
class DepositLpAction(VaultAction):
    """
    deposit lp action

    :param position: position to deposit
    :type position: PositionInfo
    """
    position: PositionInfo

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_deposit_lp


@dataclass
class WithdrawLpAction(VaultAction):
    """
    withdraw lp action

    :param position: position to withdraw
    :type position: PositionInfo
    """
    position: PositionInfo

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_withdraw_lp


@dataclass
class ReduceDebtAction(VaultAction):
    """
    Reduce debt action,

    :param position: uniswap lp position redeemed
    :type position: PositionInfo
    :param withdrawn_eth_amount: eth amount withdraw from lp
    :type withdrawn_eth_amount: UnitDecimal
    :param withdrawn_osqth_amount: osqth amount withdraw from lp
    :type withdrawn_osqth_amount: UnitDecimal
    :param burn_amount: osqth burned
    :type burn_amount: UnitDecimal
    :param excess: excess
    :type excess: UnitDecimal
    :param bounty: Reduce debt bounty to pay
    :type bounty: UnitDecimal
    :param short_amount_after: debt amount after
    :type short_amount_after: UnitDecimal
    :param collateral_after: collateral amount after
    :type collateral_after: UnitDecimal
    """
    position: PositionInfo
    withdrawn_eth_amount: UnitDecimal
    withdrawn_osqth_amount: UnitDecimal
    burn_amount: UnitDecimal
    excess: UnitDecimal
    bounty: UnitDecimal
    short_amount_after: UnitDecimal
    collateral_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_reduce_debt


@dataclass
class LiquidationAction(VaultAction):
    """
    Liquidation

    :param liquidate_amount: liquidated osqth debt amount
    :type liquidate_amount: UnitDecimal
    :param short_amount_after: debt amount after
    :type short_amount_after: UnitDecimal
    :param collateral_to_pay: eth collateral paid
    :type collateral_to_pay: UnitDecimal
    :param collateral_after: eth collateral after
    :type collateral_after: UnitDecimal
    """
    liquidate_amount: UnitDecimal
    short_amount_after: UnitDecimal
    collateral_to_pay: UnitDecimal
    collateral_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_liquidation
