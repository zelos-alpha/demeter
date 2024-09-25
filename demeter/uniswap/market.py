import numpy as np
import os
import pandas as pd
from datetime import date, timedelta, datetime, time
from decimal import Decimal
from typing import Dict, Tuple
import orjson
from ._typing import (
    UniV3Pool,
    TokenInfo,
    Position,
    UniLpBalance,
    AddLiquidityAction,
    RemoveLiquidityAction,
    CollectFeeAction,
    BuyAction,
    SellAction,
    position_dict_to_dataframe,
    PositionInfo,
    UniDescription,
    UniswapMarketStatus,
    SwapAction,
)
from .core import V3CoreLib
from .data import fillna, resample
from .helper import (
    tick_to_base_unit_price,
    base_unit_price_to_tick,
    base_unit_price_to_sqrt_price_x96,
    tick_to_sqrt_price_x96,
    get_swap_value_with_part_balance_used,
    MIN_ERROR,
    nearest_usable_tick,
    sqrt_price_x96_to_tick,
)
from .liquitidy_math import (
    get_sqrt_ratio_at_tick,
    estimate_ratio,
    get_liquidity,
    get_liquidity_for_amount0,
    get_liquidity_for_amount1,
)
from .._typing import DemeterError, DECIMAL_0, UnitDecimal
from ..broker import MarketBalance, Market, MarketInfo, write_func
from ..utils import (
    get_formatted_from_dict,
    get_formatted_predefined,
    STYLE,
    float_param_formatter,
    to_decimal,
    require,
)


class UniLpMarket(Market):
    """
    | UniLpMarket is the simulator of uniswap v3, it can simulate transactions such as add/remove liquidity, swap assets. and calculate position net value
    | UniLpMarket corresponds to a pool on chain, which means a token pair in a chain.

    :param market_info: key of this market
    :type market_info: MarketInfo
    :param pool_info: Uniswap v3 pool info
    :type pool_info: UniV3Pool
    :param data: pool data for back test. downloaded by demeter-fetch
    :type data: pd.DataFrame
    :param data_path: path to load pool data
    :type data_path: str
    """

    def __init__(
        self, market_info: MarketInfo, pool_info: UniV3Pool, data: pd.DataFrame = None, data_path: str = "./data"
    ):
        super().__init__(market_info=market_info, data=data, data_path=data_path)
        self._pool: UniV3Pool = pool_info
        # init balance
        self._is_token0_quote = pool_info.is_token0_quote
        # reference for super().assets dict.
        self.base_token, self.quote_token = self._convert_pair(self.pool_info.token0, self.pool_info.token1)
        # status
        self._positions: Dict[PositionInfo, Position] = {}
        # In order to distinguish price in pool and to u, we call former one "pool price"
        self._pool_price_unit = f"{self.base_token.name}/{self.quote_token.name}"
        # internal temporary variable
        # self.action_buffer = []
        # tick of last minute(previous minute), to compatible with old version, keep default as None
        self.last_tick: int = None

    # region properties

    def __str__(self):
        from demeter.utils import orjson_default

        return orjson.dumps(self.description, default=orjson_default).decode()

    @property
    def description(self) -> UniDescription:
        return UniDescription(
            type=type(self).__name__,
            name=self._market_info.name,
            token0=self.pool_info.token0,
            token1=self.pool_info.token1,
            quote_token=self.pool_info.quote_token,
            base_token=(
                self.pool_info.token0 if self.pool_info.quote_token == self.pool_info.token1 else self.pool_info.token1
            ),
            fee_rate=self.pool_info.fee_rate,
        )

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

    @property
    def market_status(self) -> UniswapMarketStatus:
        return self._market_status

    # endregion

    def get_position(self, position_info: PositionInfo) -> Position:
        """
        get get_position by get_position information

        :param position_info: get_position information
        :type position_info: PositionInfo
        :return: Position entity
        :rtype: Position
        """
        return self._positions[position_info]

    def set_market_status(
        self,
        market_status: UniswapMarketStatus | None,
        price: pd.Series | None,
    ):
        """
        Set current pool status (total liquidity, price etc.) to Market

        | Note: UniswapMarketStatus also have price attribute, but it's different price parameter.
        | price parameter is used to evaluate token value. Often get from coingecko
        | UniswapMarketStatus.price is the relative price of pool token pair. It's calculated from pool swap events.
        | if base token in pool is stable coin and its price is 1, the two price will be the same. But if stable coin price is not 1, there will be a gap between two prices.

        :param market_status: market data
        :type market_status: UniswapMarketStatus
        :param price: price of token at this moment
        :type price: pd.Series
        """
        # update price tick
        super().set_market_status(market_status, price)

        total_virtual_liq = sum([p.liquidity for p in self._positions.values()])
        self.last_tick = self._market_status.data.closeTick if "closeTick" in self._market_status.data.index else np.nan

        if market_status.data is None:
            market_status.data = self.data.loc[market_status.timestamp].copy()
        market_status.data.currentLiquidity = market_status.data.currentLiquidity + total_virtual_liq
        self._market_status = market_status

    def get_price_from_data(self) -> Tuple[pd.DataFrame, TokenInfo]:
        """
        Extract token pair price from pool data.

        :return: a dataframe includes quote token price, and quote token price will be set to 1
        :rtype: Tuple[pd.DataFrame, TokenInfo]

        """
        if self.data is None:
            raise DemeterError("data has not set")
        price_series: pd.Series = self.data.price
        df = pd.DataFrame(index=price_series.index, data={self.base_token.name: price_series})
        df[self.quote_token.name] = 1
        return df, self.quote_token

    def _convert_pair(self, any0, any1):
        """
        convert order of token0/token1 to base_token/quote_token, according to self.is_token0_quote.

        Or convert order of base_token/quote_token to token0/token1

        :param any0: token0 or any property of token0, e.g. balance...
        :param any1: token1 or any property of token1, e.g. balance...
        :return: (base,qoute) or (token0,token1)
        """
        return (any1, any0) if self._is_token0_quote else (any0, any1)

    def check_market(self):
        """
        Verify settings before backtest
        """
        super().check_market()
        required_columns = [
            "closeTick",
            "currentLiquidity",
            "inAmount0",
            "inAmount1",
            "price",
        ]
        for col in required_columns:
            assert col in self.data.columns

        if not self._pool:
            raise DemeterError("set up pool info first")
        if self.base_token not in self.broker.assets:
            self.broker.set_balance(self.base_token, DECIMAL_0)
        if self.quote_token not in self.broker.assets:
            self.broker.set_balance(self.quote_token, DECIMAL_0)

    def update(self):
        """
        re-calculate status.
        """
        self.__update_fee()

    def __update_fee(self):
        """
        update fee in all positions according to current status

        fee will be calculated by liquidity
        """
        for position_info, position in self._positions.items():
            V3CoreLib.update_fee(self.last_tick, self.pool_info, position_info, position, self.market_status.data)

    def get_position_amount(self, position_info: PositionInfo) -> Tuple[Decimal, Decimal]:
        if position_info not in self.positions:
            return DECIMAL_0, DECIMAL_0
        pool_price = self._market_status.data.price
        sqrt_price = base_unit_price_to_sqrt_price_x96(
            pool_price,
            self._pool.token0.decimal,
            self._pool.token1.decimal,
            self._is_token0_quote,
        )
        position = self.positions[position_info]
        amount0, amount1 = V3CoreLib.get_token_amounts(self._pool, position_info, sqrt_price, position.liquidity)
        return amount0, amount1

    def get_market_balance(self) -> MarketBalance:
        """
        get current status, including positions, balances

        :return: MarketBalance
        """
        pool_price = {self.quote_token.name: Decimal(1), self.base_token.name: self._market_status.data.price}

        sqrt_price = base_unit_price_to_sqrt_price_x96(
            self._market_status.data.price,
            self._pool.token0.decimal,
            self._pool.token1.decimal,
            self._is_token0_quote,
        )
        base_fee_sum = Decimal(0)
        quote_fee_sum = Decimal(0)
        deposit_amount0 = Decimal(0)
        deposit_amount1 = Decimal(0)
        for position_info, position in self._positions.items():
            if position.transferred:
                continue
            base_fee, quote_fee = self._convert_pair(position.pending_amount0, position.pending_amount1)
            base_fee_sum += base_fee
            quote_fee_sum += quote_fee
            amount0, amount1 = V3CoreLib.get_token_amounts(self._pool, position_info, sqrt_price, position.liquidity)
            deposit_amount0 += amount0
            deposit_amount1 += amount1

        base_deposit_amount, quote_deposit_amount = self._convert_pair(deposit_amount0, deposit_amount1)

        net_value = (base_fee_sum + base_deposit_amount) * pool_price[self.base_token.name] + (
            quote_fee_sum + quote_deposit_amount
        ) * pool_price[self.quote_token.name]

        val = UniLpBalance(
            net_value=net_value,
            base_uncollected=UnitDecimal(base_fee_sum, self.base_token.name),
            quote_uncollected=UnitDecimal(quote_fee_sum, self.quote_token.name),
            base_in_position=UnitDecimal(base_deposit_amount, self.base_token.name),
            quote_in_position=UnitDecimal(quote_deposit_amount, self.quote_token.name),
            position_count=len(list(filter(lambda p: not p.transferred, self._positions.values()))),
        )
        return val

    def transfer_position_out(self, position_info: PositionInfo):
        if position_info in self.positions and not self.positions[position_info].transferred:
            self.positions[position_info].transferred = True
        else:
            raise DemeterError("position not exist or has transferred out ")

    def transfer_position_in(self, position_info: PositionInfo):
        if position_info in self.positions and self.positions[position_info].transferred:
            self.positions[position_info].transferred = False
        else:
            raise DemeterError("position not exist or has not transferred yet ")

    def tick_to_price(self, tick: int) -> Decimal:
        """
        convert tick to price

        :param tick: tick
        :type tick: int
        :return: price
        :rtype: Decimal
        """
        return tick_to_base_unit_price(
            int(tick),
            self._pool.token0.decimal,
            self._pool.token1.decimal,
            self._is_token0_quote,
        )

    def estimate_liquidity(self, value: Decimal, position: PositionInfo) -> Tuple[int, Decimal, Decimal]:
        """
        In the current market situation, to obtain value (e.g. 500 usd) from this tick range, how many liquidity units need to be removed?

        :param value: value to get (e.g. 500 usd)
        :param position: LP position
        :return: Liquidity and how much token amount you can get if remove liquidity.
        """
        sqrt_price_x96 = base_unit_price_to_sqrt_price_x96(
            self.market_status.data.price,
            self.pool_info.token0.decimal,
            self.pool_info.token1.decimal,
            self.pool_info.is_token0_quote,
        )
        current_tick = sqrt_price_x96_to_tick(sqrt_price_x96)

        lower_sqrt = get_sqrt_ratio_at_tick(position.lower_tick)
        upper_sqrt = get_sqrt_ratio_at_tick(position.upper_tick)
        if current_tick <= position.lower_tick:
            quote_amount = DECIMAL_0
            base_amount = value / Decimal(self.market_status.data.price)
            liq = int(get_liquidity_for_amount0(lower_sqrt, upper_sqrt, base_amount * 10**self.base_token.decimal))
            token0_amount, token1_amount = self._convert_pair(base_amount, quote_amount)

        elif current_tick >= position.upper_tick:
            quote_amount = value
            base_amount = DECIMAL_0
            liq = int(get_liquidity_for_amount1(lower_sqrt, upper_sqrt, quote_amount * 10**self.quote_token.decimal))
            token0_amount, token1_amount = self._convert_pair(base_amount, quote_amount)
        else:
            token0_amount, token1_amount = self.estimate_amount(value, position.lower_tick, position.upper_tick)
            liq = get_liquidity(
                sqrt_price_x96,
                position.lower_tick,
                position.upper_tick,
                token0_amount,
                token1_amount,
                self.pool_info.token0.decimal,
                self.pool_info.token1.decimal,
            )

        return liq, token0_amount, token1_amount

    def estimate_amount(self, value: Decimal, lower_tick: int, upper_tick: int) -> Tuple[Decimal, Decimal]:
        """
        Emulate amount of token 0,1 with given tick range

        :param value: value to get (e.g. 500 usd)
        :param lower_tick: lower tick
        :param upper_tick: upper tick
        :return:
        """
        current_price = self.market_status.data.price
        current_tick = base_unit_price_to_tick(
            current_price, self.pool_info.token0.decimal, self.pool_info.token1.decimal, self.pool_info.is_token0_quote
        )
        ratio_in_amount = estimate_ratio(current_tick, lower_tick, upper_tick)
        ratio_in_amount = Decimal(
            ratio_in_amount * 10 ** (self.pool_info.token1.decimal - self.pool_info.token0.decimal)
        )
        ratio_in_value = (
            ratio_in_amount / current_price if self.pool_info.is_token0_quote else ratio_in_amount * current_price
        )
        token1_value = value / (ratio_in_value + 1)
        token0_value = value - token1_value
        token0_amount = token0_value if self.pool_info.is_token0_quote else token0_value / current_price
        token1_amount = token1_value if not self.pool_info.is_token0_quote else token1_value / current_price
        return token0_amount, token1_amount

    @float_param_formatter
    def price_to_tick(self, price: Decimal | float) -> int:
        """
        convert price to tick

        :param price: price
        :type price:  Decimal | float
        :return: tick
        :rtype: int
        """
        return nearest_usable_tick(
            base_unit_price_to_tick(
                price,
                self._pool.token0.decimal,
                self._pool.token1.decimal,
                self._is_token0_quote,
            ),
            self.pool_info.tick_spacing,
        )

    @write_func
    def _add_liquidity_by_tick(
        self,
        token0_amount: Decimal,
        token1_amount: Decimal,
        lower_tick: int,
        upper_tick: int,
        sqrt_price_x96: int = -1,
    ):
        lower_tick = int(lower_tick)
        upper_tick = int(upper_tick)
        require(
            lower_tick % self.pool_info.tick_spacing == 0 and upper_tick % self.pool_info.tick_spacing == 0,
            "tick should match tick space",
        )
        sqrt_price_x96 = int(sqrt_price_x96)

        if sqrt_price_x96 == -1:
            # self.current_tick must be initialed
            sqrt_price_x96 = get_sqrt_ratio_at_tick(self.market_status.data.closeTick)
        if lower_tick > upper_tick:
            raise DemeterError("lower tick should be less than upper tick")

        token0_used, token1_used, liquidity, position_info = V3CoreLib.new_position(
            self._pool,
            token0_amount,
            token1_amount,
            lower_tick,
            upper_tick,
            sqrt_price_x96,
        )
        if position_info in self._positions:
            self._positions[position_info].liquidity += liquidity
        else:
            lower_price = self.tick_to_price(lower_tick)
            upper_price = self.tick_to_price(upper_tick)
            if self.pool_info.is_token0_quote:
                lower_price, upper_price = upper_price, lower_price
            self._positions[position_info] = Position(DECIMAL_0, DECIMAL_0, liquidity, lower_price, upper_price)
        self.broker.subtract_from_balance(self.token0, token0_used)
        self.broker.subtract_from_balance(self.token1, token1_used)
        return position_info, token0_used, token1_used, liquidity

    @write_func
    def __remove_liquidity(self, position: PositionInfo, liquidity: int = None, sqrt_price_x96: int = -1):
        sqrt_price_x96 = (
            int(sqrt_price_x96)
            if sqrt_price_x96 != -1
            else base_unit_price_to_sqrt_price_x96(
                self.market_status.data.price,
                self.pool_info.token0.decimal,
                self.pool_info.token1.decimal,
                self.pool_info.is_token0_quote,
            )
        )
        delta_liquidity = (
            liquidity
            if (liquidity is not None) and liquidity < self.positions[position].liquidity
            else self.positions[position].liquidity
        )
        token0_get, token1_get = V3CoreLib.close_position(self._pool, position, delta_liquidity, sqrt_price_x96)

        self._positions[position].liquidity = self.positions[position].liquidity - delta_liquidity
        self._positions[position].pending_amount0 += token0_get
        self._positions[position].pending_amount1 += token1_get

        return token0_get, token1_get, delta_liquidity

    @write_func
    def __collect_fee(
        self,
        position: Position,
        max_collect_amount0: Decimal = None,
        max_collect_amount1: Decimal = None,
        collect_to_user: bool = True,
    ):
        """
        Collect fee

        :param position: get_position
        :param max_collect_amount0: max collect amount0
        :param max_collect_amount1: max collect amount1
        :param collect_to_user: Transfer collected token to user balance, default is true
        :return:
        """
        token0_fee = (
            max_collect_amount0
            if max_collect_amount0 is not None and max_collect_amount0 < position.pending_amount0
            else position.pending_amount0
        )
        token1_fee = (
            max_collect_amount1
            if max_collect_amount1 is not None and max_collect_amount1 < position.pending_amount1
            else position.pending_amount1
        )

        position.pending_amount0 -= token0_fee
        position.pending_amount1 -= token1_fee
        # add un_collect fee to current balance
        if collect_to_user:
            self.broker.add_to_balance(self.token0, token0_fee)
            self.broker.add_to_balance(self.token1, token1_fee)
        return token0_fee, token1_fee

    # action for strategy

    @float_param_formatter
    def add_liquidity(
        self,
        lower_quote_price: Decimal | float,
        upper_quote_price: Decimal | float,
        quote_max_amount: Decimal | float = None,
        base_max_amount: Decimal | float = None,
    ) -> (PositionInfo, Decimal, Decimal, int):
        """

        add liquidity, then get a new get_position

        :param lower_quote_price: lower price base on quote token.
        :type lower_quote_price: Decimal | float
        :param upper_quote_price: upper price base on quote token.
        :type upper_quote_price: Decimal | float
        :param base_max_amount:  inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type base_max_amount: Decimal | float
        :param quote_max_amount: inputted base token amount, also the max amount to deposit, if is None, will use all the balance of base token
        :type quote_max_amount: Decimal | float
        :return: added get_position, base token used, quote token used
        :rtype: (PositionInfo, Decimal, Decimal)
        """
        base_max_amount = self.broker.get_token_balance(self.base_token) if base_max_amount is None else base_max_amount
        quote_max_amount = (
            self.broker.get_token_balance(self.quote_token) if quote_max_amount is None else quote_max_amount
        )

        token0_amt, token1_amt = self._convert_pair(base_max_amount, quote_max_amount)
        lower_tick, upper_tick = V3CoreLib.quote_price_pair_to_tick(self._pool, lower_quote_price, upper_quote_price)
        lower_tick = nearest_usable_tick(lower_tick, self.pool_info.tick_spacing)
        upper_tick = nearest_usable_tick(upper_tick, self.pool_info.tick_spacing)
        # lower_tick, upper_tick = self._convert_pair(upper_tick, lower_tick)
        (
            created_position,
            token0_used,
            token1_used,
            liquidity,
        ) = self._add_liquidity_by_tick(token0_amt, token1_amt, lower_tick, upper_tick)
        base_used, quote_used = self._convert_pair(token0_used, token1_used)
        self._record_action(
            AddLiquidityAction(
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
                liquidity=int(liquidity),
            )
        )
        return created_position, base_used, quote_used, liquidity

    def add_liquidity_by_tick(
        self,
        lower_tick: int,
        upper_tick: int,
        base_max_amount: Decimal | float = None,
        quote_max_amount: Decimal | float = None,
        sqrt_price_x96: int = -1,
        tick: int = -1,
        trim_tick: bool = True,
    ) -> (PositionInfo, Decimal, Decimal, int):
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
        :param trim_tick: trim tick according to tick spacing, default is True
        :type trim_tick: bool
        :return: added get_position, base token used, quote token used, liquidity
        :rtype: (PositionInfo, Decimal, Decimal, int)
        """
        if trim_tick:
            lower_tick = nearest_usable_tick(lower_tick, self.pool_info.tick_spacing)
            upper_tick = nearest_usable_tick(upper_tick, self.pool_info.tick_spacing)

        if lower_tick > upper_tick:
            lower_tick, upper_tick = upper_tick, lower_tick

        if sqrt_price_x96 == -1 and tick != -1:
            sqrt_price_x96 = tick_to_sqrt_price_x96(tick)

        base_max_amount = self.broker.get_token_balance(self.base_token) if base_max_amount is None else base_max_amount
        quote_max_amount = (
            self.broker.get_token_balance(self.quote_token) if quote_max_amount is None else quote_max_amount
        )

        token0_amt, token1_amt = self._convert_pair(base_max_amount, quote_max_amount)
        (
            created_position,
            token0_used,
            token1_used,
            liquidity,
        ) = self._add_liquidity_by_tick(token0_amt, token1_amt, lower_tick, upper_tick, sqrt_price_x96)
        base_used, quote_used = self._convert_pair(token0_used, token1_used)
        self._record_action(
            AddLiquidityAction(
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
                liquidity=int(liquidity),
            )
        )
        return created_position, base_used, quote_used, liquidity

    @float_param_formatter
    def remove_liquidity(
        self,
        position: PositionInfo,
        liquidity: int = None,
        collect: bool = True,
        sqrt_price_x96: int = -1,
        remove_dry_pool: bool = True,
    ) -> (Decimal, Decimal):
        """
        | remove liquidity from the pool. Liquidity will be reduced to 0,
        | instead of send tokens to broker, tokens will be transferred to fee property in get_position.
        | get_position will be not deleted, until fees and tokens are collected.

        :param position: get_position to remove.
        :type position: PositionInfo
        :param liquidity: liquidity amount to remove, if set to None, all the liquidity will be removed
        :type liquidity: int
        :param collect: collect or not, if collect, will call collect function. and tokens will be sent to broker. if not, token will be kept in fee property of postion
        :type collect: bool
        :param sqrt_price_x96: precise price.  if set to none, it will be calculated from current price.
        :type sqrt_price_x96: int
        :param remove_dry_pool: remove pool which liquidity==0, effect when collect==True
        :type remove_dry_pool: bool
        :return: (base_got,quote_get), base and quote token amounts collected from get_position
        :rtype:  (Decimal,Decimal)
        """
        if liquidity and liquidity < 0:
            raise DemeterError("liquidity should large than 0")
        token0_get, token1_get, delta_liquidity = self.__remove_liquidity(position, liquidity, sqrt_price_x96)

        base_get, quote_get = self._convert_pair(token0_get, token1_get)
        self._record_action(
            RemoveLiquidityAction(
                market=self.market_info,
                base_balance_after=self.broker.get_token_balance_with_unit(self.base_token),
                quote_balance_after=self.broker.get_token_balance_with_unit(self.quote_token),
                position=position,
                base_amount=UnitDecimal(base_get, self.base_token.name),
                quote_amount=UnitDecimal(quote_get, self.quote_token.name),
                removed_liquidity=delta_liquidity,
                remain_liquidity=self.positions[position].liquidity,
            )
        )
        if collect:
            return self.collect_fee(position, remove_dry_pool=remove_dry_pool)
        else:
            return base_get, quote_get

    @float_param_formatter
    def collect_fee(
        self,
        position: PositionInfo,
        max_collect_amount0: Decimal = None,
        max_collect_amount1: Decimal = None,
        remove_dry_pool: bool = True,
        collect_to_user: bool = True,
    ) -> (Decimal, Decimal):
        """
        | collect fee and token from positions,
        | if the amount and liquidity is zero, this get_position will be deleted.

        :param position: get_position to collect
        :type position: PositionInfo
        :param max_collect_amount0: max token0 amount to collect, e.g. 1.2345 usdc, if set to None, all the amount will be collect
        :type max_collect_amount0: Decimal
        :param max_collect_amount1: max token0 amount to collect, if set to None, all the amount will be collect
        :type max_collect_amount1: Decimal
        :param remove_dry_pool: remove pool which liquidity==0, effect when collect==True
        :type remove_dry_pool: bool
        :param collect_to_user: Transfer collected token to user balance, default is true
        :type collect_to_user: bool
        :return: (base_got,quote_get), base and quote token amounts collected from get_position
        :rtype:  (Decimal,Decimal)
        """
        if (max_collect_amount0 and max_collect_amount0 < 0) or (max_collect_amount1 and max_collect_amount1 < 0):
            raise DemeterError("collect amount should large than 0")
        token0_get, token1_get = self.__collect_fee(
            self._positions[position], max_collect_amount0, max_collect_amount1, collect_to_user
        )

        base_get, quote_get = self._convert_pair(token0_get, token1_get)
        if self._positions[position]:
            self._record_action(
                CollectFeeAction(
                    market=self.market_info,
                    base_balance_after=self.broker.get_token_balance_with_unit(self.base_token),
                    quote_balance_after=self.broker.get_token_balance_with_unit(self.quote_token),
                    position=position,
                    base_amount=UnitDecimal(base_get, self.base_token.name),
                    quote_amount=UnitDecimal(quote_get, self.quote_token.name),
                )
            )
        if (
            self._positions[position].pending_amount0 == Decimal(0)
            and self._positions[position].pending_amount1 == Decimal(0)
            and self._positions[position].liquidity == 0
            and remove_dry_pool
        ):
            del self.positions[position]
        return base_get, quote_get

    @float_param_formatter
    def swap(
        self,
        from_amount: Decimal | float,
        from_token: TokenInfo,
        to_token: TokenInfo,
        price: Decimal | float = None,
        throw_action=True,
    ):
        if from_token == to_token:
            raise DemeterError("from and to token can not same")
        if from_token not in [self.quote_token, self.base_token] or to_token not in [self.quote_token, self.base_token]:
            raise DemeterError("from or to token not in pool")

        if from_token == self.base_token:
            # e.g. swap 1 eth for 3000 usdc
            price = price if price else self.market_status.data.price
        else:
            # e.g. swap 3000 usdc for 1 eth
            price = price if price else 1 / self.market_status.data.price
        fee_in_from = from_amount * self.pool_info.fee_rate
        to_amount = (from_amount - fee_in_from) * price
        self.broker.subtract_from_balance(from_token, from_amount)
        self.broker.add_to_balance(to_token, to_amount)
        if throw_action:
            self._record_action(
                SwapAction(
                    market=self.market_info,
                    amount=UnitDecimal(from_amount, from_token.name),
                    price=UnitDecimal(price, f"{from_token.name}/{to_token.name}"),
                    fee=UnitDecimal(fee_in_from, from_token.name),
                    to_amount=UnitDecimal(to_amount, to_token.name),
                )
            )
        return fee_in_from, to_amount

    @float_param_formatter
    def buy(self, base_token_amount: Decimal | float, price: Decimal | float = None) -> (Decimal, Decimal, Decimal):
        """
        buy base token, swap from quote token to base token.

        :param base_token_amount: amount to buy(in base token)
        :type base_token_amount:  Decimal | float
        :param price: price in base/quote, e.g. 1234 eth/usdc, if leave to None, will use pool price
        :type price: Decimal | float
        :return: fee in base token, quote token amount spend, base token amount got
        :rtype: (Decimal, Decimal, Decimal)
        """
        if base_token_amount == 0:
            return DECIMAL_0, DECIMAL_0, DECIMAL_0
        price = price if price else self.market_status.data.price
        quote_amount_with_fee = base_token_amount * price / (1 - self._pool.fee_rate)
        fee_in_quote, base_amount_got = self.swap(
            quote_amount_with_fee, self.quote_token, self.base_token, 1 / price, False
        )
        self._record_action(
            BuyAction(
                market=self.market_info,
                base_balance_after=self.broker.get_token_balance_with_unit(self.base_token),
                quote_balance_after=self.broker.get_token_balance_with_unit(self.quote_token),
                amount=UnitDecimal(base_token_amount, self.base_token.name),
                price=UnitDecimal(price, self._pool_price_unit),
                fee=UnitDecimal(fee_in_quote, self.quote_token.name),
                base_change=UnitDecimal(base_amount_got, self.base_token.name),
                quote_change=UnitDecimal(quote_amount_with_fee, self.quote_token.name),
            )
        )
        return fee_in_quote, quote_amount_with_fee, base_amount_got

    @float_param_formatter
    def sell(self, base_token_amount: Decimal | float, price: Decimal | float = None) -> (Decimal, Decimal, Decimal):
        """
        Sell base token, swap from base token to quote token.

        :param base_token_amount: amount to sell(in base token)
        :type base_token_amount:  Decimal | float
        :param price: price, e.g. 1234 eth/usdc, if leave to None, will use pool price
        :type price: Decimal | float
        :return: fee in quote token, base token amount spend, quote token amount got
        :rtype: (Decimal, Decimal, Decimal)
        """
        if base_token_amount == 0:
            return DECIMAL_0, DECIMAL_0, DECIMAL_0
        price = price if price else self.market_status.data.price

        fee_in_base, quote_amount_got = self.swap(base_token_amount, self.base_token, self.quote_token, price, False)

        self._record_action(
            SellAction(
                market=self.market_info,
                base_balance_after=self.broker.get_token_balance_with_unit(self.base_token),
                quote_balance_after=self.broker.get_token_balance_with_unit(self.quote_token),
                amount=UnitDecimal(base_token_amount, self.base_token.name),
                price=UnitDecimal(price, self._pool_price_unit),
                fee=UnitDecimal(fee_in_base, self.base_token.name),
                base_change=UnitDecimal(base_token_amount, self.base_token.name),
                quote_change=UnitDecimal(quote_amount_got, self.quote_token.name),
            )
        )

        return fee_in_base, base_token_amount, quote_amount_got

    def add_liquidity_by_value(
        self, lower_tick: int, upper_tick: int, value_to_use: Decimal | None = None, trim_tick: bool = True
    ) -> (PositionInfo, Decimal, Decimal, int):
        """
        Add liquidity from balance with value defined, and swap if necessary.
        e.g. you have 1 eth and 3000 usdc, and eth price is 1000. If you want to invest at 1:1,
        you have to swap 1000 usdc to eth, so your balance will be 2 eth and 2000 usdc, but swap fee is not counted.
        this function will calculate the best swap amount(1005.025, if fee is 1%),
        which will make the balance at: 1.99975 eth and 1994.975 usdc, which is just 1:1, So all balance will be used.
        This function to free you from complex calculation.


        :param lower_tick: lower tick
        :type lower_tick: int
        :param upper_tick: upper tick
        :type upper_tick: int
        :param trim_tick: trim tick according to tick spacing, default is True
        :type trim_tick: bool
        :param value_to_use: Value you want to add liquidity(in quote token). Actual value used would be less than this value because swap fee might be charged.
        :return: added get_position, base token used, quote token used, liquidity
        :rtype: (PositionInfo, Decimal, Decimal, int)
        """
        if trim_tick:
            lower_tick = nearest_usable_tick(lower_tick, self.pool_info.tick_spacing)
            upper_tick = nearest_usable_tick(upper_tick, self.pool_info.tick_spacing)
        price = self._market_status.data.price
        tick = self._market_status.data.closeTick
        price0, price1 = self._convert_pair(price, Decimal(1))

        quote_balance = self.broker.get_token_balance(self.quote_token)
        base_balance_value = self.broker.get_token_balance(self.base_token) * price

        balance = quote_balance + base_balance_value

        if value_to_use is None:
            value_to_use = balance

        if value_to_use > balance:
            raise DemeterError("Not enough balance to add liquidity")
        if lower_tick >= upper_tick:
            raise DemeterError("Lower tick is larger than upper tick")

        # price is greater than upper price
        if (self._is_token0_quote and tick > upper_tick) or (not self._is_token0_quote and tick < lower_tick):
            # all base
            base_amount = value_to_use / self._market_status.data.price
            diff = base_amount - self.broker.get_token_balance(self.base_token)
            fee_in_quote = Decimal(0)
            if diff > MIN_ERROR:
                fee_in_quote, to_amount = self.swap(diff * price, self.quote_token, self.base_token)
            return self.add_liquidity_by_tick(lower_tick, upper_tick, base_amount - fee_in_quote / price, Decimal(0))

        # price is lower than upper price
        if (self._is_token0_quote and tick < lower_tick) or (not self._is_token0_quote and tick > upper_tick):
            # all quote
            diff = value_to_use - self.broker.get_token_balance(self.quote_token)
            fee_in_base = Decimal(0)
            if diff > 0:
                fee_in_base, quote_got = self.swap(diff / price, self.base_token, self.quote_token)
            return self.add_liquidity_by_tick(lower_tick, upper_tick, Decimal(0), value_to_use - fee_in_base * price)

        # price is in tick range

        ratio = estimate_ratio(tick, lower_tick, upper_tick)
        ratio_in_amount = ratio * 10 ** (self.pool_info.token1.decimal - self.pool_info.token0.decimal)
        ratio_in_value = Decimal(ratio_in_amount) / price if self._is_token0_quote else Decimal(ratio_in_amount) * price

        token1_value = value_to_use / (ratio_in_value + 1)
        token0_value = value_to_use - token1_value
        balance0_value = self.broker.get_token_balance(self.token0) * price0
        balance1_value = self.broker.get_token_balance(self.token1) * price1
        if token0_value <= balance0_value and token1_value <= balance1_value:
            # do not need swap
            base_value, quote_value = self._convert_pair(token0_value, token1_value)
            return self.add_liquidity_by_tick(lower_tick, upper_tick, base_value / price, quote_value)
        elif token0_value > balance0_value and token1_value > balance1_value:
            raise DemeterError("Not enough balance to add liquidity")
        elif token0_value < balance0_value and token1_value > balance1_value:
            # need swap from token0 to token1
            actual_token0_value, actual_token1_value, swap_value = get_swap_value_with_part_balance_used(
                balance0_value, balance1_value, value_to_use, self.pool_info.fee_rate, ratio_in_value
            )
            if self._is_token0_quote:
                self.swap(swap_value, self.quote_token, self.base_token)
            else:
                self.swap(swap_value / price, self.base_token, self.quote_token)
            base_value, quote_value = self._convert_pair(actual_token0_value, actual_token1_value)
            return self.add_liquidity_by_tick(lower_tick, upper_tick, base_value / price, quote_value)
        elif token0_value > balance0_value and token1_value < balance1_value:
            # need to swap from token1 to token 0
            actual_token1_value, actual_token0_value, swap_value = get_swap_value_with_part_balance_used(
                balance1_value, balance0_value, value_to_use, self.pool_info.fee_rate, 1 / ratio_in_value
            )
            if self._is_token0_quote:
                self.swap(swap_value / price, self.base_token, self.quote_token)
            else:
                self.swap(swap_value, self.quote_token, self.base_token)
            base_value, quote_value = self._convert_pair(actual_token0_value, actual_token1_value)
            return self.add_liquidity_by_tick(lower_tick, upper_tick, base_value / price, quote_value)
        else:
            raise NotImplementedError()
        pass

    def even_rebalance(self, price: Decimal | None = None):
        """
        Divide assets equally between two tokens.

        :param price: price of quote token. e.g. 1234 eth/usdc, if leave to None, will use pool price
        :type price: Decimal
        """
        if price is None:
            price = self._market_status.data.price

        amount_quote = self.broker.get_token_balance(self.quote_token)
        amount_base = self.broker.get_token_balance(self.base_token)

        delta_base = (amount_quote / price - amount_base) / (Decimal(2) + self.pool_info.fee_rate)
        if delta_base >= 0:
            self.buy(delta_base)
            return

        delta_quote = (amount_base - amount_quote / price) / (Decimal(2) - self.pool_info.fee_rate)
        if delta_quote >= 0:
            self.sell(delta_quote)
            return
        pass

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
        high_name, low_name = (
            ("lowestTick", "highestTick") if self.pool_info.is_token0_quote else ("highestTick", "lowestTick")
        )
        df["low"] = df[high_name].map(lambda x: self.tick_to_price(x))
        df["high"] = df[low_name].map(lambda x: self.tick_to_price(x))
        df["volume0"] = df["inAmount0"].map(lambda x: Decimal(x) / 10**self.pool_info.token0.decimal)
        df["volume1"] = df["inAmount1"].map(lambda x: Decimal(x) / 10**self.pool_info.token1.decimal)

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
        if start_date > end_date:
            raise DemeterError(f"start date {start_date} should earlier than end date {end_date}")
        while day <= end_date:
            new_type_path = os.path.join(
                self.data_path,
                f"{chain.lower()}-{contract_addr}-{day.strftime('%Y-%m-%d')}.minute.csv",
            )
            path = (
                new_type_path
                if os.path.exists(new_type_path)
                else os.path.join(
                    self.data_path,
                    f"{chain}-{contract_addr}-{day.strftime('%Y-%m-%d')}.csv",
                )
            )
            if not os.path.exists(path):
                raise IOError(
                    f"resource file {new_type_path} not found, please download with demeter-fetch: https://github.com/zelos-alpha/demeter-fetch"
                )
            day_df = pd.read_csv(
                path,
                converters={
                    "inAmount0": to_decimal,
                    "inAmount1": to_decimal,
                    "netAmount0": to_decimal,
                    "netAmount1": to_decimal,
                    "currentLiquidity": to_decimal,
                },
            )
            if len(day_df.index) > 0:
                df = pd.concat([df, day_df])
            day = day + timedelta(days=1)
        self.logger.info("load file complete, preparing...")

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)

        # fill empty row (first minutes in a day, might be blank)
        full_indexes = pd.date_range(
            start=start_date,
            end=datetime.combine(end_date, time(0, 0, 0)) + timedelta(days=1) - timedelta(minutes=1),
            freq="1min",
        )
        df = df.reindex(full_indexes)
        # df = Lines.from_dataframe(df)
        # df = df.fillna()
        df: pd.DataFrame = fillna(df)
        if pd.isna(df.iloc[0]["closeTick"]):
            df = df.bfill()

        self.add_statistic_column(df)
        self.data = df
        self.logger.info("data has been prepared")

    def formatted_str(self) -> str:
        """
        Return a brief description of this market in pretty format. Used for print in console.
        """
        value = get_formatted_predefined(f"{self.market_info.name}({type(self).__name__})", STYLE["header3"]) + "\n"
        value += (
            get_formatted_from_dict(
                {
                    "token0": self.pool_info.token0.name,
                    "token1": self.pool_info.token1.name,
                    "fee(%)": self.pool_info.fee_rate * 100,
                    "quote token": self.quote_token.name,
                }
            )
            + "\n"
        )
        value += get_formatted_predefined("positions", STYLE["key"]) + "\n"
        df = position_dict_to_dataframe(self.positions)
        if len(df.index) > 0:
            value += df.to_string()
        else:
            value += "Empty DataFrame\n"
        return value

    def _resample(self, freq: str):
        self._data = resample(self.data, freq)
