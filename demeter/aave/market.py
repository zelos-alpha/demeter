import os
import token
from _decimal import Decimal
from datetime import datetime
from typing import Dict, List, Set

import pandas as pd

from . import helper
from ._typing import AaveBalance, SupplyInfo, BorrowInfo, AaveV3PoolStatus, Supply, Borrow, InterestRateMode, RiskParameter
from .core import AaveV3CoreLib
from .. import MarketInfo, DECIMAL_0, DemeterError, TokenInfo
from .._typing import ChainType
from ..broker import Market, BaseAction, MarketStatus, MarketBalance

DEFAULT_DATA_PATH = "./data"


class AaveV3Market(Market):
    def __init__(self, market_info: MarketInfo, chain: ChainType, token_setting_path: str = "./aave_risk_parameters", tokens=[]):
        super().__init__(market_info=market_info)
        self._supplies: Dict[TokenInfo, SupplyInfo] = {}
        self._borrows: Dict[TokenInfo, BorrowInfo] = {}
        self._market_status: pd.Series | AaveV3PoolStatus = AaveV3PoolStatus(None, {})

        if chain not in [
            ChainType.arbitrum,
            ChainType.avalanche,
            ChainType.ethereum,
            ChainType.fantom,
            ChainType.harmony,
            ChainType.optimism,
            ChainType.polygon,
        ]:
            raise DemeterError(f"chain {chain} is not supported in aave")

        self._risk_parameters: pd.DataFrame | Dict[str, RiskParameter] = helper.load_risk_parameter(chain, token_setting_path)

        self._supply_amount_cache: [TokenInfo, Decimal] = None
        self._borrows_amount_cache: [TokenInfo, Decimal] = None

        self._tokens: Set[TokenInfo] = set()
        self.add_token(tokens)

    def __str__(self):
        pass

    @property
    def market_info(self) -> MarketInfo:
        return self._market_info

    @property
    def data(self):
        """
        data got from uniswap pool
        :return:
        :rtype:
        """
        return self._data

    def set_data(self, token_info: TokenInfo, value: pd.DataFrame):
        if isinstance(value, pd.DataFrame):
            value = value / (10**27)
            value.columns = pd.MultiIndex.from_tuples([(token_info.name, c) for c in value.columns])
            self._data = pd.concat([self._data, value], axis="columns")
        else:
            raise ValueError()

    @data.setter
    def data(self, value):
        raise NotImplementedError("Aave market doesn't support set data with setter, please use set_data instead")

    @property
    def tokens(self) -> Set[TokenInfo]:
        return self._tokens

    @property
    def supplies_value(self):
        if self._supply_amount_cache is None:
            self._supply_amount_cache = {}
            for t, v in self._supplies.items():
                self._supply_amount_cache[t] = (
                    AaveV3CoreLib.get_current_amount(v.base_amount, self._market_status.tokens[t].liquidity_index) * self._price_status[t.name]
                )
        return self._supply_amount_cache

    @property
    def borrows_value(self):
        if self._borrows_amount_cache is None:
            self._borrows_amount_cache = {}
            for t, v in self._borrows.items():
                self._borrows_amount_cache[t] = (
                    AaveV3CoreLib.get_current_amount(v.base_amount, self._market_status.tokens[t].variable_borrow_index) * self._price_status[t.name]
                )
        return self._borrows_amount_cache

    @property
    def supplies(self) -> Dict[TokenInfo, Supply]:
        supply_dict: Dict[TokenInfo, Supply] = {}
        supplies_value = self.supplies_value
        for token_info, supply_info in self._supplies.items():
            supply_value = Supply(
                token=token_info,
                base_amount=supply_info.base_amount,
                collateral=supply_info.collateral,
                amount=supplies_value[token_info] / self._price_status.loc[token_info.name],
                apy=AaveV3CoreLib.rate_to_apy(self._market_status.tokens[token_info].liquidity_rate),
                value=supplies_value[token_info],
            )
            supply_dict[token_info] = supply_value
        return supply_dict

    @property
    def borrows(self) -> Dict[TokenInfo, Borrow]:
        borrow_dict = {}
        borrows_value = self.borrows_value
        for token_info, borrow_info in self._borrows.items():
            borrow_value = Borrow(
                token=token_info,
                base_amount=borrow_info.base_amount,
                interest_rate_mode=borrow_info.interest_rate_mode,
                amount=borrows_value[token_info] / self._price_status.loc[token_info.name],
                apy=AaveV3CoreLib.rate_to_apy(
                    self.market_status.tokens[token_info].variable_borrow_rate
                    if borrow_info.interest_rate_mode == InterestRateMode.variable
                    else self.market_status.tokens[token_info].stable_borrow_rate
                ),
                value=borrows_value[token_info],
            )
            borrow_dict[token_info] = borrow_value

        return borrow_dict

    def set_market_status(self, timestamp: datetime, data: pd.Series | AaveV3PoolStatus, price: pd.Series):
        """
        set up market status, such as liquidity, price
        :param timestamp: current timestamp
        :type timestamp: datetime
        :param data: market status
        :type data: pd.Series | MarketStatus
        """
        if isinstance(data, MarketStatus):
            self._market_status: pd.Series | AaveV3PoolStatus = data
        else:
            self._market_status = MarketStatus(timestamp)
        self._price_status = price
        self._borrows_amount_cache = None
        self._supply_amount_cache = None

    @property
    def liquidation_threshold(self) -> Decimal:
        return AaveV3CoreLib.total_liquidation_threshold(self.supplies_value, self._risk_parameters)

    @property
    def current_ltv(self) -> Decimal:
        return AaveV3CoreLib.current_ltv(self.supplies_value, self.borrows_value, self._risk_parameters)

    @property
    def health_factor(self) -> Decimal:
        return AaveV3CoreLib.health_factor(self.supplies_value, self.borrows_value, self._risk_parameters)

    @property
    def supply_apy(self) -> Decimal:
        rate_dict = {}
        for t in self.tokens:
            rate_dict[t] = self._market_status.tokens[t].liquidity_rate

        return AaveV3CoreLib.get_apy(self.supplies_value, rate_dict)

    @property
    def borrow_apy(self) -> Decimal:
        rate_dict = {}
        for t in self._borrows.keys():
            if self._borrows[t].interest_rate_mode == InterestRateMode.variable:
                rate_dict[t] = self._market_status.tokens[t].variable_borrow_rate
            else:
                rate_dict[t] = self._market_status.tokens[t].stable_borrow_rate

        return AaveV3CoreLib.get_apy(self.borrows_value, rate_dict)

    @property
    def total_apy(self) -> Decimal:
        total_supplies = sum(self.supplies_value.values())
        total_borrows = sum(self.borrows_value.values())
        supply_apy = self.supply_apy
        borrow_apy = self.borrow_apy
        return AaveV3CoreLib.safe_div(supply_apy * total_supplies - borrow_apy * total_borrows, total_supplies + total_borrows)

    def add_token(self, token: TokenInfo | List[TokenInfo]):
        if not isinstance(token, list):
            token = [token]
        for t in token:
            self._tokens.add(t)

    def get_market_balance(self) -> AaveBalance:
        """
        get market asset balance
        :return:
        :rtype:
        """
        supplys = self.supplies
        borrows = self.borrows

        total_supplies = sum(self.supplies_value.values())
        total_borrows = sum(self.borrows_value.values())
        collateral = sum(map(lambda v: v.value, filter(lambda v: v.collateral, supplys.values())))
        net_worth = total_supplies - total_borrows
        supply_apy = self.supply_apy
        borrow_apy = self.borrow_apy
        net_apy = AaveV3CoreLib.safe_div(supply_apy * total_supplies - borrow_apy * total_borrows, total_supplies + total_borrows)

        return AaveBalance(
            net_value=net_worth,
            supplys=supplys,
            borrows=borrows,
            liquidation_threshold=self.liquidation_threshold,
            health_factor=self.health_factor,
            total_borrows=total_borrows,
            total_supplies=total_supplies,
            collateral=collateral,
            current_ltv=self.current_ltv,
            supply_apy=supply_apy,
            borrow_apy=borrow_apy,
            net_apy=net_apy,
        )

    # region for subclass to override
    def check_asset(self):
        pass

    def update(self):
        """
        update status various in markets. eg. liquidity fees of uniswap
        :return:
        :rtype:
        """
        pass

    @property
    def market_status(self):
        return self._market_status

    def check_before_test(self):
        """
        do some check for this market before back test start

        检查: market数据和price中是否包含了self._tokens定义的所有token
        :return:
        :rtype:
        """
        if not isinstance(self.data, pd.DataFrame):
            raise DemeterError("data must be type of data frame")
        if not isinstance(self.data.index, pd.core.indexes.datetimes.DatetimeIndex):
            raise DemeterError("date index must be datetime")

    def formatted_str(self):
        return ""

    # endregion

    def supply(self, token: TokenInfo, amount: Decimal, collateral: bool = True):
        #  calc in pool value
        pool_amount = AaveV3CoreLib.get_base_amount(amount, self._market_status.tokens[token].liquidity_index)

        if token in self._supplies:
            self._supplies[token].base_amount += pool_amount
            pass
        else:
            # update self.supplies
            supply_item = SupplyInfo(base_amount=pool_amount, collateral=collateral)
            self._supplies[token] = supply_item
            pass
        self._supply_amount_cache = None

    def change_collateral(self, token: TokenInfo, collateral: bool):
        self._supplies[token].collateral = collateral

    def withdraw(self):
        self._supply_amount_cache = None

        pass

    def borrow(self):
        self._borrows_amount_cache = None
        pass

    def repay(self):
        self._borrows_amount_cache = None

        pass

    def _liquidate(self):
        self._borrows_amount_cache = None
        self._supply_amount_cache = None

        pass
