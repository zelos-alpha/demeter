from _decimal import Decimal
from datetime import datetime
from typing import Dict, List, Set

import pandas as pd

from . import helper
from ._typing import AaveBalance, SupplyInfo, BorrowInfo, AaveV3PoolStatus, Supply, Borrow, InterestRateMode, RiskParameter, SupplyKey, BorrowKey
from .core import AaveV3CoreLib
from .. import MarketInfo, DemeterError, TokenInfo
from .._typing import ChainType, DECIMAL_0
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
    def supplies_value(self) -> Dict[SupplyKey, Decimal]:
        if self._supply_amount_cache is None:
            self._supply_amount_cache = {}
            for k, v in self._supplies.items():
                self._supply_amount_cache[k] = (
                    AaveV3CoreLib.get_current_amount(v.base_amount, self._market_status.tokens[k.token].liquidity_index)
                    * self._price_status[k.token.name]
                )
        return self._supply_amount_cache

    @property
    def total_supply_value(self) -> Decimal:
        return Decimal(sum(self.supplies_value.values()))

    @property
    def collateral_value(self) -> Dict[SupplyKey, Decimal]:
        if self._collateral_cache is None:
            self._collateral_cache = {}
            for k, v in self._supplies.items():
                if v.collateral:
                    self._collateral_cache[k] = self.supplies_value[k]
        return self._collateral_cache

    @property
    def total_collateral_value(self) -> Decimal:
        return Decimal(sum(self.collateral_value.values()))

    @property
    def borrows_value(self) -> Dict[BorrowKey, Decimal]:
        if self._borrows_amount_cache is None:
            self._borrows_amount_cache = {}
            for k, v in self._borrows.items():
                self._borrows_amount_cache[k] = (
                    AaveV3CoreLib.get_current_amount(v.base_amount, self._market_status.tokens[k.token].variable_borrow_index)
                    * self._price_status[k.token.name]
                )
        return self._borrows_amount_cache

    @property
    def total_borrows_value(self) -> Decimal:
        return Decimal(sum(self.borrows_value.values()))

    @property
    def supplies(self) -> Dict[SupplyKey, Supply]:
        supply_dict: Dict[SupplyKey, Supply] = {}
        for key in self._supplies.keys():
            supply_dict[key] = self.get_supply(supply_key=key)
        return supply_dict

    @property
    def borrows(self) -> Dict[BorrowKey, Borrow]:
        borrow_dict: Dict[BorrowKey, Borrow] = {}
        for key in self._borrows.keys():
            borrow_dict[key] = self.get_borrow(key)
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
        return AaveV3CoreLib.total_liquidation_threshold(self.collateral_value, self._risk_parameters)

    @property
    def current_ltv(self) -> Decimal:
        return AaveV3CoreLib.current_ltv(self.collateral_value, self._risk_parameters)

    @property
    def health_factor(self) -> Decimal:
        return AaveV3CoreLib.health_factor(self.collateral_value, self.borrows_value, self._risk_parameters)

    @property
    def supply_apy(self) -> Decimal:
        rate_dict: Dict[TokenInfo, Decimal] = {}
        for k in self.supplies.keys():
            rate_dict[k.token] = self._market_status.tokens[k.token].liquidity_rate

        return AaveV3CoreLib.get_apy(self.supplies_value, rate_dict)

    @property
    def borrow_apy(self) -> Decimal:
        rate_dict: Dict[TokenInfo, Decimal] = {}
        for k in self._borrows.keys():
            if k.interest_rate_mode == InterestRateMode.variable:
                rate_dict[k.token] = self._market_status.tokens[k.token].variable_borrow_rate
            else:
                rate_dict[k.token] = self._market_status.tokens[k.token].stable_borrow_rate

        return AaveV3CoreLib.get_apy(self.borrows_value, rate_dict)

    @property
    def total_apy(self) -> Decimal:
        total_supplies = self.total_supply_value
        total_borrows = self.total_borrows_value
        supply_apy = self.supply_apy
        borrow_apy = self.borrow_apy
        return AaveV3CoreLib.safe_div(supply_apy * total_supplies - borrow_apy * total_borrows, total_supplies - total_borrows)

    def get_supply(self, supply_key: SupplyKey = None, token: TokenInfo = None) -> Supply:
        key, token = AaveV3Market.__get_supply_key(supply_key, token)
        supply_info = self._supplies[key]
        supply_value = Supply(
            token=token,
            base_amount=supply_info.base_amount,
            collateral=supply_info.collateral,
            amount=self.supplies_value[key] / self._price_status.loc[key.token.name],
            apy=AaveV3CoreLib.rate_to_apy(self._market_status.tokens[key.token].liquidity_rate),
            value=self.supplies_value[key],
        )
        return supply_value

    def get_borrow(self, borrow_key: BorrowKey):
        borrow_info = self._borrows[borrow_key]
        return Borrow(
            token=borrow_key.token,
            base_amount=borrow_info.base_amount,
            interest_rate_mode=borrow_info.interest_rate_mode,
            amount=self.borrows_value[borrow_key] / self._price_status.loc[key.token.name],
            apy=AaveV3CoreLib.rate_to_apy(
                self.market_status.tokens[borrow_key.token].variable_borrow_rate
                if borrow_key.interest_rate_mode == InterestRateMode.variable
                else self.market_status.tokens[borrow_key.token].stable_borrow_rate
            ),
            value=self.borrows_value[borrow_key],
        )

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

        total_supplies = self.total_supply_value
        total_borrows = self.total_borrows_value
        net_worth = total_supplies - total_borrows

        supply_apy = self.supply_apy
        borrow_apy = self.borrow_apy
        net_apy = AaveV3CoreLib.safe_div(supply_apy * total_supplies - borrow_apy * total_borrows, total_supplies - total_borrows)

        return AaveBalance(
            net_value=net_worth,
            supplys=supplys,
            borrows=borrows,
            liquidation_threshold=self.liquidation_threshold,
            health_factor=self.health_factor,
            borrow_balance=total_borrows,
            supply_balance=total_supplies,
            collateral_balance=self.total_collateral_value,
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

    def supply(self, token: TokenInfo, amount: Decimal, collateral: bool = True) -> SupplyKey:
        if collateral:
            require(self._risk_parameters[token.name].canCollateral, "Can not supplied as collateral")
        #  calc in pool value
        pool_amount = AaveV3CoreLib.get_base_amount(amount, self._market_status.tokens[token].liquidity_index)

        self.broker.subtract_from_balance(token, amount)

        key = SupplyKey(token)
        if key not in self._supplies:
            self._supplies[key] = SupplyInfo(base_amount=Decimal(0), collateral=collateral)
        else:
            require(self._supplies[key].collateral == collateral, "Collateral different from existing supply")
        self._supplies[key].base_amount += pool_amount

        self._supply_amount_cache = None
        self._collateral_cache = None

        return key

    @staticmethod
    def __get_supply_key(supply_key: SupplyKey = None, token: TokenInfo = None):
        if supply_key is not None:
            key = supply_key
            token = key.token
        elif token is not None:
            key = SupplyKey(token)
        else:
            raise DemeterError("supply_key or token should be specified")
        return key, token

    def change_collateral(self, collateral: bool, supply_key: SupplyKey = None, token: TokenInfo = None) -> SupplyKey:
        key, token = AaveV3Market.__get_supply_key(supply_key, token)
        old_collateral = self._supplies[key].collateral
        if old_collateral == collateral:
            return key

        self._supplies[key].collateral = collateral
        self._collateral_cache = None

        if (not collateral) and self.health_factor > AaveV3Market.HEALTH_FACTOR_LIQUIDATION_THRESHOLD:
            # rollback
            self._supplies[SupplyKey(token)].collateral = old_collateral
            raise DemeterError("health factor lower than liquidation threshold")
        return key

    def withdraw(self, supply_key: SupplyKey = None, token: TokenInfo = None, amount: Decimal = None): # TODO: amount should changed to Decimal| float
        key, token = AaveV3Market.__get_supply_key(supply_key, token)

        supply = self.get_supply(key)
        if amount is None:
            amount = supply.amount
        require(amount != 0, "invalid amount")
        require(amount <= supply.amount, "not enough available user balance")

        base_amount = amount / self._market_status.tokens[token].liquidity_index

        old_balance = self._supplies[key].base_amount

        self._supplies[key].base_amount -= base_amount
        self._supply_amount_cache = None

        # revert
        if self._supplies[key].collateral:
            self._collateral_cache = None
            if self.health_factor > AaveV3Market.HEALTH_FACTOR_LIQUIDATION_THRESHOLD:
                self._supplies[key].base_amount += old_balance
                raise DemeterError("health factor lower than liquidation threshold")

        self.broker.add_to_balance(token, amount)
        if self._supplies[key].base_amount == DECIMAL_0:
            del self._supplies[key]

        pass

    def borrow(self, token: TokenInfo, amount: Decimal, interest_rate_mode: InterestRateMode) -> BorrowKey:
        key = BorrowKey(token, interest_rate_mode)

        # check

        require(self._risk_parameters.loc[token.name, "canBorrow"], f"borrow is not enabled for {token.name}")
        collateral_balance = sum(self.collateral_value.values())
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
        base_amount = amount / self._market_status.tokens[token].variable_borrow_index # TODO : update this, consider decimal and ceiling/floor

        if key not in self._borrows:
            self._borrows[key] = BorrowInfo(DECIMAL_0)
        self._borrows[key].base_amount += base_amount

        self.broker.add_to_balance(token, amount)

        self._borrows_amount_cache = None
        return key

    def repay(self, amount: Decimal = None, key: BorrowKey = None, token: TokenInfo = None, interest_rate_mode: InterestRateMode = None):
        if key is None:
            if token is None:
                raise DemeterError("either key or token should be filled")
            key = BorrowKey(token, interest_rate_mode)
        token = key.token
        interest_rate_mode = key.interest_rate_mode

        borrow = self.get_borrow(key)

        if amount is None:
            amount = borrow.amount
        base_amount = amount / self._market_status.tokens[token].variable_borrow_index

        require(base_amount != 0, "invalid amount")
        require(self._borrows[key] != 0, "no debt of selected type")

        require(self._borrows[key].base_amount >= base_amount, "amount exceed debt")

        self.broker.subtract_from_balance(token, amount)
        self._borrows[key] -= base_amount
        self._borrows_amount_cache = None

        if self._borrows[key].base_amount == DECIMAL_0:
            del self._borrows[key]
        pass

    def _liquidate(self):
        self._borrows_amount_cache = None
        self._supply_amount_cache = None
        self._collateral_cache = None

        pass
