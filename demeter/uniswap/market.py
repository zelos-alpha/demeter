import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict

import pandas as pd

from ._typing import UniV3Pool, TokenInfo, BrokerAsset, Position, UniV3PoolStatus, UniLpBalance, \
    AddLiquidityAction, RemoveLiquidityAction, CollectFeeAction, BuyAction, SellAction, position_dict_to_dataframe, \
    PositionInfo
from .core import V3CoreLib
from .data import fillna, UniLPData
from .helper import tick_to_quote_price, quote_price_to_tick, quote_price_to_sqrt, tick_to_sqrtPriceX96
from .liquitidy_math import get_sqrt_ratio_at_tick
from .._typing import DemeterError, DECIMAL_0, UnitDecimal
from ..broker import MarketBalance, Market, MarketInfo
from ..utils import get_formatted_from_dict, get_formatted_predefined, STYLE, float_param_formatter, to_decimal


class UniLpMarket(Market):
    """
    Broker manage assets in back testing. Including asset, positions. it also provides operations for positions,
    such as add/remove liquidity, swap assets.

    UniLpMarket does not save historical state.

    出于对计算效率的考虑, 回测没有模拟每个add/remove liquidity,
    因此, 无法计算出当前池子价格等信息, 如current_tick, SqrtPriceX96,
    这些信息需要在回测的时候从外部输入(设置到market_status变量).
    :param pool_info: pool information
    :type pool_info: UniV3Pool
    """

    def __init__(self, market_info: MarketInfo, pool_info: UniV3Pool, data: pd.DataFrame = None):
        """
        init UniLpMarket
        :param market_info: uni_market
        :param pool_info: pool info with token0, token1, fee, base token
        :param data: default None, dataframe data
        """
        super().__init__(market_info=market_info, data=data)
        self._pool: UniV3Pool = pool_info
        # init balance
        self._is_token0_base = pool_info.is_token0_base
        # reference for super().assets dict.
        self.base_token, self.quote_token = self._convert_pair(self.pool_info.token0, self.pool_info.token1)
        # status
        self._positions: Dict[PositionInfo, Position] = {}
        self._market_status = UniV3PoolStatus(None, 0, 0, 0, 0, DECIMAL_0)
        # In order to distinguish price in pool and to u, we call former one "pool price"
        self._pool_price_unit = f"{self.base_token.name}/{self.quote_token.name}"
        self.history_recorder = None
        # internal temporary variable
        # self.action_buffer = []

    # region properties

    def __str__(self):
        return f"{self._market_info.name}:{type(self).__name__}, positions: {len(self._positions)}, " \
               f"total liquidity: {sum([p.liquidity for p in self._positions.values()])}"

    @property
    def positions(self) -> Dict[PositionInfo, Position]:
        """
        current positions in broker

        :return: all positions
        :rtype: dict[PositionInfo:Position]
        """
        return self._positions

    @property
    def pool_info(self) -> UniV3Pool:
        """
        Get pool info.

        :return: pool info
        :rtype: UniV3Pool
        """
        return self._pool

    @property
    def token0(self) -> TokenInfo:
        """
        get asset 0 info, including balance

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._pool.token0

    @property
    def token1(self) -> TokenInfo:
        """
        get asset 1 info, including balance

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._pool.token1

    def position(self, position_info: PositionInfo) -> Position:
        """
        get position by position information

        :param position_info: position information
        :type position_info: PositionInfo
        :return: Position entity
        :rtype: Position
        """
        return self._positions[position_info]

    @property
    def market_status(self) -> UniV3PoolStatus:
        return self._market_status

    # endregion

    def set_market_status(self, timestamp: datetime | None, data: UniLPData | UniV3PoolStatus, price: pd.Series | None):
        # update price tick
        local_prev_tick = self._market_status.current_tick
        total_virtual_liq = sum([p.liquidity for p in self._positions.values()])
        if isinstance(data, UniV3PoolStatus):
            self._market_status = data
            self._market_status.current_liquidity += total_virtual_liq
            if not data.last_tick:
                self._market_status.last_tick = local_prev_tick
        else:
            self._market_status = UniV3PoolStatus(timestamp,
                                                  int(data.closeTick),
                                                  data.currentLiquidity + total_virtual_liq,
                                                  data.inAmount0,
                                                  data.inAmount1,
                                                  data.price,
                                                  local_prev_tick)
        self._price_status = price

    def get_price_from_data(self) -> pd.DataFrame:
        if self.data is None:
            raise DemeterError("data has not set")
        price_series: pd.Series = self.data.price
        df = pd.DataFrame(index=price_series.index,
                          data={self.quote_token.name: price_series})
        df[self.base_token.name] = 1
        return df

    def _convert_pair(self, any0, any1):
        """
        convert order of token0/token1 to base_token/quote_token, according to self.is_token0_base.

        Or convert order of base_token/quote_token to token0/token1

        :param any0: token0 or any property of token0, eg. balance...
        :param any1: token1 or any property of token1, eg. balance...
        :return: (base,qoute) or (token0,token1)
        """
        return (any0, any1) if self._is_token0_base else (any1, any0)

    def check_asset(self):
        """

        """
        if not self._pool:
            raise DemeterError("set up pool info first")
        if self.base_token not in self.broker.assets:
            raise DemeterError(f"base token {self.base_token.name} not exist in asset dict")
        if self.quote_token not in self.broker.assets:
            raise DemeterError(f"quote token {self.quote_token.name} not exist in asset dict")

    def update(self):
        """
        re-calculate status
        """
        self.__update_fee()

    def __update_fee(self):
        """
        update fee in all positions according to current status

        fee will be calculated by liquidity
        """
        for position_info, position in self._positions.items():
            V3CoreLib.update_fee(self.pool_info, position_info, position, self.market_status)

    def get_market_balance(self, prices: pd.Series | Dict[str, Decimal] = None) -> MarketBalance:
        """
        get current status, including positions, balances

        :param prices: current price, used for calculate position value and net value, if set to None, will use price in current status
        :type prices: pd.Series | Dict[str, Decimal]

        :return: MarketBalance
        """
        if prices is None:
            pool_price = self._market_status.price
            prices = {
                self.base_token.name: Decimal(1),
                self.quote_token.name: self._market_status.price
            }
        else:
            pool_price = prices[self.quote_token.name] / prices[self.base_token.name]

        sqrt_price = quote_price_to_sqrt(pool_price,
                                         self._pool.token0.decimal,
                                         self._pool.token1.decimal,
                                         self._is_token0_base)
        base_fee_sum = Decimal(0)
        quote_fee_sum = Decimal(0)
        deposit_amount0 = Decimal(0)
        deposit_amount1 = Decimal(0)
        for position_info, position in self._positions.items():
            base_fee, quote_fee = self._convert_pair(position.pending_amount0, position.pending_amount1)
            base_fee_sum += base_fee
            quote_fee_sum += quote_fee
            amount0, amount1 = V3CoreLib.get_token_amounts(self._pool, position_info, sqrt_price, position.liquidity)
            deposit_amount0 += amount0
            deposit_amount1 += amount1

        base_deposit_amount, quote_deposit_amount = self._convert_pair(deposit_amount0, deposit_amount1)
        # net value here is calculated by external price, because we usually want a net value with usd base,
        net_value = (base_fee_sum + base_deposit_amount) * prices[self.base_token.name] + \
                    (quote_fee_sum + quote_deposit_amount) * prices[self.quote_token.name]

        val = UniLpBalance(net_value=net_value,
                           base_uncollected=UnitDecimal(base_fee_sum, self.base_token.name),
                           quote_uncollected=UnitDecimal(quote_fee_sum, self.quote_token.name),
                           base_in_position=UnitDecimal(base_deposit_amount, self.base_token.name),
                           quote_in_position=UnitDecimal(quote_deposit_amount, self.quote_token.name),
                           position_count=len(self._positions))
        return val

    def tick_to_price(self, tick: int) -> Decimal:
        """
        convert tick to price

        :param tick: tick
        :type tick: int
        :return: price
        :rtype: Decimal
        """
        return tick_to_quote_price(int(tick),
                                   self._pool.token0.decimal,
                                   self._pool.token1.decimal,
                                   self._is_token0_base)

    @float_param_formatter
    def price_to_tick(self, price: Decimal | float) -> int:
        """
        convert price to tick

        :param price: price
        :type price:  Decimal | float
        :return: tick
        :rtype: int
        """
        return quote_price_to_tick(price,
                                   self._pool.token0.decimal,
                                   self._pool.token1.decimal,
                                   self._is_token0_base)

    def _add_liquidity_by_tick(self, token0_amount: Decimal,
                               token1_amount: Decimal,
                               lower_tick: int,
                               upper_tick: int,
                               sqrt_price_x96: int = -1):
        lower_tick = int(lower_tick)
        upper_tick = int(upper_tick)
        sqrt_price_x96 = int(sqrt_price_x96)

        if sqrt_price_x96 == -1:
            # self.current_tick must be initialed
            sqrt_price_x96 = get_sqrt_ratio_at_tick(self.market_status.current_tick)
        if lower_tick > upper_tick:
            raise DemeterError("lower tick should be less than upper tick")

        token0_used, token1_used, liquidity, position_info = V3CoreLib.new_position(self._pool,
                                                                                    token0_amount,
                                                                                    token1_amount,
                                                                                    lower_tick,
                                                                                    upper_tick,
                                                                                    sqrt_price_x96)
        if position_info in self._positions:
            self._positions[position_info].liquidity += liquidity
        else:
            self._positions[position_info] = Position(DECIMAL_0, DECIMAL_0, liquidity)
        self.broker.subtract_from_balance(self.token0, token0_used)
        self.broker.subtract_from_balance(self.token1, token1_used)
        return position_info, token0_used, token1_used, liquidity

    def __remove_liquidity(self, position: PositionInfo, liquidity: int = None, sqrt_price_x96: int = -1):
        sqrt_price_x96 = int(sqrt_price_x96) if sqrt_price_x96 != -1 else \
            get_sqrt_ratio_at_tick(self.market_status.current_tick)
        delta_liquidity = liquidity if (liquidity is not None) and liquidity < self.positions[position].liquidity \
            else self.positions[position].liquidity
        token0_get, token1_get = V3CoreLib.close_position(self._pool, position, delta_liquidity, sqrt_price_x96)

        self._positions[position].liquidity = self.positions[position].liquidity - delta_liquidity
        self._positions[position].pending_amount0 += token0_get
        self._positions[position].pending_amount1 += token1_get

        return token0_get, token1_get, delta_liquidity

    def __collect_fee(self, position: Position, max_collect_amount0: Decimal = None,
                      max_collect_amount1: Decimal = None):
        """
        collect fee
        :param position: position
        :param max_collect_amount0: max collect amount0
        :param max_collect_amount1: max collect amount1
        :return:
        """
        token0_fee = max_collect_amount0 if \
            max_collect_amount0 is not None and max_collect_amount0 < position.pending_amount0 else \
            position.pending_amount0
        token1_fee = max_collect_amount1 if \
            max_collect_amount1 is not None and max_collect_amount1 < position.pending_amount1 else \
            position.pending_amount1

        position.pending_amount0 -= token0_fee
        position.pending_amount1 -= token1_fee
        # add un_collect fee to current balance
        self.broker.add_to_balance(self.token0, token0_fee)
        self.broker.add_to_balance(self.token1, token1_fee)
        return token0_fee, token1_fee

    # action for strategy

    @float_param_formatter
    def add_liquidity(self,
                      lower_quote_price: Decimal | float,
                      upper_quote_price: Decimal | float,
                      base_max_amount: Decimal | float = None,
                      quote_max_amount: Decimal | float = None) -> (PositionInfo, Decimal, Decimal, int):
        """

        add liquidity, then get a new position

        :param lower_quote_price: lower price base on quote token.
        :type lower_quote_price: Decimal | float
        :param upper_quote_price: upper price base on quote token.
        :type upper_quote_price: Decimal | float
        :param base_max_amount:  inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type base_max_amount: Decimal | float
        :param quote_max_amount: inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type quote_max_amount: Decimal | float
        :return: added position, base token used, quote token used
        :rtype: (PositionInfo, Decimal, Decimal)
        """
        base_max_amount = self.broker.get_token_balance(self.base_token) if base_max_amount is None else \
            base_max_amount
        quote_max_amount = self.broker.get_token_balance(self.quote_token) if quote_max_amount is None else \
            quote_max_amount

        token0_amt, token1_amt = self._convert_pair(base_max_amount, quote_max_amount)
        lower_tick, upper_tick = V3CoreLib.quote_price_pair_to_tick(self._pool, lower_quote_price,
                                                                    upper_quote_price)
        lower_tick, upper_tick = self._convert_pair(upper_tick, lower_tick)
        (created_position, token0_used, token1_used, liquidity) = self._add_liquidity_by_tick(token0_amt,
                                                                                              token1_amt,
                                                                                              lower_tick,
                                                                                              upper_tick)
        base_used, quote_used = self._convert_pair(token0_used, token1_used)
        self.record_action(AddLiquidityAction(
            market=self.market_info,
            base_balance_after=self.broker.get_token_balance_with_unit(self.base_token),
            quote_balance_after=self.broker.get_token_balance_with_unit(self.quote_token),
            base_amount_max=UnitDecimal(base_max_amount, self.base_token.name),
            quote_amount_max=UnitDecimal(quote_max_amount, self.quote_token.name),
            lower_quote_price=UnitDecimal(lower_quote_price, self._pool_price_unit),
            upper_quote_price=UnitDecimal(upper_quote_price, self._pool_price_unit),
            base_amount_actual=UnitDecimal(base_used, self.base_token.name),
            quote_amount_actual=UnitDecimal(quote_used, self.quote_token.name),
            position=created_position,
            liquidity=int(liquidity)))
        return created_position, base_used, quote_used, liquidity

    def add_liquidity_by_tick(self,
                              lower_tick: int,
                              upper_tick: int,
                              base_max_amount: Decimal | float = None,
                              quote_max_amount: Decimal | float = None,
                              sqrt_price_x96: int = -1,
                              tick: int = -1):
        """

        add liquidity, you need to set tick instead of price.

        :param lower_tick: lower tick
        :type lower_tick: int
        :param upper_tick: upper tick
        :type upper_tick: int
        :param base_max_amount:  inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type base_max_amount: Decimal | float
        :param quote_max_amount: inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type quote_max_amount: Decimal | float
        :param tick: tick price.  if set to none, it will be calculated from current price.
        :type tick: int
        :param sqrt_price_x96: precise price.  if set to none, it will be calculated from current price. this param will override tick
        :type sqrt_price_x96: int
        :return: added position, base token used, quote token used
        :rtype: (PositionInfo, Decimal, Decimal)
        """
        if lower_tick > upper_tick:
            lower_tick, upper_tick = upper_tick, lower_tick

        if sqrt_price_x96 == -1 and tick != -1:
            sqrt_price_x96 = tick_to_sqrtPriceX96(tick)

        base_max_amount = self.broker.get_token_balance(self.base_token) if base_max_amount is None else \
            base_max_amount
        quote_max_amount = self.broker.get_token_balance(self.quote_token) if quote_max_amount is None else \
            quote_max_amount

        token0_amt, token1_amt = self._convert_pair(base_max_amount, quote_max_amount)
        (created_position, token0_used, token1_used, liquidity) = self._add_liquidity_by_tick(token0_amt,
                                                                                              token1_amt,
                                                                                              lower_tick,
                                                                                              upper_tick,
                                                                                              sqrt_price_x96)
        base_used, quote_used = self._convert_pair(token0_used, token1_used)
        self.record_action(AddLiquidityAction(
            market=self.market_info,
            base_balance_after=self.broker.get_token_balance_with_unit(self.base_token),
            quote_balance_after=self.broker.get_token_balance_with_unit(self.quote_token),
            base_amount_max=UnitDecimal(base_max_amount, self.base_token.name),
            quote_amount_max=UnitDecimal(quote_max_amount, self.quote_token.name),
            lower_quote_price=UnitDecimal(self.tick_to_price(lower_tick), self._pool_price_unit),
            upper_quote_price=UnitDecimal(self.tick_to_price(upper_tick), self._pool_price_unit),
            base_amount_actual=UnitDecimal(base_used, self.base_token.name),
            quote_amount_actual=UnitDecimal(quote_used, self.quote_token.name),
            position=created_position,
            liquidity=int(liquidity)))
        return created_position, base_used, quote_used, liquidity

    @float_param_formatter
    def remove_liquidity(self, position: PositionInfo, liquidity: int = None, collect: bool = True,
                         sqrt_price_x96: int = -1, remove_dry_pool: bool = True) -> (Decimal, Decimal):
        """
        remove liquidity from pool, liquidity will be reduced to 0,
        instead of send tokens to broker, tokens will be transferred to fee property in position.
        position will be not deleted, until fees and tokens are collected.

        :param position: position to remove.
        :type position: PositionInfo
        :param liquidity: liquidity amount to remove, if set to None, all the liquidity will be removed
        :type liquidity: int
        :param collect: collect or not, if collect, will call collect function. and tokens will be sent to broker. if not token will be kept in fee property of postion
        :type collect: bool
        :param sqrt_price_x96: precise price.  if set to none, it will be calculated from current price.
        :type sqrt_price_x96: int
        :param remove_dry_pool: remove pool which liquidity==0, effect when collect==True
        :type remove_dry_pool: bool
        :return: (base_got,quote_get), base and quote token amounts collected from position
        :rtype:  (Decimal,Decimal)
        """
        if liquidity and liquidity < 0:
            raise DemeterError("liquidity should large than 0")
        token0_get, token1_get, delta_liquidity = self.__remove_liquidity(position, liquidity, sqrt_price_x96)

        base_get, quote_get = self._convert_pair(token0_get, token1_get)
        self.record_action(
            RemoveLiquidityAction(market=self.market_info,
                                  base_balance_after=self.broker.get_token_balance_with_unit(self.base_token),
                                  quote_balance_after=self.broker.get_token_balance_with_unit(self.quote_token),
                                  position=position,
                                  base_amount=UnitDecimal(base_get, self.base_token.name),
                                  quote_amount=UnitDecimal(quote_get, self.quote_token.name),
                                  removed_liquidity=delta_liquidity,
                                  remain_liquidity=self.positions[position].liquidity
                                  ))
        if collect:
            return self.collect_fee(position, remove_dry_pool=remove_dry_pool)
        else:
            return base_get, quote_get

    @float_param_formatter
    def collect_fee(self,
                    position: PositionInfo,
                    max_collect_amount0: Decimal = None,
                    max_collect_amount1: Decimal = None,
                    remove_dry_pool: bool = True) -> (Decimal, Decimal):
        """
        collect fee and token from positions,
        if the amount and liquidity is zero, this position will be deleted.

        :param position: position to collect
        :type position: PositionInfo
        :param max_collect_amount0: max token0 amount to collect, eg: 1.2345 usdc, if set to None, all the amount will be collect
        :type max_collect_amount0: Decimal
        :param max_collect_amount1: max token0 amount to collect, if set to None, all the amount will be collect
        :type max_collect_amount1: Decimal
        :param remove_dry_pool: remove pool which liquidity==0, effect when collect==True
        :type remove_dry_pool: bool
        :return: (base_got,quote_get), base and quote token amounts collected from position
        :rtype:  (Decimal,Decimal)
        """
        if (max_collect_amount0 and max_collect_amount0 < 0) or \
                (max_collect_amount1 and max_collect_amount1 < 0):
            raise DemeterError("collect amount should large than 0")
        token0_get, token1_get = self.__collect_fee(self._positions[position], max_collect_amount0, max_collect_amount1)

        base_get, quote_get = self._convert_pair(token0_get, token1_get)
        if self._positions[position]:
            self.record_action(CollectFeeAction(
                market=self.market_info,
                base_balance_after=self.broker.get_token_balance_with_unit(self.base_token),
                quote_balance_after=self.broker.get_token_balance_with_unit(self.quote_token),
                position=position,
                base_amount=UnitDecimal(base_get, self.base_token.name),
                quote_amount=UnitDecimal(quote_get, self.quote_token.name)
            ))
        if self._positions[position].pending_amount0 == Decimal(0) \
                and self._positions[position].pending_amount1 == Decimal(0) \
                and self._positions[position].liquidity == 0 \
                and remove_dry_pool:
            del self.positions[position]
        return base_get, quote_get

    @float_param_formatter
    def buy(self, amount: Decimal | float, price: Decimal | float = None) -> (Decimal, Decimal, Decimal):
        """
        buy token, swap from base token to quote token.

        :param amount: amount to buy(in quote token)
        :type amount:  Decimal | float
        :param price: price
        :type price: Decimal | float
        :return: fee, base token amount spend, quote token amount got
        :rtype: (Decimal, Decimal, Decimal)
        """
        price = price if price else self.market_status.price
        from_amount = price * amount
        from_amount_with_fee = from_amount * (1 + self._pool.fee_rate)
        fee = from_amount_with_fee - from_amount
        from_token, to_token = self._convert_pair(self.token0, self.token1)
        self.broker.subtract_from_balance(from_token, from_amount_with_fee)
        self.broker.add_to_balance(to_token, amount)
        base_amount, quote_amount = self._convert_pair(from_amount, amount)
        self.record_action(BuyAction(
            market=self.market_info,
            base_balance_after=self.broker.get_token_balance_with_unit(self.base_token),
            quote_balance_after=self.broker.get_token_balance_with_unit(self.quote_token),
            amount=UnitDecimal(amount, self.quote_token.name),
            price=UnitDecimal(price, self._pool_price_unit),
            fee=UnitDecimal(fee, self.base_token.name),
            base_change=UnitDecimal(base_amount, self.base_token.name),
            quote_change=UnitDecimal(quote_amount, self.quote_token.name)))
        return fee, base_amount, quote_amount

    @float_param_formatter
    def sell(self, amount: Decimal | float, price: Decimal | float = None) -> (Decimal, Decimal, Decimal):
        """
        sell token, swap from quote token to base token.

        :param amount: amount to sell(in quote token)
        :type amount:  Decimal | float
        :param price: price
        :type price: Decimal | float
        :return: fee, base token amount got, quote token amount spend
        :rtype: (Decimal, Decimal, Decimal)
        """
        price = price if price else self.market_status.price
        from_amount_with_fee = amount
        from_amount = from_amount_with_fee * (1 - self._pool.fee_rate)
        to_amount = from_amount * price
        fee = from_amount_with_fee - from_amount
        to_token, from_token = self._convert_pair(self.token0, self.token1)
        self.broker.subtract_from_balance(from_token, from_amount_with_fee)
        self.broker.add_to_balance(to_token, to_amount)
        base_amount, quote_amount = self._convert_pair(to_amount, from_amount)
        self.record_action(SellAction(
            market=self.market_info,
            base_balance_after=self.broker.get_token_balance_with_unit(self.base_token),
            quote_balance_after=self.broker.get_token_balance_with_unit(self.quote_token),
            amount=UnitDecimal(amount, self.base_token.name),
            price=UnitDecimal(price, self._pool_price_unit),
            fee=UnitDecimal(fee, self.quote_token.name),
            base_change=UnitDecimal(base_amount, self.base_token.name),
            quote_change=UnitDecimal(quote_amount, self.quote_token.name)))

        return fee, base_amount, quote_amount

    def even_rebalance(self, price: Decimal = None) -> (Decimal, Decimal, Decimal):
        """
        Divide assets equally between two tokens.

        :param price: price of quote token. eg: 1234 eth/usdc
        :type price: Decimal
        :return: fee, base token amount spend, quote token amount got
        :rtype: (Decimal, Decimal, Decimal)
        """
        if price is None:
            price = self._market_status.price

        total_capital = self.broker.get_token_balance(self.base_token) + self.broker.get_token_balance(
            self.quote_token) * price
        target_base_amount = total_capital / 2
        quote_amount_diff = target_base_amount / price - self.broker.get_token_balance(self.quote_token)
        if quote_amount_diff > 0:
            return self.buy(quote_amount_diff)
        elif quote_amount_diff < 0:
            return self.sell(0 - quote_amount_diff)

    def remove_all_liquidity(self):
        """
        remove all the positions kept in broker.
        """
        if len(self.positions) < 1:
            return
        keys = list(self.positions.keys())
        for position_key in keys:
            self.remove_liquidity(position_key)

    def add_statistic_column(self, df: pd.DataFrame):
        """
        add statistic column to data, new columns including:

        * open: open price
        * price: close price (current price)
        * low: lowest price
        * high: height price
        * volume0: swap volume for token 0
        * volume1: swap volume for token 1

        :param df: original data
        :type df: pd.DataFrame

        """
        # add statistic column
        df["open"] = df["openTick"].map(lambda x: self.tick_to_price(x))
        df["price"] = df["closeTick"].map(lambda x: self.tick_to_price(x))
        high_name, low_name = ("lowestTick", "highestTick") if self.pool_info.is_token0_base \
            else ("highestTick", "lowestTick")
        df["low"] = df[high_name].map(lambda x: self.tick_to_price(x))
        df["high"] = df[low_name].map(lambda x: self.tick_to_price(x))
        df["volume0"] = df["inAmount0"].map(lambda x: Decimal(x) / 10 ** self.pool_info.token0.decimal)
        df["volume1"] = df["inAmount1"].map(lambda x: Decimal(x) / 10 ** self.pool_info.token1.decimal)

    def load_data(self, chain: str, contract_addr: str, start_date: date, end_date: date):
        """

        load data, and preprocess. preprocess actions including:

        * fill empty data
        * calculate statistic column
        * set timestamp as index

        :param chain: chain name
        :type chain: str
        :param contract_addr: pool contract address
        :type contract_addr: str
        :param start_date: start test date
        :type start_date: date
        :param end_date: end test date
        :type end_date: date
        """
        self.logger.info(f"start load files from {start_date} to {end_date}...")
        df = pd.DataFrame()
        day = start_date
        while day <= end_date:
            new_type_path = os.path.join(self.data_path, f"{chain.lower()}-{contract_addr}-{day.strftime('%Y-%m-%d')}.minute.csv")
            path = new_type_path if os.path.exists(new_type_path) else os.path.join(self.data_path, f"{chain}-{contract_addr}-{day.strftime('%Y-%m-%d')}.csv")
            if not os.path.exists(path):
                raise IOError(f"resource file {new_type_path} not found, please download with demeter-fetch: https://github.com/zelos-alpha/demeter-fetch")
            day_df = pd.read_csv(path, converters={'inAmount0': to_decimal,
                                                   'inAmount1': to_decimal,
                                                   'netAmount0': to_decimal,
                                                   'netAmount1': to_decimal,
                                                   "currentLiquidity": to_decimal})
            df = pd.concat([df, day_df])
            day = day + timedelta(days=1)
        self.logger.info("load file complete, preparing...")

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)

        # fill empty row (first minutes in a day, might be blank)
        full_indexes = pd.date_range(start=df.index[0], end=df.index[df.index.size - 1], freq="1min")
        df = df.reindex(full_indexes)
        # df = Lines.from_dataframe(df)
        # df = df.fillna()
        df = fillna(df)
        self.add_statistic_column(df)
        self.data = df
        self.logger.info("data has been prepared")

    def check_before_test(self):
        """
        prefix test
        :return:
        """
        super().check_before_test()
        required_columns = ["closeTick",
                            "currentLiquidity",
                            "inAmount0",
                            "inAmount1",
                            "price"]
        for col in required_columns:
            assert col in self.data.columns

    def formatted_str(self):
        """
        return formatted str info
        :return:
        """
        value = get_formatted_predefined(f"{self.market_info.name}({type(self).__name__})", STYLE["header3"]) + "\n"
        value += get_formatted_from_dict({
            "token0": self.pool_info.token0.name,
            "token1": self.pool_info.token1.name,
            "fee": self.pool_info.fee_rate * 100,
            "is 0 base": self.pool_info.is_token0_base
        }) + "\n"
        value += get_formatted_predefined("positions", STYLE["key"]) + "\n"
        df = position_dict_to_dataframe(self.positions)
        if len(df.index) > 0:
            value += position_dict_to_dataframe(self.positions).to_string()
        else:
            value += "Empty DataFrame"
        return value
