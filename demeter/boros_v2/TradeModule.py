from _typing import SingleOrderReq, Tuple, Trade, MarketAcc
from .BookAmmSwapBase import BookAmmSwapBase
from .SideLib import SideLib

class TradeModule(BookAmmSwapBase):

    def place_single_order(self, req: SingleOrderReq, user_root: str) -> Tuple[Trade, int, int]:
        order = req.order
        market_id = order.market_id
        cache = self.get_market_cache(market_id)
        user = MarketAcc(
            root=user_root,
            token_id=cache.token_id.value,
            market_id=market_id.value,
            is_cross=order.cross
        )

        if not order.amm_id.is_zero():
            amm = self.get_amm_id_to_acc(order.amm_id)
            swaps = self.create_swap_math_params(cache, user, amm, order.side, self.get_time_to_mat(cache))
            matched, taker_otc_fee = self.split_and_swap_book_amm(
                swaps,
                order.tif,
                SideLib.to_signed_size(order.size, order.side),
                order.tick,
                req.id_to_strict_cancel
            )
        else:
            pass