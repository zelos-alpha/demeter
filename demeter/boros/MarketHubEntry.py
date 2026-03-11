from _typing import GetRequest
from Market import MarketEntry

class MarketHubEntry:

    @staticmethod
    def settleAllAndGet(req: GetRequest) -> (int, int):
        MarketHubEntry._settleProcess(req)

    @staticmethod
    def _settleProcess(req: GetRequest) -> (int, int):
        thisVM, thisPayFee, thisSignedSize, _ = MarketEntry.settleAndGet(req)
        pass  # todo