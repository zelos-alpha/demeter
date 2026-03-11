from .CoreOrderUtils import CoreOrderUtils
from .CoreStateUtils import CoreStateUtils
from .MarketTypes import MarketAcc, LongShort, CancelData, List, Tuple, OTCTrade, UserMem, OTCResult, UserResult


class Err:
    """Error constants matching Solidity errors."""
    MarketSelfSwap = "MarketSelfSwap"
    MarketZeroSize = "MarketZeroSize"
    MarketDuplicateOTC = "MarketDuplicateOTC"
    InvalidLength = "InvalidLength"
    MarketLastTradedRateTooFar = "MarketLastTradedRateTooFar"


class MarketOrderAndOtc(CoreOrderUtils, CoreStateUtils):
    VERSION = 2

    def order_and_otc(
            self,
            user_addr: MarketAcc,
            orders: LongShort,
            cancels: CancelData,
            otcs: List[OTCTrade],
            crit_hr: int
    ) -> Tuple[UserResult, List[OTCResult]]:
        self._validate_order_and_otc(user_addr, orders, otcs)
        market = self._read_market(check_pause=True, check_maturity=True)

        pass

    def _validate_order_and_otc(self,
        user: MarketAcc,
        orders: LongShort,
        otcs: List[OTCTrade]
    ) -> None:
        if len(orders.sizes) != len(orders.limit_ticks):
            raise ValueError(Err.InvalidLength)

        for size in orders.sizes:
            if size == 0:
                raise ValueError(Err.MarketZeroSize)

            # Validate OTCs
        for i, otc in enumerate(otcs):
            if otc.counter.value() == user.value():
                raise ValueError(Err.MarketSelfSwap)

            for j in range(i + 1, len(otcs)):
                if otcs[j].counter.value() == otc.counter.value():
                    raise ValueError(Err.MarketDuplicateOTC)

