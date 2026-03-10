from PendingOIPureUtils import PendingOIPureUtils
from demeter.boros._typing import SweptF
from PaymentLib import PaymentLib


class ProcessMergeUtils(PendingOIPureUtils):
    def _process_f(self, user: UserMem, part: PartialData, market: MarketMem, longSweptF: list[SweptF],
                   shortSweptF: list[SweptF]) -> PayFee:
        res = PayFee()
        if len(longSweptF) == 0 and len(shortSweptF) == 0 and part.is_zero() and user.f_tag == market.latest_f_tag:
            return PLib.ZERO
        self.__update_oi_and_pm_on_settle_and_partial(user, market, longSweptF, shortSweptF, part)
        user_index = self._to_f_index(user.f_tag)
        orig_index = user_index
        if not part.is_zero():
            res = self.__process_swept_until_stop(user, market, longSweptF, shortSweptF, part.fTag, part.getTrade())
        res = res + self.__process_swept_until_stop(user, market, longSweptF, shortSweptF, market.latestFTag, TradeLib.ZERO)
        return res

    def __process_swept_until_stop(self, user: UserMem, market: MarketMem, longSweptF: list[SweptF], shortSweptF: list[SweptF], stopFTag: FTag, tradeAtStop: Trade) -> PayFee:
        user_index = _to_f_index(user.fTag)
        while True:
            res = PayFee()
            this_tag = stopFTag
            if len(longSweptF) > 0:
                this_tag = this_tag.min(longSweptF[-1].fTag)  # todo
            if len(shortSweptF) > 0:
                this_tag = this_tag.min(shortSweptF[-1].fTag)
            this_index = self._to_f_index(this_tag)
            res = res + PaymentLib.calc_settlement(user.signedSize, user_index, this_index)
            (user.fTag, user_index) = (this_tag, this_index)
            sumTrade = tradeAtStop if this_tag == stopFTag else TradeLib.ZERO
            sumTrade = sumTrade + self.__iterate_swept_same_tag(this_tag, longSweptF) + self.__iterate_swept_same_tag(this_tag, shortSweptF)
            if sumTrade.is_zero():
                continue
            user.signedSize += sumTrade.signedSize()
            upfrontCost = sumTrade.toUpfrontFixedCost(market.k_maturity - user_index.fTime())
            res = res.subPayment(upfrontCost)
            if not user.fTag != stopFTag:  # todo validate
                break
        return res

    def __update_oi_and_pm_on_settle_and_partial(self, user: UserMem, market: MarketMem, longSweptF: list[SweptF], shortSweptF: list[SweptF], part: PartialData):
        for i in range(0, len(longSweptF)):
            self._updateOIAndPMOnSwept(user, market, longSweptF[i])
        for i in range(0, len(shortSweptF)):
            self._updateOIAndPMOnSwept(user, market, shortSweptF[i])
        if not part.is_zero():
            self._update_oi_and_pm_on_partial(user, market, Side.LONG, part.sumLongSize, part.sumLongPM)
            self._update_oi_and_pm_on_partial(user, market, Side.SHORT, part.sumShortSize, part.sumShortPM)

    def __iterate_swept_same_tag(self, tag: FTag, sweptF: list[SweptF]) -> Trade:
        sumTrade = Trade()  # todo
        n = len(sweptF)
        while n > 0 and sweptF[n - 1].fTag == tag:
            n = n - 1
            is_purged, fill = sweptF[n].getFill()  # todo
            if not is_purged:
                sumTrade = sumTrade + fill.toTrade()
        sweptF = sweptF[:n]
        pass  # todo
