from MarginViewUtils import MarginViewUtils

class PendingOIPureUtils(MarginViewUtils):
    def _updateOIAndPMOnSwept(self, user: UserMem, market: MarketMem, sweptF: SweptF):
        is_purged, fill = sweptF.getFill()
        absSize = fill.absSize()
        if not is_purged:
            market.OI -= absSize
        PMDataMemLib.sub(user.pmData, fill.side(), absSize, self._calc_pm_from_fill(market, fill))  # todo

    def _update_oi_and_pm_on_partial(self, user: UserMem, market: MarketMem, side: Side, absSize: int, pm: int):
        market.OI -= absSize
        PMDataMemLib.sub(user.pmData, side, absSize, pm)
        
    def _updatePMOnAdd(self, user: UserMem, market: MarketMem, orders: LongShort):
        sizeAdded = 0
        pmAdded = 0
        for i in range(0, len(orders.sizes)):
            sizeAdded += orders.sizes[i]
            pmAdded += self._calcPMFromTick(market, orders.sizes[i], orders.limitTicks[i])
        PMDataMemLib.add(user.pmData, orders.side, sizeAdded, pmAdded)

    def _updatePMOnRemove(self, user: UserMem, market: MarketMem, ids: list[OrderId], sizes: list[int]):
        for i in range(0, len(ids)):
            side, tickIndex, _ = OrderIdLib.unpack(ids[i])
            pm = self._calcPMFromTick(market, sizes[i], tickIndex)
            PMDataMemLib.sub(user.pmData, side, sizes[i], pm)
