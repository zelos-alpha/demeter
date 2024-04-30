from dataclasses import dataclass
from decimal import Decimal

from demeter import TokenInfo, ChainType, MarketStatus
from demeter.uniswap import PositionInfo

oSQTH = TokenInfo("oSQTH", 18)
WETH = TokenInfo("weth", 18)


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



