from SweepProcessUtils import SweepProcessUtils
from demeter.boros._typing import PartialData
from OrderBookUtils import OrderBookUtils
from .MarketTypes import MarketAcc, MarketMem, UserMem, PayFee, OrderId


class CoreStateUtils(SweepProcessUtils, OrderBookUtils):
    _isOrderRemove = {}

    def _init_user(self, addr: MarketAcc, market: MarketMem) -> (UserMem, PayFee):
        user = UserMem()
        self._init_user_core_data(user, user_addr, False)
        settle = self._sweep_process(user, self._readAndClearPartial(self._acc_state(user)), market)
        user.postSettleSize = user.signedSize
        return user, settle
        # done


    def _init_user_core_data(self, user: UserMem, addr: MarketAcc, allow_shortcut: bool):
        state = self._acc_state(user)
        user.addr = addr
        signedSize, fTag, nLongOrders, nShortOrders = AccountData2Lib.unpack(state.data2)  # todo
        user.signedSize = user.preSettleSize = signedSize
        user.fTag = fTag
        if nLongOrders > 0:
            user.pmData.sumLongSize, user.pmData.sumLongPM = state.sumLongSize, state.sumLongPM
        if nShortOrders > 0:
            user.pmData.sumShortSize, user.pmData.sumShortPM = state.sumShortSize, state.sumShortPM
        if allow_shortcut and not self._hasAtLeastOneSettle(state, nLongOrders, nShortOrders):
            return nLongOrders, nShortOrders, True
        if nLongOrders > 0 or nShortOrders > 0:
            user.longIds, user.shortIds = StoredOrderIdArrLib.read(state.orderIds, nLongOrders, nShortOrders)  # todo
        return nLongOrders, nShortOrders, False

    def _readAndClearPartial(self, state: AccountState) -> PartialData:
        return PartialDataLib.copyFromStorageAndClear(state)  # todo

    def _hasAtLeastOneSettle(self, state: AccountState, nLongOrders: int, nShortOrders: int):
        if nLongOrders > 0:
            lastLong = StoredOrderIdArrLib.readLast(state.orderIds, Side.LONG, nLongOrders)
            if self._book_can_settle_skip_size_check(lastLong):
                return True
        if nShortOrders > 0:
            lastShort = StoredOrderIdArrLib.readLast(state.orderIds, Side.SHORT, nShortOrders)
            if self._book_can_settle_skip_size_check(lastShort):
                return True
        if nLongOrders > 0 or nShortOrders > 0:
            if not PartialDataLib.isZeroStorage(state.partialData):
                return True
        return False

    def _core_remove_aft(self, market: MarketMem, user: UserMem, cancel: CancelData, isForced: bool) -> list[OrderId]:
        if cancel.is_all:
            self._coreRemoveAllAft(market, user, isForced)
        removedSizes = self._bookRemove(cancel.ids, cancel.isStrict, isForced)
        removedIds = cancel.ids
        remove_cnt = len(removedIds)
        if remove_cnt == 0: return removedIds
        for i in range(0, remove_cnt):
            self._isOrderRemove[removedIds[i]] = True
        for iter_ in range(2):
            ids = user.long_ids if iter_ == 0 else user.short_ids
            length = len(ids)
            i = 0
            while i < length and remove_cnt > 0:
                cur_id = ids[i]
                if not self._isOrderRemove[cur_id]:
                    i += 1
                    continue
                remove_cnt -= 1
                self._isOrderRemove[cur_id] = False
                ids[i] = ids[length - 1]
                length -= 1
            LowLevelArrayLib.set_shorter_length(ids, length)
            OrderIdArrayLib.update_best_same_side(ids, 0)
        self._updatePMOnRemove(user, market, removedIds, removedSizes)
        return removedIds

    def _coreRemoveAllAft(self, market: MarketMem, user: UserMem, isForced: bool) -> list[OrderId]:
        if len(user.longIds) > 0:
            removedSizes = self._bookRemove(user.longIds, False, isForced)
            self._updatePMOnRemove(user, market, user.longIds, removedSizes)
        if len(user.shortIds) > 0:
            removedSizes = self._bookRemove(user.shortIds, False, isForced)
            self._updatePMOnRemove(user, market, user.shortIds, removedSizes)
        user.longIds.extend(user.shortIds)  # 合并进去
        removedIds = user.longIds
        user.longIds, user.shortIds = [], []
        return removedIds
