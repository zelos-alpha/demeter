import os
import token
from _decimal import Decimal
from datetime import datetime
from typing import Dict, List

import pandas as pd

from ._typing import AaveBalance, SupplyInfo, BorrowInfo, AaveV3PoolStatus, Supply, Borrow, InterestRateMode, RiskParameter
from .core import AaveV3CoreLib
from .. import MarketInfo, DECIMAL_0, DemeterError, TokenInfo
from .._typing import ChainType
from ..broker import Market, BaseAction, MarketStatus, MarketBalance

DEFAULT_DATA_PATH = "./data"


class AaveV3Market(Market):
    def __init__(self, market_info: MarketInfo, chain: ChainType, token_setting_path: str = "./aave_risk_parameters"):
        super().__init__(market_info=market_info)
        self._tokens: List[TokenInfo] = []
        self._supplies: Dict[TokenInfo, SupplyInfo] = {}
        self._borrows: Dict[TokenInfo, BorrowInfo] = {}
        self._market_status: pd.Series | AaveV3PoolStatus = AaveV3PoolStatus(None, {})
        self.health_factor = 0

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

        self._risk_parameters: pd.DataFrame | Dict[str, RiskParameter] = self._load_risk_parameter(chain, token_setting_path)

    def __str__(self):
        pass

    def _load_risk_parameter(self, chain: ChainType, token_setting_path) -> pd.DataFrame | Dict[str, RiskParameter]:
        path = os.path.join(token_setting_path, chain.value + ".csv")
        if not os.path.exists(path):
            raise DemeterError(
                f"risk parameter file {path} not exist, please download csv in https://www.config.fyi/ and save as file name [chain name].csv"
            )
        rp = pd.read_csv(path, sep=";")
        rp = rp[
            [
                "symbol",
                "canCollateral",
                "LTV",
                "liqThereshold",
                "liqBonus",
                "reserveFactor",
                "canBorrow",
                "optimalUtilization",
                "canBorrowStable",
                "debtCeiling",
                "supplyCap",
                "borrowCap",
                "eModeLtv",
                "eModeLiquidationThereshold",
                "eModeLiquidationBonus",
                "borrowableInIsolation",
            ]
        ]
        rp["LTV"] = rp["LTV"].str.rstrip("%").astype(float) / 100
        rp["liqThereshold"] = rp["liqThereshold"].str.rstrip("%").astype(float) / 100

        return rp

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

    def set_data(self, token: TokenInfo, value: pd.DataFrame):
        if isinstance(value, pd.DataFrame):
            value.columns = pd.MultiIndex.from_tuples([(token.name, c) for c in value.columns])
            self._data = pd.concat([self._data, value], axis="columns")
        else:
            raise ValueError()

    @data.setter
    def data(self, value):
        raise NotImplementedError("Aave market doesn't support set data with setter, please use set_data instead")

    @property
    def tokens(self) -> List[TokenInfo]:
        return self._tokens

    @tokens.setter
    def tokens(self, value: List[TokenInfo]):
        self._tokens = value

    @property
    def supplies(self) -> Dict[TokenInfo, Supply]:
        supply_dict: Dict[TokenInfo, Supply] = {}

        for token, supply_info in self._supplies.items():
            amount = supply_info.pool_amount * self._market_status.tokens[token].liquidity_index
            supply_value = Supply(
                token=token,
                pool_amount=supply_info.pool_amount,
                collateral=supply_info.collateral,
                amount=amount,
                apy=AaveV3CoreLib.rate_to_apy(self._market_status.tokens[token].liquidity_rate),
                token_base_amount=amount * self._price_status[token.name],
            )
            supply_dict[token] = supply_value
        return supply_dict

    @property
    def borrows(self) -> Dict[TokenInfo, Borrow]:
        borrow_dict = {}

        for token, borrow_info in self._borrows.items():
            amount = borrow_info.pool_amount * self.market_status.tokens[token].variable_borrow_index
            borrow_value = Borrow(
                token=token,
                pool_amount=borrow_info.pool_amount,
                interest_rate_mode=borrow_info.interest_rate_mode,
                amount=amount,
                apy=AaveV3CoreLib.rate_to_apy(
                    self.market_status.tokens[token].variable_borrow_rate
                    if borrow_info.interest_rate_mode == InterestRateMode.variable
                    else self.market_status.tokens[token].stable_borrow_rate
                ),
                token_base_amount=amount * self._price_status[token.name],
            )
            borrow_dict[token] = borrow_value

        return borrow_dict

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

    def get_liquidation_threshold(self, total_supplies: Dict[TokenInfo, Supply] = None) -> Decimal:
        if total_supplies is None:
            total_supplies = self.supplies

        sum_amount = DECIMAL_0
        rate = DECIMAL_0
        for s in total_supplies.values():
            sum_amount += s.amount
            rate += s.amount * self._risk_parameters[s.token.name].liqThereshold
        if sum_amount == 0:
            return Decimal("Infinity")
        return rate / sum_amount

    def get_market_balance(self, prices: pd.Series | Dict[str, Decimal]) -> AaveBalance:
        """
        get market asset balance
        :param prices: current price of each token
        :type prices: pd.Series | Dict[str, Decimal]
        :return:
        :rtype:
        """
        supplys = self.supplies
        borrows = self.borrows

        total_supplies = sum([v.amount for v in supplys.values()])
        total_borrows = sum([v.amount for v in borrows.values()])
        collateral = sum(map(lambda v: v.amount, filter(lambda v: v.collateral, supplys.values())))
        net_worth = total_supplies - total_borrows

        health_factor: Decimal
        supply_apy: Decimal
        delt_apy: Decimal
        net_apy: Decimal

        return AaveBalance(
            supplys=supplys,
            borrows=borrows,
            liquidation_threshold=self.get_liquidation_threshold(supplys),
            health_factor=None,
            total_borrows=total_borrows,
            total_supplies=total_supplies,
            collateral=collateral,
            net_worth=net_worth,
            current_ltv=None,
            supply_apy=None,
            delt_apy=None,
            net_apy=None,
        )

    def check_before_test(self):
        """
        do some check for this market before back test start
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
        pool_amount = AaveV3CoreLib.net_value_in_pool(amount, self._market_status.tokens[token].liquidity_index)

        if token in self._supplies:
            self._supplies[token].pool_amount += pool_amount
            pass
        else:
            # update self.supplies
            supply_item = SupplyInfo(pool_amount=pool_amount, collateral=collateral)
            self._supplies[token] = supply_item
            pass

    def change_collateral(self, token: TokenInfo, collateral: bool):
        self._supplies[token].collateral = collateral

    def withdraw(self):
        pass

    def borrow(self):
        pass

    def repay(self):
        pass

    def _liquidate(self):
        pass
