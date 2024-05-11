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
    id: int
    collateral_amount: Decimal = Decimal(0)
    osqth_short_amount: Decimal = Decimal(0)
    uni_nft_id: PositionInfo | None = None


@dataclass
class ShortStatus:
    collateral_amount: Decimal
    osqth_short_amount: Decimal
    premium: Decimal
    collateral_ratio: Decimal
    liquidation_price: Decimal


@dataclass
class SqueethBalance(MarketBalance):
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
    I have to use a Namedtuple as vault key other than int,
    so it will not be converted into Decimal when used as a function param
    """

    id: int


@dataclass
class VaultAction(BaseAction):
    vault_id: int


@dataclass
class AddVaultAction(VaultAction):
    vault_count: int

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_open_vault


@dataclass
class UpdateCollateralAction(VaultAction):
    collateral_amount: UnitDecimal
    collateral_after: UnitDecimal
    fee: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_update_collateral


@dataclass
class UpdateShortAction(VaultAction):
    short_amount: UnitDecimal
    short_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_update_short


@dataclass
class DepositLpAction(VaultAction):
    position: PositionInfo

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_deposit_lp


@dataclass
class WithdrawLpAction(VaultAction):
    position: PositionInfo

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_withdraw_lp


@dataclass
class ReduceDebtAction(VaultAction):
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
    liquidate_amount: UnitDecimal
    short_amount_after: UnitDecimal
    collateral_to_pay: UnitDecimal
    collateral_after: UnitDecimal

    def set_type(self):
        self.action_type = ActionTypeEnum.squeeth_liquidation
