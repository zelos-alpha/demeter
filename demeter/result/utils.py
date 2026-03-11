from typing import List, Dict, Tuple

from demeter import BaseAction, MarketTypeEnum, ActionTypeEnum, MarketInfo
from ._typing import OptionPosition, LpPosition, Position
from .._typing import MarketDescription
from ..deribit import decode_instrument
from ..deribit._typing import OptionTradeAction
from ..uniswap import AddLiquidityAction, UniDescription


def __new_option_position(action: OptionTradeAction) -> OptionPosition:
    decoded_name = decode_instrument(action.instrument_name)
    return OptionPosition(
        key=action.instrument_name,
        market=action.market,
        start=action.timestamp,
        end=None,
        amount=action.amount,
        token=decoded_name[0],
        expiry_time=decoded_name[1],
        strike_price=int(decoded_name[2]),
        type=decoded_name[3],
    )


def __new_lp_position(
    action: AddLiquidityAction, market: UniDescription, price_range: Tuple[float, float] = None
) -> LpPosition:
    if isinstance(action, AddLiquidityAction):
        price_range = (action.lower_quote_price, action.upper_quote_price)
    amount = action.liquidity if isinstance(action, AddLiquidityAction) else action.remain_liquidity
    return LpPosition(
        key=action.position,
        market=action.market,
        start=action.timestamp,
        end=None,
        amount=amount,
        base_token=market.base_token.name,
        quote_token=market.quote_token.name,
        lower_price=price_range[0],
        upper_price=price_range[1],
    )


def get_positions(action_list: List[BaseAction], markets: List[MarketDescription]) -> Dict[MarketInfo, List]:
    """
    | Extract positions from actions list.
    | If a position has position change(e.g. add or remove part of liquidity), it will be considered as a new position.

    :param action_list: backtest_result.actions.
    :param markets: backtest_result.markets.
    :return: a dict, key is each market, value is positions in this market.
    """
    market_pos: Dict[MarketInfo, List[Position]] = {}
    market_active_pos: Dict[MarketInfo, Dict[any, Position]] = {}
    markets = {x.name: x for x in markets}

    def close_position(market_key, position_key, finish_timestamp):
        market_active_pos[market_key][position_key].end = finish_timestamp
        market_pos[market_key].append(market_active_pos[market_key][position_key])
        del market_active_pos[market_key][position_key]

    for action in action_list:
        if action.market not in market_pos.keys():
            market_pos[action.market] = []
            market_active_pos[action.market] = {}
        if action.market.type == MarketTypeEnum.uniswap_v3:
            if action.action_type == ActionTypeEnum.uni_lp_add_liquidity:
                action_key = action.position
                if action_key in market_active_pos[action.market]:
                    close_position(action.market, action_key, action.timestamp)
                market_active_pos[action.market][action_key] = __new_lp_position(action, markets[action.market.name])
            elif action.action_type == ActionTypeEnum.uni_lp_remove_liquidity:
                action_key = action.position
                old_price_range = (
                    market_active_pos[action.market][action_key].lower_price,
                    market_active_pos[action.market][action_key].upper_price,
                )
                close_position(action.market, action_key, action.timestamp)
                if action.remain_liquidity > 0:
                    market_active_pos[action.market][action_key] = __new_lp_position(
                        action, markets[action.market.name], old_price_range
                    )
        elif action.market.type == MarketTypeEnum.deribit_option:
            if not hasattr(action,"instrument_name"):
                continue
            action_key = action.instrument_name
            if action.action_type == ActionTypeEnum.option_buy:
                if action_key in market_active_pos[action.market]:
                    close_position(action.market, action_key, action.timestamp)
                market_active_pos[action.market][action_key] = __new_option_position(action)
            elif action.action_type == ActionTypeEnum.option_expire:
                close_position(action.market, action_key, action.timestamp)
            elif action.action_type == ActionTypeEnum.option_sell:
                left_amount = market_active_pos[action.market][action_key].amount - action.amount
                close_position(action.market, action_key, action.timestamp)
                if left_amount > 0:
                    market_active_pos[action.market][action_key] = __new_option_position(action)
                    market_active_pos[action.market][action_key].amount = left_amount
        if action.market.type == MarketTypeEnum.aave_v3:
            pass
        if action.market.type == MarketTypeEnum.squeeth:
            pass
    for mkey, mpos in market_active_pos.items():
        if len(mpos) > 0:
            market_pos[mkey].extend(list(mpos.values()))
    return market_pos
