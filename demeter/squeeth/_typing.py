from dataclasses import dataclass

from demeter import TokenInfo, ChainType

SQTH = TokenInfo("oSQTH", 18)
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
    controller="0x64187ae08781B09368e6253F9E94951243A493D5",
    eth_quote_currency_pool="0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8",
    eth_quote_currency=TokenInfo("USDC", 6),
    squeeth_uni_pool="0x82c427AdFDf2d245Ec51D8046b41c4ee87F0d29C",
)
