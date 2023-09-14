from _decimal import Decimal
from datetime import datetime
from typing import Dict, List, Set

import pandas as pd

from . import helper
from ._typing import AaveBalance, SupplyInfo, BorrowInfo, AaveV3PoolStatus, Supply, Borrow, InterestRateMode, RiskParameter, SupplyKey, BorrowKey
from .core import AaveV3CoreLib
from .. import MarketInfo, DemeterError, TokenInfo
from .._typing import ChainType
from ..broker import Market, MarketStatus
from ..utils.application import require

DEFAULT_DATA_PATH = "./data"


class AaveV3Market(Market):
    def __init__(self, market_info: MarketInfo, chain: ChainType, token_setting_path: str = "./aave_risk_parameters", tokens: List[TokenInfo] = []):
        super().__init__(market_info=market_info)
        self._supplies: Dict[SupplyKey, SupplyInfo] = {}
        self._borrows: Dict[BorrowKey, BorrowInfo] = {}
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

        self._collateral_cache = None
        self._supply_amount_cache = None
        self._borrows_amount_cache = None

        self._tokens: Set[TokenInfo] = set()
        self.add_token(tokens)

    HEALTH_FACTOR_LIQUIDATION_THRESHOLD = Decimal(1)

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
    def supplies_amount(self):
        if self._supply_amount_cache is None:
            self._supply_amount_cache = {}
            for k, v in self._supplies.items():
                self._supply_amount_cache[k] = (
                    AaveV3CoreLib.get_current_amount(v.base_amount, self._market_status.tokens[k.token].liquidity_index)
                    * self._price_status[k.token.name]
                )
        return self._supply_amount_cache

    @property
    def collateral_amount(self):
        if self._collateral_cache is None:
            self._collateral_cache = {}
            for k, v in self._supplies.items():
                if v.collateral:
                    self._collateral_cache[k] = self.supplies_amount[k]
        return self._collateral_cache

    @property
    def borrows_amount(self):
        if self._borrows_amount_cache is None:
            self._borrows_amount_cache = {}
            for k, v in self._borrows.items():
                self._borrows_amount_cache[k] = (
                    AaveV3CoreLib.get_current_amount(v.base_amount, self._market_status.tokens[k.token].variable_borrow_index)
                    * self._price_status[k.token.name]
                )
        return self._borrows_amount_cache

    @property
    def supplies(self) -> Dict[SupplyKey, Supply]:
        supply_dict: Dict[SupplyKey, Supply] = {}
        supplies_value = self.supplies_amount
        for key, supply_info in self._supplies.items():
            supply_value = Supply(
                token=key.token,
                base_amount=supply_info.base_amount,
                collateral=supply_info.collateral,
                amount=supplies_value[key] / self._price_status.loc[key.token.name],
                apy=AaveV3CoreLib.rate_to_apy(self._market_status.tokens[key.token].liquidity_rate),
                value=supplies_value[key],
            )
            supply_dict[key] = supply_value
        return supply_dict

    @property
    def borrows(self) -> Dict[BorrowKey, Borrow]:
        borrow_dict: Dict[BorrowKey, Borrow] = {}
        borrows_value = self.borrows_amount
        for key, borrow_info in self._borrows.items():
            borrow_value = Borrow(
                token=key.token,
                base_amount=borrow_info.base_amount,
                interest_rate_mode=key.interest_rate_mode,
                amount=borrows_value[key] / self._price_status.loc[key.token.name],
                apy=AaveV3CoreLib.rate_to_apy(
                    self.market_status.tokens[key.token].variable_borrow_rate
                    if key.interest_rate_mode == InterestRateMode.variable
                    else self.market_status.tokens[key.token].stable_borrow_rate
                ),
                value=borrows_value[key],
            )
            borrow_dict[key] = borrow_value

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
        self._price_status: pd.Series = price
        self._borrows_amount_cache = None
        self._supply_amount_cache = None
        self._collateral_cache = None

    @property
    def liquidation_threshold(self) -> Decimal:
        return AaveV3CoreLib.total_liquidation_threshold(self.collateral_amount, self._risk_parameters)

    @property
    def current_ltv(self) -> Decimal:
        return AaveV3CoreLib.current_ltv(self.collateral_amount, self._risk_parameters)

    @property
    def health_factor(self) -> Decimal:
        return AaveV3CoreLib.health_factor(self.collateral_amount, self.borrows_amount, self._risk_parameters)

    @property
    def supply_apy(self) -> Decimal:
        rate_dict: Dict[TokenInfo, Decimal] = {}
        for k in self.supplies.keys():
            rate_dict[k.token] = self._market_status.tokens[k.token].liquidity_rate

        return AaveV3CoreLib.get_apy(self.supplies_amount, rate_dict)

    @property
    def borrow_apy(self) -> Decimal:
        rate_dict: Dict[TokenInfo, Decimal] = {}
        for k in self._borrows.keys():
            if k.interest_rate_mode == InterestRateMode.variable:
                rate_dict[k.token] = self._market_status.tokens[k.token].variable_borrow_rate
            else:
                rate_dict[k.token] = self._market_status.tokens[k.token].stable_borrow_rate

        return AaveV3CoreLib.get_apy(self.borrows_amount, rate_dict)

    @property
    def total_apy(self) -> Decimal:
        total_supplies = sum(self.supplies_amount.values())
        total_borrows = sum(self.borrows_amount.values())
        supply_apy = self.supply_apy
        borrow_apy = self.borrow_apy
        return AaveV3CoreLib.safe_div(supply_apy * total_supplies - borrow_apy * total_borrows, total_supplies - total_borrows)

    def add_token(self, token_info: TokenInfo | List[TokenInfo]):
        if not isinstance(token_info, list):
            token_info = [token_info]
        for t in token_info:
            self._tokens.add(t)

    def get_market_balance(self) -> AaveBalance:
        """
        get market asset balance
        :return:
        :rtype:
        """
        supplys = self.supplies
        borrows = self.borrows

        supplies_value_sum = sum(self.supplies_amount.values())
        borrows_value_sum = sum(self.borrows_amount.values())
        net_worth = supplies_value_sum - borrows_value_sum

        supply_apy = self.supply_apy
        borrow_apy = self.borrow_apy
        net_apy = AaveV3CoreLib.safe_div(supply_apy * supplies_value_sum - borrow_apy * borrows_value_sum, supplies_value_sum - borrows_value_sum)

        return AaveBalance(
            net_value=net_worth,
            supplys=supplys,
            borrows=borrows,
            liquidation_threshold=self.liquidation_threshold,
            health_factor=self.health_factor,
            borrow_balance=borrows_value_sum,
            supply_balance=supplies_value_sum,
            collateral_balance=sum(self.collateral_amount.values()),
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
        if collateral:
            require(self._risk_parameters[token.name].canCollateral, "Can not supplied as collateral")
        #  calc in pool value
        pool_amount = AaveV3CoreLib.get_base_amount(amount, self._market_status.tokens[token].liquidity_index)

        self.broker.subtract_from_balance(token, amount)

        key = SupplyKey(token)
        if key not in self._supplies:
            self._supplies[key] = SupplyInfo(base_amount=Decimal(0), collateral=collateral)
        self._supplies[key].base_amount += pool_amount

        self._supply_amount_cache = None
        self._collateral_cache = None

    def change_collateral(self, token: TokenInfo, collateral: bool):
        old_collateral = self._supplies[SupplyKey(token)].collateral
        if old_collateral == collateral:
            return
        self._supplies[SupplyKey(token)].collateral = collateral
        self._collateral_cache = None

        if (not collateral) and self.health_factor > AaveV3Market.HEALTH_FACTOR_LIQUIDATION_THRESHOLD:
            # rollback
            self._supplies[SupplyKey(token)].collateral = old_collateral
            self._collateral_cache = None
            raise DemeterError("health factor lower than liquidation threshold")

    def withdraw(self):
        self._supply_amount_cache = None
        self._collateral_cache = None

        pass

    def borrow(self, token: TokenInfo, amount: Decimal, interest_rate_mode: InterestRateMode):
        # check

        require(self._risk_parameters.loc[token.name, "canBorrow"], f"borrow is not enabled for {token.name}")
        collateral_balance = sum(self.collateral_amount.values())
        require(collateral_balance != 0, "collateral balance is zero")
        current_ltv = self.current_ltv
        require(current_ltv != 0, "ltv validation failed")

        require(self.health_factor > AaveV3Market.HEALTH_FACTOR_LIQUIDATION_THRESHOLD, "health factor lower than liquidation threshold")

        value = amount * self._price_status[token.name]
        collateral_needed = sum(self.borrows.values()) + value / current_ltv
        require(collateral_needed <= collateral_balance, "collateral cannot cover new borrow")

        if interest_rate_mode == InterestRateMode.stable:
            require(self._risk_parameters.loc[token.name, "canBorrowStable"], "stable borrowing not enabled")

            is_using_as_collateral = (token in self._supplies) and (self._supplies[SupplyKey(token)].collateral is True)

            require(
                (not is_using_as_collateral) or self._risk_parameters[token.name, "LTV"] == 0 or amount > self.broker.get_token_balance(token),
                "collateral same as borrowing currency",
            )
            # ignore pool amount check, I don't have pool amount

        # do borrow
        base_amount = amount / self._market_status.tokens[token].variable_borrow_index

        key = BorrowKey(token, interest_rate_mode)
        if key not in self._borrows:
            self._borrows[key] = BorrowInfo(Decimal(0))
        self._borrows[key].base_amount += base_amount

        self.broker.add_to_balance(token, amount)

        self._borrows_amount_cache = None
        pass

    def repay(self):
        self._borrows_amount_cache = None

        pass

    def _liquidate(self):
        self._borrows_amount_cache = None
        self._supply_amount_cache = None
        self._collateral_cache = None

        pass
