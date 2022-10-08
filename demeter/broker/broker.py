from decimal import Decimal
from pandas import Series

from .._typing import PositionInfo, ZelosError, AddLiquidityAction, RemoveLiquidityAction, BuyAction, SellAction, \
    PositionAmount, CollectFeeAction, BarStatus, DECIMAL_ZERO, UnitDecimal
from ..utils.application import float_param_formatter

from .types import PoolBaseInfo, TokenInfo, BrokerAsset, Position, BarData
from .v3_core import V3CoreLib
from .helper import tick_to_quote_price, quote_price_to_tick


class Broker(object):
    # 稍后我把日志部分加进来

    def __init__(self, pool_info: PoolBaseInfo):
        self._pool_info = pool_info
        # 初始化资金
        self._is_token0_base = pool_info.is_token0_base
        self._asset0 = BrokerAsset(pool_info.token0, DECIMAL_ZERO)
        self._asset1 = BrokerAsset(pool_info.token1, DECIMAL_ZERO)
        base_asset, quote_asset = self.__convert_pair(self._asset0, self._asset1)
        self._base_asset = base_asset
        self._quote_asset = quote_asset
        self._init_amount0 = DECIMAL_ZERO
        self._init_amount1 = DECIMAL_ZERO
        # 状态
        self._positions: dict[PositionInfo:Position] = {}
        self._current_data = BarData(None, 0, DECIMAL_ZERO, DECIMAL_ZERO, DECIMAL_ZERO, DECIMAL_ZERO)
        self._price_unit = f"{self.base_asset.name}/{self.quote_asset.name}"
        # 临时变量
        self.action_buffer = []

    @property
    def positions(self) -> dict[PositionInfo:Position]:
        return self._positions

    @property
    def pool_info(self) -> PoolBaseInfo:
        return self._pool_info

    @property
    def asset1(self) -> BrokerAsset:
        return self._asset1

    @property
    def base_asset(self) -> BrokerAsset:
        return self._base_asset

    @property
    def quote_asset(self) -> BrokerAsset:
        return self._quote_asset

    @property
    def current_data(self) -> BarData:
        return self._current_data

    @current_data.setter
    def current_data(self, value):
        self._current_data = value

    @property
    def asset0(self) -> BrokerAsset:
        return self._asset0

    def position(self, position: PositionInfo) -> Position:
        return self._positions[position]

    def __convert_pair(self, any0, any1):
        """
        将token0/1的顺序, 根据is_token0_base调整为baseToken/quoteToken的顺序
        或者将baseToken/quoteToken的顺序, 调整为token0/1的顺序
        :param any0:
        :param any1:
        :return:
        """
        return (any0, any1) if self._is_token0_base else (any1, any0)

    @float_param_formatter
    def set_asset(self, token: TokenInfo, amount: Decimal):

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

    def update_on_bar(self, data_of_bar: Series):
        self.__update_fee()

    # region read方法
    def __update_fee(self):
        # 更新手续费
        # 模型: 仅仅根据提供流动性的多少来分成, 不考虑tick的宽度.
        for position_info, position in self._positions.items():
            V3CoreLib.update_fee(self.pool_info, position_info, position, self._current_data)

    def get_init_status(self, init_price):
        base_init_amount, quote_init_amount = self.__convert_pair(self._init_amount0, self._init_amount1)
        capital = base_init_amount + quote_init_amount * init_price
        return BarStatus(UnitDecimal(base_init_amount, self.base_asset.name),
                         UnitDecimal(quote_init_amount, self.quote_asset.name),
                         UnitDecimal(DECIMAL_ZERO, self.base_asset.name),
                         UnitDecimal(DECIMAL_ZERO, self.quote_asset.name),
                         UnitDecimal(DECIMAL_ZERO, self.base_asset.name),
                         UnitDecimal(DECIMAL_ZERO, self.quote_asset.name),
                         UnitDecimal(capital, self.base_asset.name),
                         UnitDecimal(init_price, self._price_unit),
                         UnitDecimal(Decimal(1), ""),
                         UnitDecimal(DECIMAL_ZERO, ""))

    def get_status(self, price) -> BarStatus:
        """
        获取当前状态, 包括仓位状态等
        :param price: 价格, 用于辅助计算净值. 为了和current_data解耦, 单独传入
        :return:
        """
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
        return BarStatus(UnitDecimal(base_asset.balance, self.base_asset.name),
                         UnitDecimal(quote_asset.balance, self.quote_asset.name),
                         UnitDecimal(base_fee_sum, self.base_asset.name),
                         UnitDecimal(quote_fee_sum, self.quote_asset.name),
                         UnitDecimal(base_deposit_amount, self.base_asset.name),
                         UnitDecimal(quote_deposit_amount, self.quote_asset.name),
                         UnitDecimal(capital, self.base_asset.name),
                         UnitDecimal(price, self._price_unit),
                         UnitDecimal(net_value, ""),
                         UnitDecimal(profit_pct, ""))

    def get_amount_in_position(self, position: PositionInfo):
        amount0, amount1 = V3CoreLib.get_token_amounts(self._pool_info, position, self._current_tick)
        return self.__convert_pair(amount0, amount1)

    # action to pool
    @float_param_formatter
    def tick_to_price(self, tick):
        return tick_to_quote_price(tick, self.pool_info.token0.decimal, self.pool_info.token1.decimal,
                                   self._is_token0_base)

    @float_param_formatter
    def price_to_tick(self, price):
        return quote_price_to_tick(price, self.pool_info.token0.decimal, self.pool_info.token1.decimal,
                                   self._is_token0_base)

    def __add_liquidity(self, token0_amount: Decimal,
                        token1_amount: Decimal,
                        lower_tick: int,
                        upper_tick: int,
                        current_tick=None):
        if current_tick is None:
            current_tick = int(self._current_tick)  # 记得初始化self.current_tick
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
                                                          self.current_data.current_tick)
        del self._positions[position]
        # collect fee and token
        self._asset0.add(token0_get)
        self._asset1.add(token1_get)
        return token0_get, token1_get

    # @float_param_formatter
    # def swap(self, from_asset: BrokerAsset, to_asset: BrokerAsset, from_amount: Decimal, price=None):
    #     fee = from_amount * self._pool_info.fee_rate
    #     from_amount_without_fee = from_amount - fee
    #     to_amount = price * from_amount_without_fee
    #     from_asset.sub(from_amount)
    #     to_asset.add(to_amount)
    #     return fee, from_amount, to_amount

    def __collect_fee(self, position: Position):
        token0_fee, token1_fee = position.uncollected_fee_token0, position.uncollected_fee_token1
        position.uncollected_fee_token0 = 0
        position.uncollected_fee_token1 = 0
        # 手续费金额添加到现在的余额中
        self._asset0.add(token0_fee)
        self._asset1.add(token1_fee)
        return token0_fee, token1_fee

    # action for strategy

    @float_param_formatter
    def add_liquidity(self, base_max_amount, quote_max_amount, lower_quote_price, upper_quote_price):
        token0_amt, token1_amt = self.__convert_pair(base_max_amount, quote_max_amount)
        lower_tick, upper_tick = V3CoreLib.quote_price_pair_to_tick(self._pool_info, lower_quote_price,
                                                                    upper_quote_price)
        lower_tick, upper_tick = self.__convert_pair(upper_tick, lower_tick)
        (created_position, token0_used, token1_used) = self.__add_liquidity(token0_amt,
                                                                            token1_amt,
                                                                            lower_tick,
                                                                            upper_tick,
                                                                            self.current_data.current_tick)
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

    def remove_liquidity(self, positions: [PositionInfo]):
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

    def collect_fee(self, positions: [PositionInfo]):
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
    def buy(self, amount: Decimal | float, price: Decimal | float = None):
        """

        :param amount:
        :param price:
        :return:
            fee:
            base_token_used
            quote_token_get
        """
        price = price if price else self.current_data.price
        from_amount = price * amount
        from_amount_with_fee = from_amount * (1 + self.pool_info.fee_rate)
        fee = from_amount_with_fee - from_amount
        from_asset, to_asset = self.__convert_pair(self._asset0, self._asset1)
        # if 0 is token base: buy => token 0 -> token 1
        # None 无滑点current 成交，收手续费
        # price 则视为limit order book,，可能部分成交？
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
    def sell(self, amount: Decimal | float, price: Decimal | float = None):
        """

        :param amount:
        :param price:
        :return:
            fee:
            base_token_get
            quote_token_used
        """
        # None 无滑点current 成交，收手续费
        # price 则视为limit order book,，可能部分成交？
        # TODO 写swap的时候, 没感觉有部分成交这回事啊
        price = price if price else self.current_data.price
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

    # 这里定义了哪些函数会暴露给策略对象
    expose_methods = {
        "add_liquidity": add_liquidity,
        "remove_liquidity": remove_liquidity,
        "buy": buy,
        "sell": sell,
        "collect_fee": collect_fee
    }
