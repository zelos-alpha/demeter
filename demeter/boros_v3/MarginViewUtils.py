from MarketInfoAndState import MarketInfoAndState
from PMath import PMath

class MarginViewUtils(MarketInfoAndState):
    def _calc_pm_from_fill(self, market: MarketMem, fill: Fill) -> int:
        return fill.absCost().max(fill.absSize().mulDown(market.k_iThresh))

    def _calcPMFromTick(self, market: MarketMem, absSize: int, tickIndex: int) -> int:
        rate = TickMath.getRateAtTick(tickIndex, market.k_tickStep)
        return self.__calcPMFromRate(absSize, rate, market.k_iThresh)

    def __calcPMFromRate(self, absSize: int, rate: int, k_iThresh: int) -> int:
        absRate = abs(rate)
        return PMath.mul_down(absSize, PMath.max(absRate, k_iThresh))
        