from datetime import datetime
from decimal import Decimal

from .._typing import PositionInfo, ZelosError, AddLiquidityAction, RemoveLiquidityAction, BuyAction, SellAction, \
    CollectFeeAction, AccountStatus, DECIMAL_ZERO, UnitDecimal
from ..utils.application import float_param_formatter

from .types import PoolBaseInfo, TokenInfo, BrokerAsset, Position, PoolStatus
from .v3_core import V3CoreLib
from .helper import tick_to_quote_price, quote_price_to_tick
from typing import Union


class Broker(object):
    """
    Broker manage assets in back testing. Including asset, positions. it also provides operations for positions,
    such as add/remove liquidity, swap assets.

    :param pool_info: pool information
    :type pool_info: PoolBaseInfo
    """

    def __init__(self, pool_info: PoolBaseInfo):
        self._pool_info = pool_info
        # init balance
        self._is_token0_base = pool_info.is_token0_base
        self._asset0 = BrokerAsset(pool_info.token0, DECIMAL_ZERO)
        self._asset1 = BrokerAsset(pool_info.token1, DECIMAL_ZERO)
        base_asset, quote_asset = self.__convert_pair(self._asset0, self._asset1)
        self._base_asset: BrokerAsset = base_asset
        self._quote_asset: BrokerAsset = quote_asset
        self._init_amount0 = DECIMAL_ZERO
        self._init_amount1 = DECIMAL_ZERO
        # status
        self._positions: dict[PositionInfo:Position] = {}
        self._pool_status = PoolStatus(None, 0, DECIMAL_ZERO, DECIMAL_ZERO, DECIMAL_ZERO, DECIMAL_ZERO)
        self._price_unit = f"{self.base_asset.name}/{self.quote_asset.name}"
        # internal temporary variable
        self.action_buffer = []

    @property
    def positions(self) -> dict[PositionInfo:Position]:
        """
        current positions in broker

        :return: all positions
        :rtype: dict[PositionInfo:Position]
        """
        return self._positions

    @property
    def pool_info(self) -> PoolBaseInfo:
        """
        Get pool info.

        :return: pool info
        :rtype: PoolBaseInfo
        """
        return self._pool_info

    @property
    def asset0(self) -> BrokerAsset:
        """
        get asset 0 info, including balance

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._asset0

    @property
    def asset1(self) -> BrokerAsset:
        """
        get asset 1 info, including balance

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._asset1

    @property
    def base_asset(self) -> BrokerAsset:
        """
        base asset, defined by pool info. It's the reference of asset0 or asset1

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._base_asset

    @property
    def quote_asset(self) -> BrokerAsset:
        """
        quote asset, defined by pool info. It's the reference of asset0 or asset1

        :return: BrokerAsset
        :rtype: BrokerAsset
        """
        return self._quote_asset

    @property
    def pool_status(self) -> PoolStatus:
        """
        current pool status. will be writen by runner.

        :return: PoolStatus
        :rtype: PoolStatus
        """
        return self._pool_status

    @pool_status.setter
    def pool_status(self, value: PoolStatus):
        """
        current pool status. will be writen by runner.

        Do not update this property unless necessary

        :param value: current pool status
        :type value: PoolStatus
        """
        self._pool_status = value

    def position(self, position_info: PositionInfo) -> Position:
        """
        get position by position information

        :param position_info: position information
        :type position_info: PositionInfo
        :return: Position
        :rtype: Position
        """
        return self._positions[position_info]

    def __convert_pair(self, any0, any1):
        """
        convert order of token0/token1 to base_token/quote_token, according to self.is_token0_base.

        Or convert order of base_token/quote_token to token0/token1

        :param any0: token0 or any property of token0, eg. balance...
        :param any1: token1 or any property of token1, eg. balance...
        :return: (base,qoute) or (token0,token1)
        """
        return (any0, any1) if self._is_token0_base else (any1, any0)

    @float_param_formatter
    def set_asset(self, token: TokenInfo, amount: Union[Decimal, float]):
        """
        set initial balance for token

        :param token: which token to set
        :type token: TokenInfo
        :param amount: balance, eg: 1.2345
        :type amount: Union[Decimal, float]
        """
        if not self._pool_info:
            raise ZelosError("set up pool info first")
        if token == self._asset0.token_info:
            self._asset0.balance = amount
            self._init_amount0 = amount
        elif token == self._asset1.token_info:
            self._asset1.balance = amount
            self._init_amount1 = amount
        else:
            raise ZelosError("unknown token")

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
            V3CoreLib.update_fee(self.pool_info, position_info, position, self.pool_status)

    def get_init_account_status(self, init_price: Decimal, timestamp: datetime = None) -> AccountStatus:
        """
        Get initial status, which will be saved before running any test.

        :param timestamp: timestamp
        :type timestamp: datetime
        :param init_price: beginning price of testing, usually the price in the first item of data array
        :type init_price: Decimal
        :return: status
        :rtype: AccountStatus

        """
        base_init_amount, quote_init_amount = self.__convert_pair(self._init_amount0, self._init_amount1)
        capital = base_init_amount + quote_init_amount * init_price
        return AccountStatus(timestamp,
                             UnitDecimal(base_init_amount, self.base_asset.name),
                             UnitDecimal(quote_init_amount, self.quote_asset.name),
                             UnitDecimal(DECIMAL_ZERO, self.base_asset.name),
                             UnitDecimal(DECIMAL_ZERO, self.quote_asset.name),
                             UnitDecimal(DECIMAL_ZERO, self.base_asset.name),
                             UnitDecimal(DECIMAL_ZERO, self.quote_asset.name),
                             UnitDecimal(capital, self.base_asset.name),
                             UnitDecimal(init_price, self._price_unit))

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
        base_asset, quote_asset = self.__convert_pair(self._asset0, self._asset1)
        base_fee_sum = DECIMAL_ZERO
        quote_fee_sum = DECIMAL_ZERO
        tick = quote_price_to_tick(price, self.asset0.decimal, self.asset1.decimal, self._is_token0_base)
        deposit_amount0 = deposit_amount1 = Decimal(0)
        for position_info, position in self._positions.items():
            base_fee, quote_fee = self.__convert_pair(position.uncollected_fee_token0,
                                                      position.uncollected_fee_token1)
            base_fee_sum += base_fee
            quote_fee_sum += quote_fee
            amount0, amount1 = V3CoreLib.get_token_amounts(self._pool_info, position_info, tick)
            deposit_amount0 += amount0
            deposit_amount1 += amount1

        base_deposit_amount, quote_deposit_amount = self.__convert_pair(deposit_amount0, deposit_amount1)
        capital = (base_asset.balance + base_fee_sum + base_deposit_amount) + \
                  (quote_asset.balance + quote_fee_sum + quote_deposit_amount) * price
        base_init_amount, quote_init_amount = self.__convert_pair(self._init_amount0, self._init_amount1)

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
        return tick_to_quote_price(int(tick), self.pool_info.token0.decimal, self.pool_info.token1.decimal,
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
        return quote_price_to_tick(price, self.pool_info.token0.decimal, self.pool_info.token1.decimal,
                                   self._is_token0_base)

    def _add_liquidity_by_tick(self, token0_amount: Decimal,
                               token1_amount: Decimal,
                               lower_tick: int,
                               upper_tick: int,
                               current_tick=None):

        if current_tick is None:
            current_tick = int(self.pool_status.current_tick)  # self.current_tick must be initialed
        if lower_tick > upper_tick:
            raise ZelosError("lower tick should be less than upper tick")
        if token0_amount > self._asset0.balance:
            raise ZelosError("Insufficient token {} amount".format(self._asset0.name))
        if token1_amount > self._asset1.balance:
            raise ZelosError("Insufficient token {} amount".format(self._asset1.name))
        token0_used, token1_used, position_info = V3CoreLib.new_position(self._pool_info,
                                                                         token0_amount,
                                                                         token1_amount,
                                                                         lower_tick,
                                                                         upper_tick,
                                                                         current_tick)
        self._positions[position_info] = Position()
        self._asset0.sub(token0_used)
        self._asset1.sub(token1_used)
        return position_info, token0_used, token1_used

    def __remove_liquidity(self, position: PositionInfo):
        token0_get, token1_get = V3CoreLib.close_position(self._pool_info, position, self._positions[position],
                                                          self.pool_status.current_tick)
        del self._positions[position]
        # collect fee and token
        self._asset0.add(token0_get)
        self._asset1.add(token1_get)
        return token0_get, token1_get

    def __collect_fee(self, position: Position):
        token0_fee, token1_fee = position.uncollected_fee_token0, position.uncollected_fee_token1
        position.uncollected_fee_token0 = 0
        position.uncollected_fee_token1 = 0
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
                      quote_max_amount: Union[Decimal, float] = None) -> (PositionInfo, Decimal, Decimal):
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
        base_max_amount = self.base_asset.balance if base_max_amount is None else base_max_amount
        quote_max_amount = self.quote_asset.balance if quote_max_amount is None else quote_max_amount

        token0_amt, token1_amt = self.__convert_pair(base_max_amount, quote_max_amount)
        lower_tick, upper_tick = V3CoreLib.quote_price_pair_to_tick(self._pool_info, lower_quote_price,
                                                                    upper_quote_price)
        lower_tick, upper_tick = self.__convert_pair(upper_tick, lower_tick)
        (created_position, token0_used, token1_used) = self._add_liquidity_by_tick(token0_amt,
                                                                                   token1_amt,
                                                                                   lower_tick,
                                                                                   upper_tick,
                                                                                   self.pool_status.current_tick)
        base_used, quote_used = self.__convert_pair(token0_used, token1_used)
        self.action_buffer.append(AddLiquidityAction(UnitDecimal(self.base_asset.balance, self.base_asset.name),
                                                     UnitDecimal(self.quote_asset.balance, self.quote_asset.name),
                                                     UnitDecimal(base_max_amount, self.base_asset.name),
                                                     UnitDecimal(quote_max_amount, self.quote_asset.name),
                                                     UnitDecimal(lower_quote_price, self._price_unit),
                                                     UnitDecimal(upper_quote_price, self._price_unit),
                                                     UnitDecimal(base_used, self.base_asset.name),
                                                     UnitDecimal(quote_used, self.quote_asset.name),
                                                     created_position))
        return created_position, base_used, quote_used

    def remove_liquidity(self, positions: Union[PositionInfo, list]) -> {PositionInfo: (Decimal, Decimal)}:
        """
        remove liquidity from pool, position will be deleted

        :param positions: position info, as an object or an array
        :type positions: [PositionInfo]
        :return: a dict, key is position info, value is (base_got,quote_get), base_got is base token amount collected from position
        :rtype: {PositionInfo: (Decimal,Decimal)}
        """
        amount_dict = dict()
        position_list = positions if type(positions) is list else [positions, ]
        for position in position_list:
            token0_get, token1_get = self.__remove_liquidity(position)
            base_get, quote_get = self.__convert_pair(token0_get, token1_get)
            amount_dict[position] = (base_get, quote_get)
            self.action_buffer.append(
                RemoveLiquidityAction(
                    UnitDecimal(self.base_asset.balance, self.base_asset.name),
                    UnitDecimal(self.quote_asset.balance, self.quote_asset.name),
                    position,
                    UnitDecimal(base_get, self.base_asset.name),
                    UnitDecimal(quote_get, self.quote_asset.name)
                ))
        return amount_dict

    def collect_fee(self, positions: [PositionInfo]) -> {PositionInfo: tuple}:
        """
        collect fee from positions

        :param positions: position info, as an object or an array
        :type positions: [PositionInfo]
        :return: a dict, key is position info, value is (base_got,quote_get), base_got is base token fee collected from position
        :rtype: {Position: tuple(base_got,quote_get)}
        """
        amount_dict = dict()
        position_list = positions if type(positions) is list else [positions, ]
        for position in position_list:
            token0_get, token1_get = self.__collect_fee(self._positions[position])
            base_get, quote_get = self.__convert_pair(token0_get, token1_get)
            amount_dict[position] = (base_get, quote_get)
            self.action_buffer.append(
                CollectFeeAction(
                    UnitDecimal(self.base_asset.balance, self.base_asset.name),
                    UnitDecimal(self.quote_asset.balance, self.quote_asset.name),
                    position,
                    UnitDecimal(base_get, self.base_asset.name),
                    UnitDecimal(quote_get, self.quote_asset.name)
                ))
        return amount_dict

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
        from_amount_with_fee = from_amount * (1 + self.pool_info.fee_rate)
        fee = from_amount_with_fee - from_amount
        from_asset, to_asset = self.__convert_pair(self._asset0, self._asset1)
        from_asset.sub(from_amount_with_fee)
        to_asset.add(amount)
        base_amount, quote_amount = self.__convert_pair(from_amount, amount)
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
        from_amount = from_amount_with_fee * (1 - self.pool_info.fee_rate)
        to_amount = from_amount * price
        fee = from_amount_with_fee - from_amount
        to_asset, from_asset = self.__convert_pair(self._asset0, self._asset1)
        from_asset.sub(from_amount_with_fee)
        to_asset.add(to_amount)
        base_amount, quote_amount = self.__convert_pair(to_amount, from_amount)
        self.action_buffer.append(SellAction(UnitDecimal(self.base_asset.balance, self.base_asset.name),
                                             UnitDecimal(self.quote_asset.balance, self.quote_asset.name),
                                             UnitDecimal(amount, self.quote_asset.name),
                                             UnitDecimal(price, self._price_unit),
                                             UnitDecimal(fee, self.quote_asset.name),
                                             UnitDecimal(base_amount, self.base_asset.name),
                                             UnitDecimal(quote_amount, self.quote_asset.name)))

        return fee, base_amount, quote_amount
