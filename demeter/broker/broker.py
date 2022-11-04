import collections.abc
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Union

from .helper import tick_to_quote_price, quote_price_to_tick
from .liquitidymath import get_sqrt_ratio_at_tick
from .types import TokenInfo, BrokerAsset, PositionVariable, PoolStatus, PositionContainer
from .v3_core import V3CoreLib
from .._typing import PoolBaseInfo, Position, DemeterError, AddLiquidityAction, RemoveLiquidityAction, BuyAction, \
    SellAction, CollectFeeAction, AccountStatus, DECIMAL_ZERO, UnitDecimal
from ..utils.application import float_param_formatter


@dataclass
class AssetPair:
    base: BrokerAsset
    quote: BrokerAsset


class Broker(object):
    """
    Broker manage assets in back testing. Including asset, positions. it also provides operations for positions,
    such as add/remove liquidity, swap assets.

    :param pool_info: pool information
    :type pool_info: PoolBaseInfo
    """

    def __init__(self, pool_info: [PoolBaseInfo]):
        if not isinstance(pool_info, collections.abc):
            pool_info = [pool_info]
        self._pools: [PoolBaseInfo] = pool_info
        self._default_pool = self._pools[0]
        self._base_token = None
        tokens = []
        for pool in self._pools:
            tokens.append(pool.token0)
            tokens.append(pool.token1)
            base_token = pool.token0 if pool.is_token0_base else pool.token1
            if self._base_token is None:
                self._base_token = base_token
            else:
                if self._base_token != base_token:
                    raise DemeterError("base token should be the same")
        # init balance
        tokens = list(set(tokens))
        self._assets: dict[TokenInfo, BrokerAsset] = {}
        self._quote_asset = {}
        for token in tokens:
            self._assets[token] = BrokerAsset(token, DECIMAL_ZERO)
        for pool in self._pools:
            base_asset, quote_asset = Broker.convert_pair(self._assets[pool.token0], self._assets[pool.token1])
            self._pool_assets[pool] = AssetPair(base_asset, quote_asset)

        # status
        self._positions: PositionContainer = PositionContainer(self._pools)
        self._pool_status: dict[PoolBaseInfo, PoolStatus] = {}
        for pool in self._pools:
            self._pool_status[pool] = PoolStatus(None, 0, DECIMAL_ZERO, DECIMAL_ZERO, DECIMAL_ZERO, DECIMAL_ZERO)
        # internal temporary variable
        self.action_buffer = []

    def __str__(self):
        info = "Broker:\n\tPools: "
        for index, pool in enumerate(self.pools):
            info += "{}: {}\t".format(index, pool)
        info += "\n"
        info += str(self.positions)
        info += "\nAssets:"
        for index, asset in enumerate(self._assets):
            info += "{}:{} ".format(asset.name, self._assets[asset].balance)
        return info

    @property
    def positions(self) -> PositionContainer:
        """
        current positions in broker

        :return: all positions
        :rtype: dict[PositionInfo:Position]
        """
        return self._positions

    @property
    def pools(self) -> [PoolBaseInfo]:
        """
        Get pool info.

        :return: pool info
        :rtype: [PoolBaseInfo]
        """
        return self._pools

    @property
    def default_pool(self) -> PoolBaseInfo:
        """
        Get pool info.

        :return: pool info
        :rtype: [PoolBaseInfo]
        """
        return self._default_pool

    @default_pool.setter
    def default_pool(self, pool: PoolBaseInfo):
        self._default_pool = pool

    def get_asset(self, token: TokenInfo) -> BrokerAsset:
        """
        get asset 0 info, including balance

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._assets[token]

    @property
    def base_asset(self) -> BrokerAsset:
        """
        base asset, defined by pool info. It's the reference of asset0 or asset1

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._pool_assets[self._default_pool].base

    def quote_asset(self, pool) -> BrokerAsset:
        """
        quote asset, defined by pool info. It's the reference of asset0 or asset1

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._pool_assets[pool].quote

    def get_pool_status(self, pool) -> PoolStatus:
        """
        current pool status. will be writen by actuator.

        :return: PoolStatus
        :rtype: PoolStatus
        """
        return self._pool_status[pool]

    def set_pool_status(self, pool, value: PoolStatus):
        """
        current pool status. will be writen by actuator.

        Do not update this property unless necessary

        :param value: current pool status
        :type value: PoolStatus
        """
        self._pool_status[pool] = value

    @staticmethod
    def convert_pair(pool: PoolBaseInfo, any0, any1):
        """
        convert order of token0/token1 to base_token/quote_token, according to self.is_token0_base.

        Or convert order of base_token/quote_token to token0/token1

        :param any0: token0 or any property of token0, eg. balance...
        :param any1: token1 or any property of token1, eg. balance...
        :return: (base,qoute) or (token0,token1)
        """
        return (any0, any1) if pool.is_token0_base else (any1, any0)

    @float_param_formatter
    def set_asset(self, token: TokenInfo, amount: Union[Decimal, float]):
        """
        set initial balance for token

        :param token: which token to set
        :type token: TokenInfo
        :param amount: balance, eg: 1.2345
        :type amount: Union[Decimal, float]
        """
        if token not in self._assets:
            raise DemeterError("unknown token")
        self._assets[token].balance = amount

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
        for pool in self.pools:
            for pos, pos_var in self._positions.get_by_pool(pool):
                V3CoreLib.update_fee(pool, pos, pos_var, self._pool_status[pool])

    def get_account_status(self, timestamp: datetime = None) -> AccountStatus:
        """
        get current status, including positions, balances

        :param price: current price, used for calculate position value and net value, if set to None, will use price in current status
        :type price: Decimal
        :param timestamp: current timestamp, default is none
        :type timestamp: datetime
        :return: BrokerStatus
        """

        # TODO : 对价格的处理! 目前的想法是使用交易量最大的那个价格.
        # TODO : 封板了. 这个功能不着急上.
        fee_sum = {}
        deposit_sum = {}
        for token, asset in self._assets:
            fee_sum[token] = DECIMAL_ZERO
            deposit_sum[token] = DECIMAL_ZERO
        pool_token_fee_dict = {}
        pool_token_deposit_dict = {}
        for pool in self._pools:
            tick = quote_price_to_tick(price, pool.token0.decimal, pool.token1.decimal, pool.is_token0_base)
            sqrt_price_x96 = get_sqrt_ratio_at_tick(tick)
            token_fee_dict = {}
            token_deposit_dict = {}
            for pos, pos_var in self._positions.get_by_pool(pool):
                fee_sum[pool.token0] += pos_var.pending_amount0
                fee_sum[pool.token1] += pos_var.pending_amount1
                token_fee_dict[pos] = {
                    pool.token0: pos_var.pending_amount0,
                    pool.token1: pos_var.pending_amount1
                }
                amount0, amount1 = V3CoreLib.get_token_amounts(pool, pos, sqrt_price_x96, pos_var.liquidity)
                deposit_sum[pool.token0] += amount0
                deposit_sum[pool.token1] += amount1
                token_deposit_dict[pos] = {
                    pool.token0: amount0,
                    pool.token1: amount1
                }
            pool_token_fee_dict[pool] = token_fee_dict
            pool_token_deposit_dict[pool] = token_deposit_dict

        net_value = DECIMAL_ZERO
        for token, asset in self._assets:
            net_value += asset.balance + fee_sum[token] + deposit_sum[token]  # TODO !!! 乘以不同的价格.
        return AccountStatus(timestamp=timestamp,
                             balance={k: v.balance for k, v in self._assets},
                             uncollected=pool_token_fee_dict,
                             in_position=pool_token_deposit_dict,
                             net_value=UnitDecimal(net_value, self.base_asset.name),
                             price={k: v.price for k, v in self._pool_status}  # TODO : 改成按照token的价格.
                             )

    @staticmethod
    def tick_to_price(pool: PoolBaseInfo, tick: int) -> Decimal:
        """
        convert tick to price

        :param tick: tick
        :type tick: int
        :return: price
        :rtype: Decimal
        """
        return tick_to_quote_price(int(tick), pool.token0.decimal, pool.token1.decimal, pool.is_token0_base)

    @float_param_formatter
    @staticmethod
    def price_to_tick(pool: PoolBaseInfo, price: Union[Decimal, float]) -> int:
        """
        convert price to tick

        :param price: price
        :type price:  Union[Decimal, float]
        :return: tick
        :rtype: int
        """
        return quote_price_to_tick(price, pool.token0.decimal, pool.token1.decimal, pool.is_token0_base)

    def _add_liquidity_by_tick(self, pool: PoolBaseInfo,
                               token0_amount: Decimal,
                               token1_amount: Decimal,
                               lower_tick: int,
                               upper_tick: int,
                               sqrt_price_x96: int = -1):
        lower_tick = int(lower_tick)
        upper_tick = int(upper_tick)
        sqrt_price_x96 = int(sqrt_price_x96)

        if sqrt_price_x96 == -1:
            # self.current_tick must be initialed
            sqrt_price_x96 = get_sqrt_ratio_at_tick(self.pool_status.current_tick)
        if lower_tick > upper_tick:
            raise DemeterError("lower tick should be less than upper tick")

        token0_used, token1_used, liquidity, pos = \
            V3CoreLib.new_position(pool, token0_amount, token1_amount, lower_tick, upper_tick, sqrt_price_x96)
        if pos in self._positions.get_by_pool(pool):
            self._positions[pos].liquidity += liquidity
        else:
            self._positions[pos] = PositionVariable(DECIMAL_ZERO, DECIMAL_ZERO, liquidity)
        self._assets[pool.token0].sub(token0_used)
        self._assets[pool.token1].sub(token1_used)
        return pos, token0_used, token1_used, liquidity

    def __remove_liquidity(self, pool: PoolBaseInfo, position: Position, liquidity: int = None,
                           sqrt_price_x96: int = -1):
        sqrt_price_x96 = int(sqrt_price_x96) if sqrt_price_x96 != -1 else \
            get_sqrt_ratio_at_tick(self._pool_status[pool].current_tick)
        delta_liquidity = liquidity if liquidity and liquidity < self._positions.get(pool, position).liquidity \
            else self.positions[position].liquidity
        token0_get, token1_get = V3CoreLib.close_position(pool, position, delta_liquidity, sqrt_price_x96)

        self._positions.get(pool, position).liquidity -= delta_liquidity
        self._positions.get(pool, position).pending_amount0 += token0_get
        self._positions.get(pool, position).pending_amount1 += token1_get

        return token0_get, token1_get, delta_liquidity

    def __collect_fee(self,
                      pool: PoolBaseInfo,
                      pos_var: PositionVariable,
                      max_collect_amount0: Decimal = None,
                      max_collect_amount1: Decimal = None):
        token0_collected = max_collect_amount0 if max_collect_amount0 is not None and max_collect_amount0 < pos_var.pending_amount0 else pos_var.pending_amount0
        token1_collected = max_collect_amount1 if max_collect_amount1 is not None and max_collect_amount1 < pos_var.pending_amount1 else pos_var.pending_amount1

        pos_var.pending_amount0 -= token0_collected
        pos_var.pending_amount1 -= token1_collected
        # add un_collect fee to current balance
        self._assets[pool.token0].add(token0_collected)
        self._assets[pool.token1].add(token1_collected)

        return token0_collected, token1_collected

    # action for strategy

    @float_param_formatter
    def add_liquidity(self,
                      lower_quote_price: Union[Decimal, float],
                      upper_quote_price: Union[Decimal, float],
                      base_max_amount: Union[Decimal, float] = None,
                      quote_max_amount: Union[Decimal, float] = None,
                      pool: PoolBaseInfo = None) -> (Position, Decimal, Decimal):
        """

        add liquidity, then get a new position

        :param lower_quote_price: lower price base on quote token.
        :type lower_quote_price: Union[Decimal, float]
        :param upper_quote_price: upper price base on quote token.
        :type upper_quote_price: Union[Decimal, float]
        :param base_max_amount:  inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type base_max_amount: Union[Decimal, float]
        :param quote_max_amount: inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type quote_max_amount: Union[Decimal, float]
        :return: added position, base token used, quote token used
        :rtype: (Position, Decimal, Decimal)
        """
        pool = pool if pool else self._default_pool
        base_max_amount = self._pool_assets[pool].base.balance if base_max_amount is None else base_max_amount
        quote_max_amount = self._pool_assets[pool].quote.balance if quote_max_amount is None else quote_max_amount

        token0_amt, token1_amt = Broker.convert_pair(pool, base_max_amount, quote_max_amount)
        lower_tick, upper_tick = V3CoreLib.quote_price_pair_to_tick(self._pools, lower_quote_price,
                                                                    upper_quote_price)
        lower_tick, upper_tick = Broker.convert_pair(pool.upper_tick, lower_tick)
        (created_position, token0_used, token1_used, liquidity) = \
            self._add_liquidity_by_tick(pool, token0_amt, token1_amt, lower_tick, upper_tick)
        base_used, quote_used = self.convert_pair(token0_used, token1_used)
        self.action_buffer.append(
            AddLiquidityAction(base_balance_after=UnitDecimal(self.base_asset.balance, self.base_asset.name),
                               quote_balance_after=UnitDecimal(self.quote_asset(pool).balance,
                                                               self.quote_asset(pool).name),
                               pool=pool,
                               base_amount_max=UnitDecimal(base_max_amount, self.base_asset.name),
                               quote_amount_max=UnitDecimal(quote_max_amount, self.quote_asset(pool).name),
                               lower_quote_price=UnitDecimal(lower_quote_price, pool.price_unit),
                               upper_quote_price=UnitDecimal(upper_quote_price, pool.price_unit),
                               base_amount_actual=UnitDecimal(base_used, self.base_asset.name),
                               quote_amount_actual=UnitDecimal(quote_used, self.quote_asset(pool).name),
                               position=created_position,
                               liquidity=int(liquidity)))
        return created_position, base_used, quote_used, liquidity

    def add_liquidity_by_tick(self, lower_tick: int,
                              upper_tick: int,
                              base_max_amount: Union[Decimal, float] = None,
                              quote_max_amount: Union[Decimal, float] = None,
                              sqrt_price_x96: int = -1,
                              pool: PoolBaseInfo = None):
        """

        add liquidity, you need to set tick instead of price.

        :param lower_tick: lower tick
        :type lower_tick: int
        :param upper_tick: upper tick
        :type upper_tick: int
        :param base_max_amount:  inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type base_max_amount: Union[Decimal, float]
        :param quote_max_amount: inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type quote_max_amount: Union[Decimal, float]
        :param sqrt_price_x96: precise price.  if set to none, it will be calculated from current price.
        :type sqrt_price_x96: int
        :return: added position, base token used, quote token used
        :rtype: (Position, Decimal, Decimal)
        """
        pool = pool if pool else self._default_pool
        base_max_amount = self._pool_assets[pool].base.balance if base_max_amount is None else base_max_amount
        quote_max_amount = self._pool_assets[pool].quote.balance if quote_max_amount is None else quote_max_amount
        token0_amt, token1_amt = Broker.convert_pair(pool, base_max_amount, quote_max_amount)
        (created_position, token0_used, token1_used, liquidity) = \
            self._add_liquidity_by_tick(pool, token0_amt, token1_amt, lower_tick, upper_tick, sqrt_price_x96)
        base_used, quote_used = Broker.convert_pair(token0_used, token1_used)
        self.action_buffer.append(
            AddLiquidityAction(base_balance_after=UnitDecimal(self.base_asset.balance, self.base_asset.name),
                               quote_balance_after=UnitDecimal(self.quote_asset(pool).balance,
                                                               self.quote_asset(pool).name),
                               pool=pool,
                               base_amount_max=UnitDecimal(base_max_amount, self.base_asset.name),
                               quote_amount_max=UnitDecimal(quote_max_amount, self.quote_asset(pool).name),
                               lower_quote_price=UnitDecimal(self.tick_to_price(lower_tick), pool.price_unit),
                               upper_quote_price=UnitDecimal(self.tick_to_price(upper_tick), pool.price_unit),
                               base_amount_actual=UnitDecimal(base_used, self.base_asset.name),
                               quote_amount_actual=UnitDecimal(quote_used, self.quote_asset(pool).name),
                               position=created_position,
                               liquidity=int(liquidity)))
        return created_position, base_used, quote_used, liquidity

    @float_param_formatter
    def remove_liquidity(self, position: Position, liquidity: int = None, collect: bool = True,
                         sqrt_price_x96: int = -1, pool: PoolBaseInfo = None) -> (Decimal, Decimal):
        """
        remove liquidity from pool, liquidity will be reduced to 0,
        instead of send tokens to broker, tokens will be transferred to fee property in position.
        position will be not deleted, until fees and tokens are collected.

        :param position: position to remove.
        :type position: Position
        :param liquidity: liquidity amount to remove, if set to None, all the liquidity will be removed
        :type liquidity: int
        :param collect: collect or not, if collect, will call collect function. and tokens will be sent to broker. if not token will be kept in fee property of postion
        :type collect: bool
        :param sqrt_price_x96: precise price.  if set to none, it will be calculated from current price.
        :type sqrt_price_x96: int
        :return: (base_got,quote_get), base and quote token amounts collected from position
        :rtype:  (Decimal,Decimal)
        """
        pool = pool if pool else self._default_pool
        if liquidity and liquidity < 0:
            raise DemeterError("liquidity should large than 0")
        token0_get, token1_get, delta_liquidity = self.__remove_liquidity(pool, position, liquidity, sqrt_price_x96)

        base_get, quote_get = Broker.convert_pair(token0_get, token1_get)
        self.action_buffer.append(
            RemoveLiquidityAction(
                base_balance_after=UnitDecimal(self.base_asset.balance, self.base_asset.name),
                quote_balance_after=UnitDecimal(self.quote_asset(pool).balance, self.quote_asset(pool).name),
                pool=pool,
                position=position,
                base_amount=UnitDecimal(base_get, self.base_asset.name),
                quote_amount=UnitDecimal(quote_get, self.quote_asset(pool).name),
                removed_liquidity=delta_liquidity,
                remain_liquidity=self.positions[position].liquidity
            ))
        if collect:
            return self.collect_fee(position, pool=pool)
        else:
            return base_get, quote_get

    @float_param_formatter
    def collect_fee(self,
                    position: Position,
                    max_collect_amount0: Decimal = None,
                    max_collect_amount1: Decimal = None,
                    pool: PoolBaseInfo = None) -> (Decimal, Decimal):
        """
        collect fee and token from positions,
        if the amount and liquidity is zero, this position will be deleted.

        :param position: position to collect
        :type position: Position
        :param max_collect_amount0: max token0 amount to collect, eg: 1.2345 usdc, if set to None, all the amount will be collect
        :type max_collect_amount0: Decimal
        :param max_collect_amount1: max token0 amount to collect, if set to None, all the amount will be collect
        :type max_collect_amount1: Decimal
        :return: (base_got,quote_get), base and quote token amounts collected from position
        :rtype:  (Decimal,Decimal)
        """
        pool = pool if pool else self._default_pool
        if (max_collect_amount0 and max_collect_amount0 < 0) or \
                (max_collect_amount1 and max_collect_amount1 < 0):
            raise DemeterError("collect amount should large than 0")
        token0_get, token1_get = self.__collect_fee(pool,
                                                    self._positions.get(pool, position),
                                                    max_collect_amount0,
                                                    max_collect_amount1)

        base_get, quote_get = Broker.convert_pair(token0_get, token1_get)
        if self._positions[position]:
            self.action_buffer.append(
                CollectFeeAction(
                    base_balance_after=UnitDecimal(self.base_asset.balance, self.base_asset.name),
                    quote_balance_after=UnitDecimal(self.quote_asset(pool).balance, self.quote_asset(pool).name),
                    pool=pool,
                    position=position,
                    base_amount=UnitDecimal(base_get, self.base_asset.name),
                    quote_amount=UnitDecimal(quote_get, self.quote_asset(pool).name)
                ))
        if self._positions[position].pending_amount0 == Decimal(0) \
                and self._positions[position].pending_amount1 == Decimal(0) \
                and self._positions[position].liquidity == 0:
            self._positions.remove(pool, position)
        return base_get, quote_get

    @float_param_formatter
    def buy(self, amount: Union[Decimal, float], price: Union[Decimal, float] = None, pool: PoolBaseInfo = None) \
            -> (Decimal, Decimal, Decimal):
        """
        buy token, swap from base token to quote token.

        :param amount: amount to buy(in quote token)
        :type amount:  Union[Decimal, float]
        :param price: price
        :type price: Union[Decimal, float]
        :return: fee, base token amount spend, quote token amount got
        :rtype: (Decimal, Decimal, Decimal)
        """
        pool = pool if pool else self._default_pool
        price = price if price else self._pool_status[pool].price
        from_amount = price * amount
        from_amount_with_fee = from_amount * (1 + pool.fee_rate)
        fee = from_amount_with_fee - from_amount
        from_asset, to_asset = Broker.convert_pair(self._assets[pool].asset0, self._assets[pool].asset1)
        from_asset.sub(from_amount_with_fee)
        to_asset.add(amount)
        base_amount, quote_amount = Broker.convert_pair(from_amount, amount)
        self.action_buffer.append(
            BuyAction(base_balance_after=UnitDecimal(self.base_asset.balance, self.base_asset.name),
                      quote_balance_after=UnitDecimal(self.quote_asset(pool).balance, self.quote_asset(pool).name),
                      pool=pool,
                      amount=UnitDecimal(amount, self.quote_asset(pool).name),
                      price=UnitDecimal(price, pool.price_unit),
                      fee=UnitDecimal(fee, self.base_asset.name),
                      base_change=UnitDecimal(base_amount, self.base_asset.name),
                      quote_change=UnitDecimal(quote_amount, self.quote_asset(pool).name)))
        return fee, base_amount, quote_amount

    @float_param_formatter
    def sell(self, amount: Union[Decimal, float], price: Union[Decimal, float] = None, pool: PoolBaseInfo = None) \
            -> (Decimal, Decimal, Decimal):
        """
        sell token, swap from quote token to base token.

        :param amount: amount to sell(in quote token)
        :type amount:  Union[Decimal, float]
        :param price: price
        :type price: Union[Decimal, float]
        :return: fee, base token amount got, quote token amount spend
        :rtype: (Decimal, Decimal, Decimal)
        """
        pool = pool if pool else self._default_pool

        price = price if price else self._pool_status[pool].price
        from_amount_with_fee = amount
        from_amount = from_amount_with_fee * (1 - pool.fee_rate)
        to_amount = from_amount * price
        fee = from_amount_with_fee - from_amount
        from_asset, to_asset = Broker.convert_pair(self._assets[pool].asset0, self._assets[pool].asset1)
        from_asset.sub(from_amount_with_fee)
        to_asset.add(to_amount)
        base_amount, quote_amount = Broker.convert_pair(to_amount, from_amount)
        self.action_buffer.append(
            SellAction(base_balance_after=UnitDecimal(self.base_asset.balance, self.base_asset.name),
                       quote_balance_after=UnitDecimal(self.quote_asset(pool).balance, self.quote_asset(pool).name),
                       pool=pool,
                       amount=UnitDecimal(amount, self.quote_asset(pool).name),
                       price=UnitDecimal(price, pool.price_unit),
                       fee=UnitDecimal(fee, self.quote_asset(pool).name),
                       base_change=UnitDecimal(base_amount, self.base_asset.name),
                       quote_change=UnitDecimal(quote_amount, self.quote_asset(pool).name)))

        return fee, base_amount, quote_amount

    def remove_all_liquidity(self):
        """
        remove all the positions kept in broker.
        """
        for pool in self.pools:
            for pos, pos_var in self._positions.get_by_pool(pool):
                self.remove_liquidity(pos, pool=pool)
