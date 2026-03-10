import random
import time
from OrderBookUtils import OrderBookUtils
from ProcessMergeUtils import ProcessMergeUtils
from LibOrderIdSort import LibOrderIdSort, OrderIdEntryLib
from PRNGLib import PRNG
from Order import OrderIdArrayLib


class SweepProcessUtils(OrderBookUtils, ProcessMergeUtils):

    def _sweep_process(self, user: UserMem, part: PartialData, market: MarketMem) -> PayFee:
        longSweptF = self.__sweep_f_one_side(user.longIds, market)
        shortSweptF = self.__sweep_f_one_side(user.shortIds, market)
        return self._process_f(user, part, market, longSweptF, shortSweptF)

    def __sweep_f_one_side(self, ids: list[OrderId], market: MarketMem) -> list[SweptF]:
        if len(ids) == 0:
            return []
        best_pos = len(ids) - 1
        if (not self._book_can_settle_skip_size_check(ids[best_pos])):
            return []
        ids[0], ids[best_pos] = ids[best_pos], ids[0]
        sweptF = []
        sweptF[0] = self._book_get_settle_info(ids[0], market.k_tickStep, FTagLib.ZERO)
        prng = PRNG()
        prng.seed(int(time.time()))
        arr = LibOrderIdSort.make_temp_array(ids)
        partition_pos = self.__find_bound_and_sort_settled(arr, sweptF, market.k_tickStep, prng, market.latestFTag)
        sweptF = sweptF[:partition_pos]
        sweptF.reverse()
        for i in range(0, partition_pos):
            ids[arr[i].index()] = OrderIdLib.ZERO
        OrderIdArrayLib.remove_zeroes_and_update_best_same_side(ids)

    def __find_bound_and_sort_settled(self, entries: list[OrderIdEntry], out: list[SweptF], tick_step: int, prng: PRNG,
                                      latest_f_tag: FTag) -> int:
        low = 1
        high = len(entries)
        while low < high:
            part_pos = OrderIdEntryLib.random_partition(entries, low, high, prng)
            this_id = entries[part_pos].id_()  # OrderId todo
            if self._book_can_settle_skip_size_check(this_id):
                self.__batch_get_settle_info(entries, out, tick_step, prng, low, partPos + 1, latest_f_tag)  # todo

    def __batch_get_settle_info(self, entries: list[OrderIdEntry], out: list[SweptF], tick_step: int, prng: PRNG,
                                low: int, high: int, high_f_tag: FTag):
        if low >= high: return
        if out[low - 1].fTag == high_f_tag:
            for i in range(low, high):
                out[i] = self._book_get_settle_info(entries[i].id_(), tick_step, high_f_tag)
            return
        mid = OrderIdEntryLib.random_partition(entries, low, high, prng)
        out[mid] = self._book_get_settle_info(entries[mid].id_(), tick_step, FTagLib.ZERO)
        self.__batch_get_settle_info(entries, out, tick_step, prng, low, mid, out[mid].fTag)
        self.__batch_get_settle_info(entries, out, tick_step, prng, mid + 1, high, high_f_tag)
