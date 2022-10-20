from enum import Enum


class DataSource(Enum):
    BigQuery = 1


class ChainType(Enum):
    Ethereum = 1
    Polygon = 2
    Optimism = 3
    Arbitrum = 4
    Celo = 5


class OnchainTxType(Enum):
    MINT = 0
    SWAP = 2
    BURN = 1
    COLLECT = 3


MarketDataNames = [
    "timestamp",
    "netAmount0",
    "netAmount1",
    "closeTick",
    "openTick",
    "lowestTick",
    "highestTick",
    "inAmount0",
    "inAmount1",
    "currentLiquidity",
]


class MarketData(object):

    def __init__(self):
        self.timestamp = None
        self.netAmount0 = 0
        self.netAmount1 = 0
        self.closeTick = None
        self.openTick = None
        self.lowestTick = None
        self.highestTick = None
        self.inAmount0 = 0
        self.inAmount1 = 0
        self.currentLiquidity = None

    def to_array(self):
        return [
            self.timestamp,
            self.netAmount0,
            self.netAmount1,
            self.closeTick,
            self.openTick,
            self.lowestTick,
            self.highestTick,
            self.inAmount0,
            self.inAmount1,
            self.currentLiquidity
        ]

    def __str__(self):
        return str(self.timestamp)

    def fill_missing_field(self, prev_data) -> bool:
        """
        fill missing field with previous data
        :param prev_data:
        :return: data is available or not
        """
        if prev_data is None:
            prev_data = MarketData()
        self.closeTick = self.closeTick if self.closeTick is not None else prev_data.closeTick
        self.openTick = self.openTick if self.openTick is not None else prev_data.closeTick
        self.lowestTick = self.lowestTick if self.lowestTick is not None else prev_data.closeTick
        self.highestTick = self.highestTick if self.highestTick is not None else prev_data.closeTick
        self.currentLiquidity = self.currentLiquidity if self.currentLiquidity is not None else prev_data.currentLiquidity

        return False if (self.closeTick is None or self.currentLiquidity is None) else True
