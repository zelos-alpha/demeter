from decimal import Decimal

from .helper import quote_price_to_tick, from_wei
from .liquitidymath import get_amounts, getLiquidity
from .types import PoolBaseInfo, Position, PoolStatus
from .._typing import PositionInfo


class V3CoreLib(object):
    @staticmethod
    def new_position(pool: PoolBaseInfo,
                     token0_amount: Decimal, token1_amount: Decimal,
                     lower_tick: int, upper_tick: int, sqrt_price_x96: int):
        position_liq = getLiquidity(sqrt_price_x96, lower_tick, upper_tick,
                                    token0_amount, token1_amount,
                                    pool.token0.decimal, pool.token1.decimal)
        token0_in_position, token1_in_position = get_amounts(sqrt_price_x96, lower_tick, upper_tick,
                                                             position_liq, pool.token0.decimal, pool.token1.decimal)
        new_position_entity = PositionInfo(lower_tick=lower_tick,
                                           upper_tick=upper_tick)
        return token0_in_position, token1_in_position, int(position_liq), new_position_entity

    @staticmethod
    def close_position(pool: PoolBaseInfo, position_info: PositionInfo, liquidity, sqrt_price_x96):
        return V3CoreLib.get_token_amounts(pool, position_info, sqrt_price_x96, liquidity)

    @staticmethod
    def get_token_amounts(pool: PoolBaseInfo, pos: PositionInfo, sqrt_price_x96, liquidity) -> (Decimal, Decimal):
        amount0, amount1 = get_amounts(sqrt_price_x96,
                                       pos.lower_tick,
                                       pos.upper_tick,
                                       liquidity,
                                       pool.token0.decimal,
                                       pool.token1.decimal)
        return amount0, amount1

    @staticmethod
    def quote_price_pair_to_tick(pool: PoolBaseInfo, lower_quote_price: Decimal, upper_quote_price: Decimal):
        lower_tick = quote_price_to_tick(lower_quote_price, pool.token0.decimal, pool.token1.decimal,
                                         pool.is_token0_base)
        upper_tick = quote_price_to_tick(upper_quote_price, pool.token0.decimal, pool.token1.decimal,
                                         pool.is_token0_base)
        return lower_tick, upper_tick

    @staticmethod
    def update_fee(pool: PoolBaseInfo, pos: PositionInfo, position: Position, state: PoolStatus):
        # in most cases, tick will not cross to next one, which means L will not change.
        if pos.upper_tick > state.current_tick > pos.lower_tick:
            # if the simulating liquidity is above the actual liquidity, we will consider share=1
            if position.liquidity >= state.current_liquidity:
                share = Decimal(1)
            else:
                share = Decimal(position.liquidity) / Decimal(state.current_liquidity)
            position.pending_amount0 += from_wei(state.in_amount0, pool.token0.decimal) * share * pool.fee_rate
            position.pending_amount1 += from_wei(state.in_amount1, pool.token1.decimal) * share * pool.fee_rate
