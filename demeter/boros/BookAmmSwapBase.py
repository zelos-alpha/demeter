from _typing import LongShort, CancelData
from Market import MarketEntry
from MarketHubEntry import MarketHubEntry

class BookAmmSwapBase:

    @staticmethod
    def _splitAndSwapBookAMM():
        pass

    @staticmethod
    def _createSwapMathParams():
        pass

    @staticmethod
    def _swapBookAMM(ammSwapSize: int, orders: LongShort, cancelData: CancelData) -> (int, int):
        pass

    @staticmethod
    def _mintAMM(maxCashIn: int, exactSizeIn: int):
        ammCash, ammSize = BookAmmSwapBase._settleAndGetCashAMM()
        pass

    @staticmethod
    def _settleAndGetCashAMM() -> (int, int):
        cash, size = MarketHubEntry.settleAllAndGet()