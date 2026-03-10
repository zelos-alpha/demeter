from ._typing import MarketAcc, MarketId, LongShort, CancelData, List, OTCTrade, Tuple, Trade, Side
from .Market import Market

class MarketHub:
    def __init__(self):
        self.markets = {}
        self.user_positions = {}
        self.entered_markets = set()
        self.crit_hr = ONE * 90 // 100

    def _get_market(self, market_id):
        """Get or create a market"""
        if market_id not in self.markets:
            self.markets[market_id] = Market(market_id)
        return self.markets[market_id]

    def enter_market(self, user: MarketAcc, market_id: MarketId) -> None:
        """Enter a market"""
        key = (user.root, market_id.value)
        self.entered_markets.add(key)
        print(f"    [MarketHub] User {user.root[:20]}... entered market {market_id.value}")

    def exit_market(self, user: MarketAcc, market_id: MarketId) -> None:
        """Exit a market"""
        key = (user.root, market_id.value)
        self.entered_markets.discard(key)
        print(f"    [MarketHub] User {user.root[:20]}... exited market {market_id.value}")

    def cash_transfer(self, from_acc: MarketAcc, to_acc: MarketAcc, amount: int) -> None:
        """Transfer cash between accounts"""
        print(f"    [MarketHub] Transferred {amount} cash from {from_acc.root[:20]}... to {to_acc.root[:20]}...")

    def cash_transfer_all(self, from_acc: MarketAcc, to_acc: MarketAcc) -> int:
        """Transfer all cash between accounts"""
        amount = 1000000  # Mock amount
        print(f"    [MarketHub] Transferred all cash ({amount}) from {from_acc.root[:20]}... to {to_acc.root[:20]}...")
        return amount

    def order_and_otc(
            self,
            market_id: MarketId,
            user: MarketAcc,
            orders: LongShort,
            cancel_data: CancelData,
            otcs: List[OTCTrade]
    ) -> Tuple[Trade, int]:
        market = self._get_market(market_id)
        user_res, otc_res = market.order_and_otc(
            user,
            orders,
            cancel_data,
            otcs,
            self.crit_hr
        )