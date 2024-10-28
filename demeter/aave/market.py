import os
from _decimal import Decimal
from datetime import date, timedelta
from orjson import orjson
from typing import Dict, List, Set

import pandas as pd

from . import helper
from ._typing import (
    AaveBalance,
    SupplyInfo,
    BorrowInfo,
    Supply,
    Borrow,
    InterestRateMode,
    RiskParameter,
    SupplyKey,
    BorrowKey,
    supply_to_dataframe,
    borrow_to_dataframe,
    SupplyAction,
    WithdrawAction,
    BorrowAction,
    RepayAction,
    LiquidationAction,
    DictCache,
    AaveDescription,
    AaveMarketStatus,
)
from .core import AaveV3CoreLib
from .. import DemeterError, TokenInfo
from .._typing import DECIMAL_0, UnitDecimal, ChainType
from ..broker import Market, MarketInfo, write_func
from ..utils import get_formatted_predefined, STYLE, get_formatted_from_dict, console_text
from ..utils.application import require, float_param_formatter, to_decimal

DEFAULT_DATA_PATH = "./data"


class AaveV3Market(Market):
    """
    | AaveV3Market is the simulator of aave v3, here you can simulate some transactions like supply/borrow etc. this class also tracks value change.
    | AaveV3Market corresponds to a pool on chain, and one chan has one pool.

    :param market_info: key of this market
    :type market_info: MarketInfo
    :param risk_parameters_path: path to load risk parameters csv file, those files can be downloaded form https://www.config.fyi. One csv file for each chain.
    :type risk_parameters_path: str
    :param tokens: Tokens which will be used in this market
    :type tokens: List[TokenInfo]
    :param data: pool data for back test. downloaded by demeter-fetch, it's recommended to set data with load_data() or set_token_data() function
    :type data: DataFrame
    :param data_path: path to load data
    :type data_path: str
    """

    def __init__(
        self,
        market_info: MarketInfo,
        risk_parameters_path: str,
        tokens: List[TokenInfo] = None,
        data: pd.DataFrame = None,
        data_path: str = DEFAULT_DATA_PATH,
    ):
        super().__init__(market_info=market_info, data_path=data_path, data=data)
        tokens = tokens if tokens is not None else []  # just to set an initial value
        self._supplies: Dict[SupplyKey, SupplyInfo] = {}
        self._borrows: Dict[BorrowKey, BorrowInfo] = {}

        self._risk_parameters: pd.DataFrame | Dict[str, RiskParameter] = helper.load_risk_parameter(
            risk_parameters_path
        )

        # caches, since amounts and values are calculated by base_amount, and they are commonly used, cache is introduced to speed up back test.
        # when base amount or price has changed, they must be reset.
        # Maybe I'm just bring trouble on oneself
        self._collaterals_amount_cache = DictCache()
        self._supplies_amount_cache = DictCache()
        self._supplies_cache = DictCache()
        self._borrows_amount_cache = DictCache()
        self._borrows_cache = DictCache()

        self._market_status: AaveMarketStatus = None
        self._tokens: Set[TokenInfo] = set()
        self.add_token(tokens)

    REQUIRED_DATA_COLUMN = [
        "liquidity_rate",
        "stable_borrow_rate",
        "variable_borrow_rate",
        "liquidity_index",
        "variable_borrow_index",
    ]

    def __str__(self):
        from demeter.utils import orjson_default

        return orjson.dumps(self.description, default=orjson_default).decode()

    @property
    def description(self):
        """
        Get a brief description of this market
        """
        return AaveDescription(type(self).__name__, self._market_info.name, len(self._supplies), len(self._borrows))

    @property
    def data(self) -> pd.DataFrame:
        """
        | Get data attribute. data have multiple column index.
        | Columns are organized by token, like this:

        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+
        |                   | WETH           |                   |                     |                 |                      |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+
        |block_timestamp    | liquidity_rate |stable_borrow_rate |variable_borrow_rate | liquidity_index | variable_borrow_index|
        +===================+================+===================+=====================+=================+======================+
        |2023-08-15 00:00:00|              0 |                 0 |                   0 |            1    |             1        |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+
        |2023-08-15 00:01:00|              0 |                 0 |                   0 |        1.001    |         1.001        |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+
        |2023-08-15 00:02:00|              0 |                 0 |                   0 |        1.002    |         1.002        |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+
        |2023-08-15 00:03:00|              0 |                 0 |                   0 |        1.003    |         1.003        |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+
        |2023-08-15 00:04:00|              0 |                 0 |                   0 |        1.004    |         1.004        |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+



        | So if you want to read a element in this dataframe, such as liquidity_rate of weth, you should do: data.iloc[0]["WETH"]["liquidity_rate"],
        | and if you access a column, you can do data["WETH"]["liquidity_rate"]
        | If you append a new column to data, the new column will be

        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+----------------------+
        |                   | WETH           |                   |                     |                 |                      |     new_column       |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+----------------------+
        |block_timestamp    | liquidity_rate |stable_borrow_rate |variable_borrow_rate | liquidity_index | variable_borrow_index|                      |
        +===================+================+===================+=====================+=================+======================+======================+
        |2023-08-15 00:00:00|              0 |                 0 |                   0 |            1    |             1        |             1        |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+----------------------+
        |2023-08-15 00:01:00|              0 |                 0 |                   0 |        1.001    |         1.001        |             2        |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+----------------------+
        |2023-08-15 00:02:00|              0 |                 0 |                   0 |        1.002    |         1.002        |             3        |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+----------------------+
        |2023-08-15 00:03:00|              0 |                 0 |                   0 |        1.003    |         1.003        |             4        |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+----------------------+
        |2023-08-15 00:04:00|              0 |                 0 |                   0 |        1.004    |         1.004        |             5        |
        +-------------------+----------------+-------------------+---------------------+-----------------+----------------------+----------------------+

        This bring an odd thing, if you access a element in new_column by access row first. data.iloc[0]["new_column"] will return a series instead a item. so data.iloc[0]["new_column"][0] will work
        and if you access by column first, data["new_column"] will return a series, so data["new_column"].iloc[0] will work, no need to write extra [0]

        """
        return self._data

    @property
    def risk_parameters(self) -> pd.DataFrame:
        """
        Get risk parameters
        """
        return self._risk_parameters

    def set_token_data(self, token_info: TokenInfo, token_data: pd.DataFrame):
        """
        Set aave pool data of one token. Usually demeter-fetch will keep one csv file for each token.

        :param token_info: which token to set
        :type token_info: TokenInfo
        :param token_data: data
        :type token_data: DataFrame
        """
        if self._data is not None and token_info.name in self._data:
            raise DemeterError(f"{token_info.name} has already set to data")
        if isinstance(token_data, pd.DataFrame):
            token_data = token_data.map(to_decimal)
            token_data.columns = pd.MultiIndex.from_tuples([(token_info.name, c) for c in token_data.columns])
            self._data = pd.concat([self._data, token_data], axis="columns")
        else:
            raise ValueError()

    def load_data(self, chain: ChainType, token_info_list: List[TokenInfo], start_date: date, end_date: date):
        """
        Load data from folder set in data_path. Those data file should be downloaded by demeter, and meet name rule. [chain]-aave_v3-[token_contract_address]-[date].minute.csv

        :param chain: chain type
        :type chain: ChainType
        :param token_info_list: tokens to load
        :type token_info_list: List[TokenInfo]
        :param start_date: start day
        :type start_date: date
        :param end_date: end day, the end day will be included
        :type end_date: date
        """
        self.logger.info(f"start load files from {start_date} to {end_date}...")
        for token_info in token_info_list:
            day = start_date
            df = pd.DataFrame()
            if token_info.address == "":
                raise DemeterError(f"address of {token_info.name} not set")
            while day <= end_date:
                path = os.path.join(
                    self.data_path,
                    f"{chain.name.lower()}-aave_v3-{token_info.address}-{day.strftime('%Y-%m-%d')}.minute.csv",
                )
                if not os.path.exists(path):
                    raise IOError(
                        f"resource file {path} not found, please download with demeter-fetch: https://github.com/zelos-alpha/demeter-fetch"
                    )
                csv_converters = {n: to_decimal for n in AaveV3Market.REQUIRED_DATA_COLUMN}
                day_df = pd.read_csv(
                    path,
                    converters=csv_converters,
                    index_col=0,
                    parse_dates=True,
                )

                df = pd.concat([df, day_df])
                day += timedelta(days=1)
            self.set_token_data(token_info, df)
        self.logger.info("data has been prepared")

    @property
    def tokens(self) -> Set[TokenInfo]:
        """
        Get tokens in aave back test
        """
        return self._tokens

    @property
    def supplies_value(self) -> Dict[SupplyKey, Decimal]:
        """
        Get value of all supplied token. unit is usd

        :return: value of all tokens
        :rtype: Dict[SupplyKey, Decimal]
        """
        if self._supplies_amount_cache.empty:
            for k, v in self._supplies.items():
                self._supplies_amount_cache.set(
                    k,
                    AaveV3CoreLib.get_amount(v.base_amount, self._market_status.data[k.token.name].liquidity_index)
                    * self._price_status[k.token.name],
                )
        return self._supplies_amount_cache.value

    @property
    def total_supply_value(self) -> Decimal:
        """
        Get sum supply value in this pool, unit is usd
        """
        return Decimal(sum(self.supplies_value.values()))

    @property
    def collateral_value(self) -> Dict[SupplyKey, Decimal]:
        """
        Get value of all collateral token. unit is usd

        :return: value of all collaterals
        :rtype: Dict[SupplyKey, Decimal]
        """
        if self._collaterals_amount_cache.empty:
            for k, v in self._supplies.items():
                if v.collateral:
                    self._collaterals_amount_cache.set(k, self.supplies_value[k])
        return self._collaterals_amount_cache.value

    @property
    def total_collateral_value(self) -> Decimal:
        """
        Get sum supply value in this pool, unit is usd
        """
        return Decimal(sum(self.collateral_value.values()))

    @property
    def borrows_value(self) -> Dict[BorrowKey, Decimal]:
        """
        Get value of all borrowed token. unit is usd

        :return: value of all borrows
        :rtype: Dict[BorrowKey, Decimal]
        """
        if self._borrows_amount_cache.empty:
            for k, v in self._borrows.items():
                self._borrows_amount_cache.set(
                    k,
                    AaveV3CoreLib.get_amount(
                        v.base_amount, self._market_status.data[k.token.name].variable_borrow_index
                    )
                    * self._price_status[k.token.name],
                )
        return self._borrows_amount_cache.value

    @property
    def total_borrows_value(self) -> Decimal:
        """
        Get sum borrow value in this pool, unit is usd
        """
        return Decimal(sum(self.borrows_value.values()))

    @property
    def supplies(self) -> Dict[SupplyKey, Supply]:
        """
        Get amounts and values of all supplies

        :return: Dict of supply information
        :rtype: Dict[SupplyKey, Supply]
        """
        if self._supplies_cache.empty:
            for key in self._supplies.keys():
                self._supplies_cache.set(key, self.get_supply(supply_key=key))
        return self._supplies_cache.value

    @property
    def supply_keys(self) -> List[SupplyKey]:
        """
        Get all supply keys
        """
        return list(self._supplies.keys())

    @property
    def borrows(self) -> Dict[BorrowKey, Borrow]:
        """
        Get amounts and values of all borrows

        :return: Dict of borrow information
        :rtype: Dict[BorrowKey, Borrow]

        """
        if self._borrows_cache.empty:
            for key in self._borrows.keys():
                self._borrows_cache.set(key, self.get_borrow(key))
        return self._borrows_cache.value

    @property
    def borrow_keys(self) -> List[BorrowKey]:
        """
        Get all borrow keys
        """
        return list(self._borrows.keys())

    @property
    def market_status(self) -> AaveMarketStatus:
        """
        Get market status
        """
        return self._market_status

    def set_market_status(
        self,
        data: AaveMarketStatus,
        price: pd.Series,
    ):
        """
        Set up pool status of this moment, such as liquidity index, supply/borrow rate, and price

        :param data: market status
        :type data: AaveMarketStatus
        :param price: current price of tokens involved
        :type price: Series
        """
        # TODO : debug test case
        super().set_market_status(data, price)
        if data.data is None:
            data.data = self.data.loc[data.timestamp]
        self._market_status = data
        self._borrows_amount_cache.reset()
        self._supplies_amount_cache.reset()
        self._collaterals_amount_cache.reset()
        self._borrows_cache.reset()
        self._supplies_cache.reset()

    @property
    def liquidation_threshold(self) -> Decimal:
        """
        Get liquidation threshold
        """
        return AaveV3CoreLib.total_liquidation_threshold(self.collateral_value, self._risk_parameters)

    @property
    def current_ltv(self) -> Decimal:
        """
        Get current ltv, it's the max ltv of current user
        """
        return AaveV3CoreLib.current_ltv(self.collateral_value, self._risk_parameters)

    @property
    def health_factor(self) -> Decimal:
        """
        Get health factor
        """
        return AaveV3CoreLib.health_factor(self.collateral_value, self.borrows_value, self._risk_parameters)

    @property
    def supply_apy(self) -> Decimal:
        """
        Calculate apy of all supplies
        """
        rate_dict: Dict[TokenInfo, Decimal] = {}
        for k in self.supplies.keys():
            rate_dict[k.token] = self._market_status.data[k.token.name].liquidity_rate

        return AaveV3CoreLib.get_apy(self.supplies_value, rate_dict)

    @property
    def borrow_apy(self) -> Decimal:
        """
        Calculate apy of all borrows
        """
        rate_dict: Dict[TokenInfo, Decimal] = {}
        for k in self._borrows.keys():
            if k.interest_rate_mode == InterestRateMode.variable:
                rate_dict[k.token] = self._market_status.data[k.token.name].variable_borrow_rate
            else:
                rate_dict[k.token] = self._market_status.data[k.token.name].stable_borrow_rate

        return AaveV3CoreLib.get_apy(self.borrows_value, rate_dict)

    @property
    def total_apy(self) -> Decimal:
        """
        Calculate total apy based on borrow/supply apy and amount
        """
        total_supplies = self.total_supply_value
        total_borrows = self.total_borrows_value
        supply_apy = self.supply_apy
        borrow_apy = self.borrow_apy
        return AaveV3CoreLib.safe_div_zero(
            supply_apy * total_supplies - borrow_apy * total_borrows, total_supplies - total_borrows
        )

    def get_supply(self, supply_key: SupplyKey = None, token_info: TokenInfo = None) -> Supply:
        """
        Get details of supply position, include value, amount, apy etc.

        :params supply_key: supply key, you can query by supply_key or token_info
        :type supply_key: SupplyKey
        :param token_info: token info, you can query by supply_key or token_info
        :type token_info: TokenInfo
        :return: details of supply position
        :rtype: Supply
        """
        key, token_info = AaveV3Market.__get_supply_key(supply_key, token_info)
        supply_info = self._supplies[key]
        supply_value = Supply(
            token=token_info,
            base_amount=supply_info.base_amount,
            collateral=supply_info.collateral,
            amount=supply_info.base_amount * self._market_status.data[key.token.name].liquidity_index,
            apy=AaveV3CoreLib.rate_to_apy(self._market_status.data[key.token.name].liquidity_rate),
            value=self.supplies_value[key],
        )
        return supply_value

    def get_borrow(self, borrow_key: BorrowKey) -> Borrow:
        """
        Get details of borrow position. include type, amount, value etc.

        :params borrow_key: borrow key
        :type borrow_key: BorrowKey
        :return: details of borrow position
        :rtype: Borrow
        """
        borrow_info = self._borrows[borrow_key]
        return Borrow(
            token=borrow_key.token,
            base_amount=borrow_info.base_amount,
            interest_rate_mode=borrow_key.interest_rate_mode,
            amount=borrow_info.base_amount * self._market_status.data[borrow_key.token.name].variable_borrow_index,
            apy=AaveV3CoreLib.rate_to_apy(
                self.market_status.data[borrow_key.token.name].variable_borrow_rate
                if borrow_key.interest_rate_mode == InterestRateMode.variable
                else self.market_status.data[borrow_key.token.name].stable_borrow_rate
            ),
            value=self.borrows_value[borrow_key],
        )

    def add_token(self, token_info: TokenInfo | List[TokenInfo]):
        """
        Add one or an array of token to aave back test.

        :param token_info: tokens to add
        :type token_info: TokenInfo | List[TokenInfo]
        """
        if not isinstance(token_info, list):
            token_info = [token_info]
        for t in token_info:
            self._tokens.add(t)

    def get_market_balance(self) -> AaveBalance:
        """
        Get position and their values invested in aave market. Note: price will be read from self.market_status.price

        :return: values of positions in aave
        :rtype: AaveBalance
        """
        # supplys = self.supplies
        # borrows = self.borrows
        rounding = Decimal("0.0001")
        total_supplies = self.total_supply_value.quantize(rounding)
        total_borrows = self.total_borrows_value.quantize(rounding)
        net_worth = total_supplies - total_borrows

        supply_apy = self.supply_apy.quantize(rounding)
        borrow_apy = self.borrow_apy.quantize(rounding)
        net_apy = AaveV3CoreLib.safe_div_zero(
            supply_apy * total_supplies - borrow_apy * total_borrows, total_supplies - total_borrows
        )

        return AaveBalance(
            net_value=net_worth,
            supplies_count=len(self._supplies),
            borrows_count=len(self._borrows),
            liquidation_threshold=AaveV3CoreLib.safe_rounding(self.liquidation_threshold, rounding),
            health_factor=AaveV3CoreLib.safe_rounding(self.health_factor, rounding),
            borrows_value=total_borrows,
            supplies_value=total_supplies,
            collaterals_value=self.total_collateral_value.quantize(rounding),
            current_ltv=AaveV3CoreLib.safe_rounding(self.current_ltv, rounding),
            supply_apy=supply_apy,
            borrow_apy=borrow_apy,
            net_apy=net_apy,
        )

    # region for subclass to override
    def check_market(self):
        """
        Check market tokens before back test
        """
        super().check_market()
        require(len(self.tokens) > 0, "should set tokens")
        for t in self.tokens:
            require(
                t.name in self.risk_parameters.index,
                f"According to risk_parameter, {t.name} is not supported in this chain. ",
            )
            for col in AaveV3Market.REQUIRED_DATA_COLUMN:
                require((t.name, col) in self.data.columns, f"{t.name}.{col} not found in data")

    def update(self):
        """
        Trigger update of this market
        """
        self._liquidate()

    def formatted_str(self):
        """
        Return a brief description of this market in pretty format. Used for print in console.
        """
        value = get_formatted_predefined(f"{self.market_info.name}({type(self).__name__})", STYLE["header3"]) + "\n"
        token_dict = {"tokens": ",".join([t.name for t in self._tokens])}
        value += get_formatted_from_dict(token_dict) + "\n"
        balance = self.get_market_balance()
        value += (
            get_formatted_from_dict(
                {
                    "net_value": console_text.format_value(balance.net_value),
                    "health_factor": console_text.format_value(balance.health_factor),
                    "borrow_balance": console_text.format_value(balance.borrows_value),
                    "supply_balance": console_text.format_value(balance.supplies_value),
                    "collateral_balance": console_text.format_value(balance.collaterals_value),
                    "supply_apy": console_text.format_value(balance.supply_apy),
                    "borrow_apy": console_text.format_value(balance.borrow_apy),
                    "net_apy": console_text.format_value(balance.net_apy),
                }
            )
            + "\n"
        )
        value += get_formatted_predefined("Supplies", STYLE["key"]) + "\n"
        supply_df = supply_to_dataframe(self.supplies)
        value += supply_df.to_string() + "\n" if len(supply_df.index) > 0 else "Empty DataFrame\n"
        value += get_formatted_predefined("Borrows", STYLE["key"]) + "\n"
        borrow_df = borrow_to_dataframe(self.borrows)
        value += borrow_df.to_string() + "\n" if len(borrow_df.index) > 0 else "Empty DataFrame\n"

        return value

    # endregion

    @write_func
    @float_param_formatter
    def supply(self, token_info: TokenInfo, amount: Decimal | float, collateral: bool = True) -> SupplyKey:
        """
        | Supply asset to aave pool
        | Note:
        | 1. some token are not allow to collateral, it's decided by risk parameter
        | 2. if append amount to existing supply, collateral can not change.

        :param token_info: which token to supply
        :type token_info: TokenInfo
        :param amount: amount to supply
        :type amount: Decimal | float
        :param collateral: collateral or not, default is true.
        :type collateral: bool
        :return: key of new supply
        :rtype: SupplyKey
        """
        if collateral:
            require(self._risk_parameters.loc[token_info.name].canCollateral, "Can not supplied as collateral")
        token_status = self._market_status.data[token_info.name]
        #  calc in pool value
        pool_amount = AaveV3CoreLib.get_base_amount(amount, token_status.liquidity_index)

        self.broker.subtract_from_balance(token_info, amount)

        key = SupplyKey(token_info)
        if key not in self._supplies:
            self._supplies[key] = SupplyInfo(base_amount=Decimal(0), collateral=collateral)
        else:
            require(self._supplies[key].collateral == collateral, "Collateral different from existing supply")
        self._supplies[key].base_amount += pool_amount

        self._supplies_amount_cache.reset()
        self._supplies_cache.reset()
        self._collaterals_amount_cache.reset()

        self._record_action(
            SupplyAction(
                market=self.market_info,
                token=token_info.name,
                amount=UnitDecimal(amount, token_info.name),
                collateral=collateral,
                deposit_after=UnitDecimal(
                    AaveV3CoreLib.get_amount(self._supplies[key].base_amount, token_status.liquidity_index),
                    token_info.name,
                ),
            )
        )

        return key

    @staticmethod
    def __get_supply_key(supply_key: SupplyKey = None, token_info: TokenInfo = None):
        if supply_key is not None:
            key = supply_key
            token_info = key.token
        elif token_info is not None:
            key = SupplyKey(token_info)
        else:
            raise DemeterError("supply_key or token should be specified")
        return key, token_info

    @write_func
    def change_collateral(
        self, collateral: bool, supply_key: SupplyKey = None, token_info: TokenInfo = None
    ) -> SupplyKey:
        """
        Change collateral type of supply position. Health factor will be checked to prevent liquidation

        :param collateral: new value
        :type collateral: bool
        :param supply_key: key of supply, you can set by supply_key or token_info
        :type supply_key: SupplyKey
        :param token_info: token to supply, you can set by supply_key or token_info
        :type token_info: TokenInfo
        :return: key of new supply
        :rtype: SupplyKey
        """
        key, token_info = AaveV3Market.__get_supply_key(supply_key, token_info)
        old_collateral = self._supplies[key].collateral
        if old_collateral == collateral:
            return key

        self._supplies[key].collateral = collateral
        self._collaterals_amount_cache.reset()

        if (not collateral) and self.health_factor < AaveV3CoreLib.HEALTH_FACTOR_LIQUIDATION_THRESHOLD:
            # revert
            self._supplies[SupplyKey(token_info)].collateral = old_collateral
            self._collaterals_amount_cache.reset()
            raise AssertionError("health factor lower than liquidation threshold")

        return key

    @write_func
    @float_param_formatter
    def withdraw(
        self,
        supply_key: SupplyKey = None,
        amount: Decimal | float = None,
        token_info: TokenInfo = None,
    ):
        """
        Withdraw supply from aave pool.

        :param supply_key: key of supply, you can set by supply_key or token_info
        :type supply_key: SupplyKey
        :param amount: amount to withdraw, if set to None, will withdraw max available amount
        :type amount: Decimal | float
        :param token_info: which token to withdraw. you can set by supply_key or token_info
        :type token_info: TokenInfo
        """
        key, token_info = AaveV3Market.__get_supply_key(supply_key, token_info)
        token_status = self._market_status.data[token_info.name]
        supply = self.get_supply(key)
        if amount is None:
            amount = supply.amount
        require(amount != 0, "invalid amount")
        require(amount <= supply.amount, "not enough available user balance")

        # try calc new health factor after withdraw. if health factor is low, raise a error
        if self._supplies[key].collateral:
            old_base_amount = self._supplies[key].base_amount
            self._supplies[key].base_amount -= AaveV3CoreLib.get_base_amount(
                amount, self._market_status.data[key.token.name].liquidity_index
            )
            self._supplies_amount_cache.reset()
            self._collaterals_amount_cache.reset()
            if self.health_factor < AaveV3CoreLib.HEALTH_FACTOR_LIQUIDATION_THRESHOLD:
                raise AssertionError("health factor lower than liquidation threshold")
            self._supplies[key].base_amount = old_base_amount

        final_base_amount = self.__sub_supply_amount(key, amount)
        self.broker.add_to_balance(token_info, amount)
        self._record_action(
            WithdrawAction(
                market=self.market_info,
                token=token_info.name,
                amount=UnitDecimal(amount, token_info.name),
                deposit_after=UnitDecimal(
                    AaveV3CoreLib.get_amount(final_base_amount, token_status.liquidity_index), token_info.name
                ),
            )
        )

        pass

    def get_max_withdraw_amount(self, supply_key: SupplyKey = None, token_info: TokenInfo = None) -> Decimal:
        """
        Get max available withdraw amount

        :param supply_key: key of supply to query, you can set by supply_key or token_info
        :type supply_key: SupplyKey
        :param token_info: which token to query. you can set by supply_key or token_info
        :type token_info: TokenInfo
        :return: max withdraw amount
        :rtype: Decimal
        """
        key, token_info = AaveV3Market.__get_supply_key(supply_key, token_info)
        return self.supplies[key].amount - AaveV3CoreLib.get_min_withdraw_kept_amount(
            token_info,
            self.collateral_value,
            self.borrows_value,
            self._risk_parameters,
            self._price_status[token_info.name],
        )

    def get_max_borrow_amount(self, token_info: TokenInfo) -> Decimal:
        """
        Get max token amount to borrow.

        :param token_info: token to query
        :param token_info: TokenInfo
        :return: max borrow amount
        :rtype: Decimal
        """
        value = AaveV3CoreLib.get_max_borrow_value(self.collateral_value, self.borrows_value, self.risk_parameters)
        return value / self._price_status[token_info.name]

    @write_func
    @float_param_formatter
    def borrow(
        self,
        token_info: TokenInfo,
        amount: Decimal | float = None,
        interest_rate_mode: InterestRateMode = InterestRateMode.variable,
    ) -> BorrowKey:
        """
        | Borrow token from aave pool.
        | Note:
        | 1. Risk parameter decides Which token is allowed to borrow
        | 2. If this borrow transaction will cause health factor below 1, an exception will be raised.
        | 3. If Borrow on existing borrow key, amount will be added to existing key

        :param token_info: Token to borrow
        :type token_info: TokenInfo
        :param amount: amount to borrow. if set to None, will borrow max amount.
        :type amount: Decimal | float
        :param interest_rate_mode: interest rate mode, default is variable.
        :type interest_rate_mode: InterestRateMode
        :return: key of new Borrows
        :rtype: BorrowKey
        """
        key = BorrowKey(token_info, interest_rate_mode)
        if amount is None:
            amount = self.get_max_borrow_amount(token_info)
        # check
        token_status = self._market_status.data[token_info.name]

        require(self._risk_parameters.loc[token_info.name, "canBorrow"], f"borrow is not enabled for {token_info.name}")
        collateral_balance = sum(self.collateral_value.values())
        require(collateral_balance != 0, "collateral balance is zero")
        current_ltv = self.current_ltv
        require(current_ltv != 0, "ltv validation failed")

        require(
            self.health_factor > AaveV3CoreLib.HEALTH_FACTOR_LIQUIDATION_THRESHOLD,
            "health factor lower than liquidation threshold",
        )

        value = amount * self._price_status.loc[token_info.name]
        collateral_needed = sum(self.borrows.values()) + value / current_ltv
        require(collateral_needed <= collateral_balance, "collateral cannot cover new borrow")

        if interest_rate_mode == InterestRateMode.stable:
            require(self._risk_parameters.loc[token_info.name, "canBorrowStable"], "stable borrowing not enabled")

            is_using_as_collateral = (token_info in self._supplies) and (
                self._supplies[SupplyKey(token_info)].collateral is True
            )

            require(
                (not is_using_as_collateral)
                or self._risk_parameters.loc[token_info.name, "LTV"] == 0
                or amount > self.broker.get_token_balance(token_info),
                "collateral same as borrowing currency",
            )
            # ignore pool amount check, I don't have pool amount

        # do borrow
        base_amount = AaveV3CoreLib.get_base_amount(amount, token_status.variable_borrow_index)

        if key not in self._borrows:
            self._borrows[key] = BorrowInfo(DECIMAL_0)
        self._borrows[key].base_amount += base_amount

        self.broker.add_to_balance(token_info, amount)

        self._borrows_amount_cache.reset()
        self._borrows_cache.reset()

        self._record_action(
            BorrowAction(
                market=self.market_info,
                token=token_info.name,
                amount=UnitDecimal(amount, token_info.name),
                interest_rate_mode=interest_rate_mode,
                debt_after=UnitDecimal(
                    AaveV3CoreLib.get_amount(self._borrows[key].base_amount, token_status.variable_borrow_index),
                    token_info.name,
                ),
            )
        )

        return key

    def get_max_repay_amount(
        self, key: BorrowKey = None, token_info: TokenInfo = None, interest_rate_mode: InterestRateMode = None
    ) -> Decimal:
        """
        Get max token amount to repay.

        :param key: key for borrow. Either fill key parameter or token_info+interest_rate_mode parameter.
        :type key: BorrowKey
        :param token_info: token to borrow, Either fill key parameter or token_info+interest_rate_mode parameter.
        :type token_info: TokenInfo
        :param interest_rate_mode: interest rate mode, Either fill key parameter or token_info+interest_rate_mode parameter.
        :type interest_rate_mode: InterestRateMode
        :return: max amount to repay
        :rtype: Decimal
        """
        (key, _, _) = AaveV3Market.__get_borrow_key(key, token_info, interest_rate_mode)
        return AaveV3CoreLib.get_amount(
            self._borrows[key].base_amount, self.market_status.data[key.token.name].variable_borrow_index
        )

    @staticmethod
    def __get_borrow_key(
        key: BorrowKey = None, token_info: TokenInfo = None, interest_rate_mode: InterestRateMode = None
    ):
        if key is None:
            if token_info is None:
                raise DemeterError("either key or token should be filled")
            key = BorrowKey(token_info, interest_rate_mode)
        token_info = key.token
        interest_rate_mode = key.interest_rate_mode
        return key, token_info, interest_rate_mode

    def _get_swap_amount(self, from_token: TokenInfo, to_token: TokenInfo, amount: Decimal, swap_fee=0):
        return amount * (1 - swap_fee) * self._price_status.loc[from_token.name] / self._price_status.loc[to_token.name]

    @write_func
    @float_param_formatter
    def repay(
        self,
        key: BorrowKey = None,
        payback_amount: Decimal | float = None,
        borrow_token: TokenInfo = None,
        interest_rate_mode: InterestRateMode = None,
        repay_with_collateral: bool = False,
        repay_collateral_token: TokenInfo = None,
    ):
        """
        Repay borrow. You can repay with collateral token or cash.

        :param key: key for borrow. Either fill key parameter or token_info+interest_rate_mode parameter.
        :type key: BorrowKey
        :param borrow_token: token to borrow, Either fill key parameter or token_info+interest_rate_mode parameter.
        :type borrow_token: TokenInfo
        :param interest_rate_mode: interest rate mode, Either fill key parameter or token_info+interest_rate_mode parameter.
        :type interest_rate_mode: InterestRateMode
        :param payback_amount: amount to pay back, if leave to None, will use max repay amount
        :type payback_amount: Decimal | float
        :param repay_with_collateral: If set to True, will repay with collateral, else will repay with cash
        :type repay_with_collateral: bool
        :param repay_collateral_token: Which collateral token is used to repay the debt, if repay_with_collateral==False, this parameter will not work,
        :type repay_collateral_token: TokenInfo

        """
        (key, borrow_token, interest_rate_mode) = AaveV3Market.__get_borrow_key(key, borrow_token, interest_rate_mode)
        # because liqThereshold<1, so repay will collateral will increase health factor, so there is no need to check health factor
        token_status = self._market_status.data[borrow_token.name]
        borrow = self.get_borrow(key)

        if payback_amount is None:
            payback_amount = borrow.amount

        if repay_with_collateral:
            if repay_collateral_token is None:
                repay_collateral_token = borrow_token
            repay_collateral_key = SupplyKey(repay_collateral_token)
            require(repay_collateral_key in self.supplies.keys(), f"token {repay_collateral_token} is not in supply")
            require(
                self.supplies[repay_collateral_key].collateral, f"token {repay_collateral_token} is not in collateral"
            )

            required_amount_in_collateral_token = self._get_swap_amount(
                borrow_token, repay_collateral_token, payback_amount
            )
            supply = self.get_supply(supply_key=repay_collateral_key)
            if required_amount_in_collateral_token > supply.amount:
                # contract will change payback amount instead of raise a error
                payback_amount = self._get_swap_amount(repay_collateral_token, borrow_token, supply.amount)

        payback_base_amount = AaveV3CoreLib.get_base_amount(payback_amount, token_status.variable_borrow_index)

        require(payback_base_amount > 0, "invalid amount")
        require(self._borrows[key].base_amount> 0, "no debt of selected type")
        require(round(self._borrows[key].base_amount-payback_base_amount, 18) >= 0, "amount exceed debt")
        if repay_with_collateral:
            payback_amount_in_collateral = self._get_swap_amount(borrow_token, repay_collateral_token, payback_amount)
            self.__sub_supply_amount(SupplyKey(repay_collateral_token), payback_amount_in_collateral)
        else:
            self.broker.subtract_from_balance(borrow_token, payback_amount)
        debt = self.__sub_borrow_amount(key, payback_amount)
        self._record_action(
            RepayAction(
                market=self.market_info,
                token=borrow_token.name,
                amount=UnitDecimal(payback_amount, borrow_token.name),
                interest_rate_mode=interest_rate_mode,
                debt_after=UnitDecimal(
                    AaveV3CoreLib.get_amount(debt, token_status.variable_borrow_index), borrow_token.name
                ),
            )
        )

        pass

    def __sub_supply_amount(self, key: SupplyKey, amount: Decimal) -> Decimal:
        if key not in self._supplies:
            if amount == Decimal(0):
                return Decimal(0)
            else:
                raise DemeterError(f"{key} not exist in supplies")
        self._supplies[key].base_amount = helper.sub_base_amount(
            self._supplies[key].base_amount,
            AaveV3CoreLib.get_base_amount(amount, self._market_status.data[key.token.name].liquidity_index),
        )
        if self._supplies[key].collateral:
            self._collaterals_amount_cache.reset()
        self._supplies_amount_cache.reset()
        self._supplies_cache.reset()
        if self._supplies[key].base_amount == DECIMAL_0:
            if self._supplies[key].collateral:
                self._collaterals_amount_cache.reset()
            del self._supplies[key]
            return DECIMAL_0
        else:
            return self._supplies[key].base_amount

    def __sub_borrow_amount(self, key: BorrowKey, amount: Decimal) -> Decimal:
        if key not in self._borrows:
            if amount == Decimal(0):
                return Decimal(0)
            else:
                raise DemeterError(f"{key} not exist in borrows")
        self._borrows[key].base_amount = helper.sub_base_amount(
            self._borrows[key].base_amount,
            AaveV3CoreLib.get_base_amount(amount, self._market_status.data[key.token.name].variable_borrow_index),
        )
        self._borrows_amount_cache.reset()
        self._borrows_cache.reset()
        if self._borrows[key].base_amount == DECIMAL_0:
            del self._borrows[key]
            return DECIMAL_0
        else:
            return self._borrows[key].base_amount

    @write_func
    def _liquidate(self):
        """
        | Do passive liquidate. If health factor is below 1, liquidate will be triggered. And user can not make a liquidation transaction. Because currently demeter doesn't support that.
        | First is to decide when to liquidate, if in current loop, health factor is below 1, liquidation will happen immediately. Triggered by update function.
        | Second step to choose the assets. Here we will pick the most valuable collateral asset and least valuable debt.
        | After liquidation, if health factor is still below 1. Will choose a pair of collateral and debt to liquidate again.
        | But if a debt asset has liquidated, It will not be liquidated again.
        """
        health_factor = self.health_factor
        has_liquidated: List[BorrowKey] = []
        # health_factor ==0 means there are no collateral to liquidate
        # health_factor > 0.000001 to avoid calculate error
        while 0 < health_factor < AaveV3CoreLib.HEALTH_FACTOR_LIQUIDATION_THRESHOLD:
            # choose which token and how much to liquidate

            # choose the smallest delt
            borrows = self.borrows
            supplys = self.supplies

            min_borrow_key = None
            min_borrow_value = Decimal(10e21)  # a very large number
            for k, v in borrows.items():
                if min_borrow_value >= v.value and (k not in has_liquidated):
                    min_borrow_value = v.value
                    min_borrow_key = k
            # choose the biggest collateral
            max_supply_key = None
            max_supply_value = Decimal(0)
            for k, v in supplys.items():
                if v.collateral and max_supply_value <= v.value:
                    max_supply_value = v.value
                    max_supply_key = k
            # if a token has liquidated, but health_factor still < 1, it should not be liquidated again.
            # because if 0.95 < health_factor < 1, only half of this token will be liquidated. if liquidate this token again, will only liquidate 1/4
            # so health_factor will never go above 1

            has_liquidated.append(min_borrow_key)

            try:
                self._do_liquidate(max_supply_key.token, min_borrow_key.token, min_borrow_value)
            except AssertionError:
                # if a liquidated is rejected, choose another delt token to liquidate
                pass
            health_factor = self.health_factor

    def _do_liquidate(self, collateral_token: TokenInfo, delt_token: TokenInfo, delt_value_to_cover: Decimal):
        """
        Make a liquidation transaction;

        :param collateral_token: Which collateral token will be used
        :type collateral_token: TokenInfo
        :param delt_token: Which debt token will be repaid
        :type delt_token: TokenInfo
        :param delt_value_to_cover: total delt token value to repay. unit is usd
        :type delt_value_to_cover: Decimal

        """
        old_health_factor = self.health_factor
        borrow_index = self._market_status.data[delt_token.name].variable_borrow_index
        supply_index = self._market_status.data[delt_token.name].liquidity_index

        stable_key = BorrowKey(delt_token, InterestRateMode.stable)
        variable_key = BorrowKey(delt_token, InterestRateMode.variable)
        collateral_key = SupplyKey(collateral_token)
        liquidation_bonus = self._risk_parameters.loc[collateral_token.name].liqBonus

        # _calculateDebt
        stable_delt = self.get_borrow(stable_key).amount if stable_key in self._borrows else DECIMAL_0
        variable_delt = self.get_borrow(variable_key).amount if variable_key in self._borrows else DECIMAL_0
        total_debt = stable_delt + variable_delt
        close_factor = (
            AaveV3CoreLib.DEFAULT_LIQUIDATION_CLOSE_FACTOR
            if old_health_factor > AaveV3CoreLib.CLOSE_FACTOR_HF_THRESHOLD
            else AaveV3CoreLib.MAX_LIQUIDATION_CLOSE_FACTOR
        )
        max_liquidatable_debt = total_debt * close_factor
        actual_debt_to_liquidate = (
            max_liquidatable_debt if delt_value_to_cover > max_liquidatable_debt else delt_value_to_cover
        )

        # validate delt
        is_collateral_enabled = (
            self._risk_parameters.loc[collateral_token.name].liqThereshold != 0
            and self._supplies[collateral_key].collateral
        )

        require(is_collateral_enabled, "collateral cannot be liquidated")
        require(total_debt != DECIMAL_0, "specified currency not borrowed by user")

        user_collateral_balance = (
            self._supplies[SupplyKey(collateral_token)].base_amount
            * self._market_status.data[collateral_token.name].liquidity_index
        )

        # calculate actual amount
        should_collateral = (
            self._price_status.loc[delt_token.name]
            * actual_debt_to_liquidate
            / self._price_status.loc[collateral_token.name]
        )
        max_collateral_to_liquidate = should_collateral * (1 + liquidation_bonus)

        if max_collateral_to_liquidate > user_collateral_balance:
            actual_collateral_to_liquidate = user_collateral_balance
            actual_debt_to_liquidate = (
                self._price_status.loc[collateral_token.name] * actual_collateral_to_liquidate
            ) / (self._price_status.loc[delt_token.name] * (1 + liquidation_bonus))
        else:
            actual_collateral_to_liquidate = max_collateral_to_liquidate
            actual_debt_to_liquidate = actual_debt_to_liquidate
        self._supplies[collateral_key].base_amount = helper.sub_base_amount(
            self._supplies[collateral_key].base_amount,
            AaveV3CoreLib.get_base_amount(actual_collateral_to_liquidate, supply_index),
        )

        if self._supplies[collateral_key].base_amount == 0:
            del self._supplies[collateral_key]
        if variable_delt > actual_debt_to_liquidate:
            vari_debt_remaining_base = self.__sub_borrow_amount(variable_key, actual_debt_to_liquidate)
            stable_debt_remaining_base = (
                self._borrows[stable_key].base_amount if stable_key in self._borrows else DECIMAL_0
            )
            vari_debt_liquidated = actual_debt_to_liquidate
            stable_debt_liquidated = DECIMAL_0

        else:
            vari_debt_liquidated = variable_delt
            stable_debt_liquidated = actual_debt_to_liquidate - variable_delt
            vari_debt_remaining_base = self.__sub_borrow_amount(variable_key, variable_delt)
            stable_debt_remaining_base = self.__sub_borrow_amount(stable_key, stable_debt_liquidated)

        self._borrows_amount_cache.reset()
        self._borrows_cache.reset()
        self._supplies_amount_cache.reset()
        self._supplies_cache.reset()
        self._collaterals_amount_cache.reset()

        self._record_action(
            LiquidationAction(
                market=self.market_info,
                collateral_token=collateral_token.name,
                debt_token=delt_token.name,
                delt_to_cover=UnitDecimal(delt_value_to_cover, delt_token.name),
                collateral_used=UnitDecimal(actual_collateral_to_liquidate, collateral_token.name),
                variable_delt_liquidated=UnitDecimal(vari_debt_liquidated, delt_token.name),
                stable_delt_liquidated=UnitDecimal(stable_debt_liquidated, delt_token.name),
                health_factor_before=old_health_factor,
                health_factor_after=self.health_factor,
                collateral_after=UnitDecimal(
                    AaveV3CoreLib.get_amount(
                        self._supplies[collateral_key].base_amount if collateral_key in self._supplies else DECIMAL_0,
                        supply_index,
                    ),
                    collateral_token.name,
                ),
                variable_debt_after=UnitDecimal(
                    AaveV3CoreLib.get_amount(vari_debt_remaining_base, borrow_index), delt_token.name
                ),
                stable_delt_after=UnitDecimal(
                    AaveV3CoreLib.get_amount(stable_debt_remaining_base, borrow_index), delt_token.name
                ),
            )
        )

    def _resample(self, freq: str):
        self._data = self.data.resample(freq).first()
