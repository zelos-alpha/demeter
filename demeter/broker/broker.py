import collections.abc
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Union

from .helper import tick_to_quote_price, quote_price_to_tick
from .liquitidymath import get_sqrt_ratio_at_tick
from .types import PoolBaseInfo, TokenInfo, BrokerAsset, Position, PoolStatus
from .v3_core import V3CoreLib
from .._typing import PositionInfo, DemeterError, AddLiquidityAction, RemoveLiquidityAction, BuyAction, SellAction, \
    CollectFeeAction, AccountStatus, DECIMAL_ZERO, UnitDecimal
from ..utils.application import float_param_formatter


@dataclass
class AssetPair:
    base: BrokerAsset
    quote: BrokerAsset


class PositionContainer:
    def __init__(self, pools: [PoolBaseInfo]):
        self.positions: {PoolBaseInfo, dict[PositionInfo:Position]} = {}
        for pool in pools:
            self.positions[pool] = {}

    def get(self, pool: PoolBaseInfo, position: PositionInfo):
        return self.positions[pool][position]

    def set(self, pool: PoolBaseInfo, position: PositionInfo, value: Position):
        self.positions[pool][position] = value

    def get_by_pool(self, pool: PoolBaseInfo):
        return self.positions[pool]

    def __str__(self):
        value = "PositionContainer: \n"
        for index, pool in enumerate(self.positions):
            value += "pool {}, {}: (".format(index, pool)
            for pos_index, position in enumerate(self.positions[pool]):
                value += "{}: {}".format(position, self.positions[pool][position])
            value += ")\n"


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
        for token in tokens:
            self._assets[token] = BrokerAsset(token, DECIMAL_ZERO)
        self._pool_assets = {}
        for pool in self._pools:
            base_asset, quote_asset = Broker.convert_pair(self._assets[pool.token0], self._assets[pool.token1])
            self._pool_assets[pool] = AssetPair(base_asset, quote_asset)

        # status
        self._positions: PositionContainer = PositionContainer(self._pools)
        self._pool_status: dict[PoolBaseInfo, PoolStatus] = {}
        for pool in self._pools:
            self._pool_status[pool] = PoolStatus(None, 0, DECIMAL_ZERO, DECIMAL_ZERO, DECIMAL_ZERO, DECIMAL_ZERO,
                                                 f"{self._pool_assets[pool].base.name}/{self._pool_assets[pool].quote.name}")
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

    def get_asset(self, token: TokenInfo) -> BrokerAsset:
        """
        get asset 0 info, including balance

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._assets[token]

    def get_base_asset(self, pool) -> BrokerAsset:
        """
        base asset, defined by pool info. It's the reference of asset0 or asset1

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._pool_assets[pool].base

    def get_quote_asset(self, pool) -> BrokerAsset:
        """
        quote asset, defined by pool info. It's the reference of asset0 or asset1

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._pool_assets[pool].quote

    @property
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

    def get_position(self, pool: PoolBaseInfo, position_info: PositionInfo) -> Position:
        """
        get position by position information

        :param position_info: position information
        :type position_info: PositionInfo
        :return: Position
        :rtype: Position
        """
        return self._positions.get(pool, position_info)

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
            for position_info, position in self._positions.positions[pool]:
                V3CoreLib.update_fee(pool, position_info, position, self._pool_status[pool])

    def get_account_status(self, price: Decimal = None, timestamp: datetime = None) -> AccountStatus:
        """
        get current status, including positions, balances

        :param price: current price, used for calculate position value and net value, if set to None, will use price in current status
        :type price: Decimal
        :param timestamp: current timestamp, default is none
        :type timestamp: datetime
        :return: BrokerStatus
        """
        if price is None:
            price = self.pool_status.price
        base_asset, quote_asset = Broker.convert_pair(pool, self._asset0, self._asset1)
        base_fee_sum = DECIMAL_ZERO
        quote_fee_sum = DECIMAL_ZERO
        tick = quote_price_to_tick(price, self.asset0.decimal, self.asset1.decimal, self._is_token0_base)
        sqrt_price_x96=get_sqrt_ratio_at_tick(tick)
        deposit_amount0 = deposit_amount1 = Decimal(0)
        for position_info, position in self._positions.items():
            base_fee, quote_fee = Broker.convert_pair(position.pending_amount0,
                                                      position.pending_amount1)
            base_fee_sum += base_fee
            quote_fee_sum += quote_fee
            amount0, amount1 = V3CoreLib.get_token_amounts(self._pools, position_info, sqrt_price_x96, position.liquidity)
            deposit_amount0 += amount0
            deposit_amount1 += amount1

        base_deposit_amount, quote_deposit_amount = Broker.convert_pair(deposit_amount0, deposit_amount1)
        capital = (base_asset.balance + base_fee_sum + base_deposit_amount) + \
                  (quote_asset.balance + quote_fee_sum + quote_deposit_amount) * price
        base_init_amount, quote_init_amount = Broker.convert_pair(self._init_amount0, self._init_amount1)

        net_value = capital / (base_init_amount + price * quote_init_amount)

        profit_pct = (net_value - 1) * 100
        return AccountStatus(timestamp,
                             UnitDecimal(base_asset.balance, self.base_asset.name),
                             UnitDecimal(quote_asset.balance, self.quote_asset.name),
                             UnitDecimal(base_fee_sum, self.base_asset.name),
                             UnitDecimal(quote_fee_sum, self.quote_asset.name),
                             UnitDecimal(base_deposit_amount, self.base_asset.name),
                             UnitDecimal(quote_deposit_amount, self.quote_asset.name),
                             UnitDecimal(capital, self.base_asset.name),
                             UnitDecimal(price, self._price_unit))

    def tick_to_price(self, tick: int) -> Decimal:
        """
        convert tick to price

        :param tick: tick
        :type tick: int
        :return: price
        :rtype: Decimal
        """
        return tick_to_quote_price(int(tick), self.pools.token0.decimal, self.pools.token1.decimal,
                                   self._is_token0_base)

    @float_param_formatter
    def price_to_tick(self, price: Union[Decimal, float]) -> int:
        """
        convert price to tick

        :param price: price
        :type price:  Union[Decimal, float]
        :return: tick
        :rtype: int
        """
        return quote_price_to_tick(price, self.pools.token0.decimal, self.pools.token1.decimal,
                                   self._is_token0_base)

    def _add_liquidity_by_tick(self, token0_amount: Decimal,
                               token1_amount: Decimal,
                               lower_tick: int,
                               upper_tick: int,
                               sqrt_price_x96: int = -1,
                               pool: PoolBaseInfo = None):
        lower_tick = int(lower_tick)
        upper_tick = int(upper_tick)
        sqrt_price_x96 = int(sqrt_price_x96)

        if sqrt_price_x96 == -1:
            # self.current_tick must be initialed
            sqrt_price_x96 = get_sqrt_ratio_at_tick(self.pool_status.current_tick)
        if lower_tick > upper_tick:
            raise DemeterError("lower tick should be less than upper tick")

        token0_used, token1_used, liquidity, position_info = V3CoreLib.new_position(pool,
                                                                                    token0_amount,
                                                                                    token1_amount,
                                                                                    lower_tick,
                                                                                    upper_tick,
                                                                                    sqrt_price_x96)
        if position_info in self._positions.get_by_pool(pool):
            self._positions[position_info].liquidity += liquidity
        else:
            self._positions[position_info] = Position(DECIMAL_ZERO, DECIMAL_ZERO, liquidity)
        self._assets[pool.token0].sub(token0_used)
        self._assets[pool.token1].sub(token1_used)
        return position_info, token0_used, token1_used, liquidity

    def __remove_liquidity(self, position: PositionInfo, liquidity: int = None, sqrt_price_x96: int = -1):
        sqrt_price_x96 = int(sqrt_price_x96) if sqrt_price_x96 != -1 else get_sqrt_ratio_at_tick(
            self.pool_status.current_tick)
        delta_liquidity = liquidity if liquidity and liquidity < self.positions[position].liquidity \
            else self.positions[position].liquidity
        token0_get, token1_get = V3CoreLib.close_position(self._pools, position, delta_liquidity, sqrt_price_x96)

        self._positions[position].liquidity = self.positions[position].liquidity - delta_liquidity
        self._positions[position].pending_amount0 += token0_get
        self._positions[position].pending_amount1 += token1_get

        return token0_get, token1_get, delta_liquidity

    def __collect_fee(self, position: Position, max_collect_amount0: Decimal = None,
                      max_collect_amount1: Decimal = None):
        token0_fee = max_collect_amount0 if max_collect_amount0 is not None and max_collect_amount0 < position.pending_amount0 else position.pending_amount0
        token1_fee = max_collect_amount1 if max_collect_amount1 is not None and max_collect_amount1 < position.pending_amount1 else position.pending_amount1

        position.pending_amount0 -= token0_fee
        position.pending_amount1 -= token1_fee
        # add un_collect fee to current balance
        self._asset0.add(token0_fee)
        self._asset1.add(token1_fee)

        return token0_fee, token1_fee

    # action for strategy

    @float_param_formatter
    def add_liquidity(self,
                      lower_quote_price: Union[Decimal, float],
                      upper_quote_price: Union[Decimal, float],
                      base_max_amount: Union[Decimal, float] = None,
                      quote_max_amount: Union[Decimal, float] = None,
                      pool: PoolBaseInfo = None) -> (PositionInfo, Decimal, Decimal):
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
        :rtype: (PositionInfo, Decimal, Decimal)
        """
        if not pool:
            pool = self._default_pool
        base_max_amount = self._pool_assets[pool].base.balance if base_max_amount is None else base_max_amount
        quote_max_amount = self._pool_assets[pool].quote.balance if quote_max_amount is None else quote_max_amount

        token0_amt, token1_amt = Broker.convert_pair(pool, base_max_amount, quote_max_amount)
        lower_tick, upper_tick = V3CoreLib.quote_price_pair_to_tick(self._pools, lower_quote_price,
                                                                    upper_quote_price)
        lower_tick, upper_tick = Broker.convert_pair(pool.upper_tick, lower_tick)
        (created_position, token0_used, token1_used, liquidity) = self._add_liquidity_by_tick(token0_amt,
                                                                                              token1_amt,
                                                                                              lower_tick,
                                                                                              upper_tick,
                                                                                              pool)
        base_used, quote_used = self.convert_pair(token0_used, token1_used)
        self.action_buffer.append(AddLiquidityAction(pool,
                                                     UnitDecimal(self.base_asset.balance, self.base_asset.name),
                                                     UnitDecimal(self.quote_asset.balance, self.quote_asset.name),
                                                     UnitDecimal(base_max_amount, self.base_asset.name),
                                                     UnitDecimal(quote_max_amount, self.quote_asset.name),
                                                     UnitDecimal(lower_quote_price, self._price_unit),
                                                     UnitDecimal(upper_quote_price, self._price_unit),
                                                     UnitDecimal(base_used, self.base_asset.name),
                                                     UnitDecimal(quote_used, self.quote_asset.name),
                                                     created_position,
                                                     int(liquidity)))
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
        :rtype: (PositionInfo, Decimal, Decimal)
        """
        if not pool:
            pool = self._default_pool
        base_max_amount = self._pool_assets[pool].base.balance if base_max_amount is None else base_max_amount
        quote_max_amount = self._pool_assets[pool].quote.balance if quote_max_amount is None else quote_max_amount
        token0_amt, token1_amt = Broker.convert_pair(pool, base_max_amount, quote_max_amount)
        (created_position, token0_used, token1_used, liquidity) = self._add_liquidity_by_tick(token0_amt,
                                                                                              token1_amt,
                                                                                              lower_tick,
                                                                                              upper_tick,
                                                                                              sqrt_price_x96,
                                                                                              pool)
        base_used, quote_used = Broker.convert_pair(token0_used, token1_used)
        self.action_buffer.append(AddLiquidityAction(pool,
                                                     UnitDecimal(self.base_asset.balance, self.base_asset.name),
                                                     UnitDecimal(self.quote_asset.balance, self.quote_asset.name),
                                                     UnitDecimal(base_max_amount, self.base_asset.name),
                                                     UnitDecimal(quote_max_amount, self.quote_asset.name),
                                                     UnitDecimal(self.tick_to_price(lower_tick), self._price_unit),
                                                     UnitDecimal(self.tick_to_price(upper_tick), self._price_unit),
                                                     UnitDecimal(base_used, self.base_asset.name),
                                                     UnitDecimal(quote_used, self.quote_asset.name),
                                                     created_position,
                                                     int(liquidity)))
        return created_position, base_used, quote_used, liquidity

    @float_param_formatter
    def remove_liquidity(self, position: PositionInfo, liquidity: int = None, collect: bool = True,
                         sqrt_price_x96: int = -1) -> (Decimal, Decimal):
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
        :return: (base_got,quote_get), base and quote token amounts collected from position
        :rtype:  (Decimal,Decimal)
        """
        if liquidity and liquidity < 0:
            raise DemeterError("liquidity should large than 0")
        token0_get, token1_get, delta_liquidity = self.__remove_liquidity(position, liquidity, sqrt_price_x96)

        base_get, quote_get = Broker.convert_pair(token0_get, token1_get)
        self.action_buffer.append(
            RemoveLiquidityAction(
                UnitDecimal(self.base_asset.balance, self.base_asset.name),
                UnitDecimal(self.quote_asset.balance, self.quote_asset.name),
                position,
                UnitDecimal(base_get, self.base_asset.name),
                UnitDecimal(quote_get, self.quote_asset.name),
                delta_liquidity,
                self.positions[position].liquidity
            ))
        if collect:
            return self.collect_fee(position)
        else:
            return base_get, quote_get

    @float_param_formatter
    def collect_fee(self,
                    position: PositionInfo,
                    max_collect_amount0: Decimal = None,
                    max_collect_amount1: Decimal = None) -> (Decimal, Decimal):
        """
        collect fee and token from positions,
        if the amount and liquidity is zero, this position will be deleted.

        :param position: position to collect
        :type position: PositionInfo
        :param max_collect_amount0: max token0 amount to collect, eg: 1.2345 usdc, if set to None, all the amount will be collect
        :type max_collect_amount0: Decimal
        :param max_collect_amount1: max token0 amount to collect, if set to None, all the amount will be collect
        :type max_collect_amount1: Decimal
        :return: (base_got,quote_get), base and quote token amounts collected from position
        :rtype:  (Decimal,Decimal)
        """
        if (max_collect_amount0 and max_collect_amount0 < 0) or \
                (max_collect_amount1 and max_collect_amount1 < 0):
            raise DemeterError("collect amount should large than 0")
        token0_get, token1_get = self.__collect_fee(self._positions[position])

        base_get, quote_get = Broker.convert_pair(token0_get, token1_get)
        if self._positions[position]:
            self.action_buffer.append(
                CollectFeeAction(
                    UnitDecimal(self.base_asset.balance, self.base_asset.name),
                    UnitDecimal(self.quote_asset.balance, self.quote_asset.name),
                    position,
                    UnitDecimal(base_get, self.base_asset.name),
                    UnitDecimal(quote_get, self.quote_asset.name)
                ))
        if self._positions[position].pending_amount0 == Decimal(0) \
                and self._positions[position].pending_amount1 == Decimal(0) \
                and self._positions[position].liquidity == 0:
            del self.positions[position]
        return base_get, quote_get

    @float_param_formatter
    def buy(self, amount: Union[Decimal, float], price: Union[Decimal, float] = None) -> (Decimal, Decimal, Decimal):
        """
        buy token, swap from base token to quote token.

        :param amount: amount to buy(in quote token)
        :type amount:  Union[Decimal, float]
        :param price: price
        :type price: Union[Decimal, float]
        :return: fee, base token amount spend, quote token amount got
        :rtype: (Decimal, Decimal, Decimal)
        """
        price = price if price else self.pool_status.price
        from_amount = price * amount
        from_amount_with_fee = from_amount * (1 + self.pools.fee_rate)
        fee = from_amount_with_fee - from_amount
        from_asset, to_asset = Broker.convert_pair(self._asset0, self._asset1)
        from_asset.sub(from_amount_with_fee)
        to_asset.add(amount)
        base_amount, quote_amount = Broker.convert_pair(from_amount, amount)
        self.action_buffer.append(BuyAction(UnitDecimal(self.base_asset.balance, self.base_asset.name),
                                            UnitDecimal(self.quote_asset.balance, self.quote_asset.name),
                                            UnitDecimal(amount, self.quote_asset.name),
                                            UnitDecimal(price, self._price_unit),
                                            UnitDecimal(fee, self.base_asset.name),
                                            UnitDecimal(base_amount, self.base_asset.name),
                                            UnitDecimal(quote_amount, self.quote_asset.name)))
        return fee, base_amount, quote_amount

    @float_param_formatter
    def sell(self, amount: Union[Decimal, float], price: Union[Decimal, float] = None) -> (Decimal, Decimal, Decimal):
        """
        sell token, swap from quote token to base token.

        :param amount: amount to sell(in quote token)
        :type amount:  Union[Decimal, float]
        :param price: price
        :type price: Union[Decimal, float]
        :return: fee, base token amount got, quote token amount spend
        :rtype: (Decimal, Decimal, Decimal)
        """
        price = price if price else self.pool_status.price
        from_amount_with_fee = amount
        from_amount = from_amount_with_fee * (1 - self.pools.fee_rate)
        to_amount = from_amount * price
        fee = from_amount_with_fee - from_amount
        to_asset, from_asset = Broker.convert_pair(self._asset0, self._asset1)
        from_asset.sub(from_amount_with_fee)
        to_asset.add(to_amount)
        base_amount, quote_amount = Broker.convert_pair(to_amount, from_amount)
        self.action_buffer.append(SellAction(UnitDecimal(self.base_asset.balance, self.base_asset.name),
                                             UnitDecimal(self.quote_asset.balance, self.quote_asset.name),
                                             UnitDecimal(amount, self.quote_asset.name),
                                             UnitDecimal(price, self._price_unit),
                                             UnitDecimal(fee, self.quote_asset.name),
                                             UnitDecimal(base_amount, self.base_asset.name),
                                             UnitDecimal(quote_amount, self.quote_asset.name)))

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
            price = self._pool_status.price

        total_capital = self.base_asset.balance + self.quote_asset.balance * price
        target_base_amount = total_capital / 2
        quote_amount_diff = target_base_amount / price - self.quote_asset.balance
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
