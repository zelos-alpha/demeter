from _typing import Side, SideLib, LongShort, MatchAux, List, Dict, TickMatchResult, Fill, UserResult, PayFee, UserMem, GetRequest
from TimeInForceLib import TimeInForceLib
from tick_math import TickMath
from TradeLib import TradeLib, FillLib
from ProcessMergeUtils import ProcessMergeUtils
from PayFeeLib import PayFeeLib


class MarketEntry:

    @staticmethod
    def getBestFeeRates():
        return MarketEntry.getBestFeeRates(), MarketEntry.getBestFeeRates()

    @staticmethod
    def _getTakerFeeRate(self):
        return 0  # todo

    @staticmethod
    def _getOtcFeeRate(self):
        return 0  # todo

    @staticmethod
    def getLatestFTime():
        return 0  # todo

    @staticmethod
    def getNextNTicks(side: Side, startTick: int, nTicks: int):
        if nTicks == 0:
            return [], []
        nFound = 0
        found = False
        if startTick == SideLib.tickToGetFirstAvail(side):
            pass

    @staticmethod
    def _getBook() -> Dict:
        pass

    @staticmethod
    def orderAndOtc():
        res = UserResult()  # todo

    @staticmethod
    def _matchOrder():

        bookMatched, partialFill, lastMatchedTick, lastMatchedRate = MarketEntry._bookMatch(k_tickStep, latestFTag, orders)
        if TradeLib.isZero(bookMatched):
            return
        # _updateImpliedRate
        res.bookMatched = bookMatched
        res.payment = ProcessMergeUtils._mergeNewMatchAft()
        if partialFill == 0:
            return
        if (MarketEntry._squashPartial()):
            pass
        partialUser, partialSettle = MarketEntry._initUser()
        res.partialPayFee = PayFeeLib.addPayment(partialSettle, MarketEntry._mergePartialFillAft(partialUser, partialFill))

    @staticmethod
    def _mergePartialFillAft(user: UserMem, fill: Fill) -> int:
        pass

    @staticmethod
    def _squashPartial() -> bool:
        pass  # todo

    @staticmethod
    def _initUser() -> (PayFee, UserMem):
        pass  # todo


    @staticmethod
    def _bookMatch(_tickStep: int, orders: LongShort, _latestFTag: int) -> (int, Fill, int, int):
        matchAux = MatchAux(
            side=SideLib.opposite(orders.side),
            sizes=orders.sizes,
            limitTicks=orders.limitTicks,
            tickStep=_tickStep,
            latestFTag=_latestFTag
        )
        if TimeInForceLib.shouldSkipMatchableOrders(orders.tif):
            MarketEntry._removeMatchableOrders(matchAux)
            return 0, 0, 0, 0
        orderBook = MarketEntry._getBook()
        result = TickMatchResult()
        totalMatched = 0
        partialFill = 0
        lastMatchedTick = 0
        lastMatchedRate = 0
        curOrder = 0
        while True:
            curTick, found = 0, True  # todo
            if not found: break
            curOrder = MarketEntry.__nextMatchableOrder(matchAux.side, curTick, matchAux.limitTicks, curOrder)
            if curOrder == len(matchAux.sizes): break
            matched = 0
            matched, curOrder = MarketEntry._processTickMatches(orderBook, matchAux, curOrder, curTick, result)  # todo result 返回
            lastMatchedTick = curTick
            lastMatchedRate = TickMath.get_rate_at_tick(curTick, matchAux.tickStep)
            totalMatched = totalMatched + TradeLib._from3(matchAux.side, matched, lastMatchedRate)
            if result.partialSize > 0:
                partialFill = FillLib.from3(matchAux.side, result.partialSize, lastMatchedRate)
                break
            if matchAux.sizes[curOrder] == 0:
                break
        MarketEntry.__removeZeroSizes()
        totalMatched = TradeLib.opposite(totalMatched)
        return totalMatched, partialFill, lastMatchedTick, lastMatchedRate

    @staticmethod
    def _processTickMatches(orderBook: Dict, matchAux: MatchAux, startOrder: int, curTick: int, result: TickMatchResult) -> (int, int):
        pass  # todo

    @staticmethod
    def _removeMatchableOrders(matchAux: MatchAux):
        orderBook = MarketEntry._getBook()
        bestTick, found = 0, True
        if not found:
            return
        for i, item in enumerate(matchAux.sizes):
            if SideLib.canMatch(matchAux.side, matchAux.limitTicks[i], bestTick):
                matchAux.sizes[i] = 0
        MarketEntry.__removeZeroSizes()

    @staticmethod
    def __removeZeroSizes():  # todo
        pass

    @staticmethod
    def __nextMatchableOrder(side: Side, curTick: int, limitTicks: List, curOrder: int):
        n = len(limitTicks)
        while curOrder < n and SideLib.canMatch(side, limitTicks[curOrder], curTick):
            curOrder += 1
        return curOrder

    @staticmethod
    def getMarkRate() -> int:
        pass  # todo

    @staticmethod
    def settleAllAndGet() -> (int, int):
        pass  # todo

    @staticmethod
    def settleAndGet(getType: GetRequest):
        res, settle, signedSize, nOrders = _shortcutSettleAndGet()

