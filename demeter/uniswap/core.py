from decimal import Decimal

from ._typing import UniV3Pool, Position, UniV3PoolStatus, PositionInfo
from .helper import quote_price_to_tick, from_wei
from .liquitidy_math import get_amounts, get_liquidity


class V3CoreLib(object):
    @staticmethod
    def new_position(
        pool: UniV3Pool,
        token0_amount: Decimal,
        token1_amount: Decimal,
        lower_tick: int,
        upper_tick: int,
        sqrt_price_x96: int,
    ):
        """
        create new position
        :param pool: operation on which pool
        :param token0_amount: token0 amount
        :param token1_amount: token1 amount
        :param lower_tick: lower tick
        :param upper_tick: upper tick
        :param sqrt_price_x96: sqrt(price) * 2^96
        :return: token0 position, token1 position, liquid, position instance
        """
        position_liq = get_liquidity(
            sqrt_price_x96,
            lower_tick,
            upper_tick,
            token0_amount,
            token1_amount,
            pool.token0.decimal,
            pool.token1.decimal,
        )
        token0_in_position, token1_in_position = get_amounts(
            sqrt_price_x96,
            lower_tick,
            upper_tick,
            position_liq,
            pool.token0.decimal,
            pool.token1.decimal,
        )
        new_position_entity = PositionInfo(lower_tick=lower_tick, upper_tick=upper_tick)
        return (
            token0_in_position,
            token1_in_position,
            int(position_liq),
            new_position_entity,
        )

    @staticmethod
    def close_position(pool: UniV3Pool, position_info: PositionInfo, liquidity, sqrt_price_x96):
        """
        close position
        :param pool: operation on which pool
        :param position_info: position info
        :param liquidity: liquidity
        :param sqrt_price_x96: sqrt(price) * 2^96
        :return: token amount
        """
        return V3CoreLib.get_token_amounts(pool, position_info, sqrt_price_x96, liquidity)

    @staticmethod
    def get_token_amounts(pool: UniV3Pool, pos: PositionInfo, sqrt_price_x96, liquidity) -> (Decimal, Decimal):
        """
        get token amount in position
        :param pool: operation on which pool
        :param pos: position info
        :param sqrt_price_x96: sqrt(price) * 2^96
        :param liquidity: liquidity
        :return: token0 amount, token1 amount
        """
        if liquidity == 0:  # performance improve
            return 0, 0
        amount0, amount1 = get_amounts(
            sqrt_price_x96,
            pos.lower_tick,
            pos.upper_tick,
            liquidity,
            pool.token0.decimal,
            pool.token1.decimal,
        )
        return amount0, amount1

    @staticmethod
    def quote_price_pair_to_tick(pool: UniV3Pool, lower_quote_price: Decimal, upper_quote_price: Decimal):
        """
        quote price pair to tick
        :param pool: operation on which pool
        :param lower_quote_price: lower quote price
        :param upper_quote_price: upper quote price
        :return: lower_tick, upper_tick
        """
        lower_tick = quote_price_to_tick(
            lower_quote_price,
            pool.token0.decimal,
            pool.token1.decimal,
            pool.is_token0_base,
        )
        upper_tick = quote_price_to_tick(
            upper_quote_price,
            pool.token0.decimal,
            pool.token1.decimal,
            pool.is_token0_base,
        )
        return lower_tick, upper_tick

    @staticmethod
    def update_fee(pool: UniV3Pool, pos: PositionInfo, position: Position, state: UniV3PoolStatus):
        """
        update fee
        :param pool: operation on which pool
        :param pos: position info
        :param position: position
        :param state: UniV3PoolStatus
        :param last_tick:
        :return: None
        """

        # in most cases, tick will not cross to on_bar one, which means L will not change.
        def calc_amounts():
            share = Decimal(position.liquidity) / Decimal(state.currentLiquidity)
            position.pending_amount0 += from_wei(state.inAmount0, pool.token0.decimal) * share * pool.fee_rate
            position.pending_amount1 += from_wei(state.inAmount1, pool.token1.decimal) * share * pool.fee_rate

        condition_in_position = pos.upper_tick >= state.closeTick >= pos.lower_tick
        if state.last_tick:
            condition_over_position = (state.last_tick > pos.upper_tick and state.closeTick < pos.lower_tick) or (
                    state.closeTick > pos.upper_tick and state.last_tick < pos.lower_tick
            )
            condition_in_to_out_position = pos.upper_tick >= state.last_tick >= pos.lower_tick and (
                    state.closeTick > pos.upper_tick or state.closeTick < pos.lower_tick
            )
        else:
            condition_in_to_out_position = condition_over_position = False

        if condition_in_position or condition_over_position or condition_in_to_out_position:
            calc_amounts()
