import json
import os
import token
from _decimal import Decimal
from datetime import datetime, date, timedelta
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
    AaveMarketDescription,
    AaveMarketStatus,
)
from .core import AaveV3CoreLib
from .. import DemeterError, TokenInfo
from .._typing import DECIMAL_0, UnitDecimal
from ..broker import Market, MarketStatus, MarketInfo
from ..utils import get_formatted_predefined, STYLE, get_formatted_from_dict
from ..utils.application import require, float_param_formatter, to_decimal

DEFAULT_DATA_PATH = "./data"


# TODO: price
# TODO: function comment
class AaveV3Market(Market):
    def __init__(self, market_info: MarketInfo, risk_parameters_path: str, tokens: List[TokenInfo] = None, data_path=DEFAULT_DATA_PATH):
        tokens = tokens if token is not None else []
        super().__init__(market_info=market_info)
        self._supplies: Dict[SupplyKey, SupplyInfo] = {}
        self._borrows: Dict[BorrowKey, BorrowInfo] = {}

        self._risk_parameters: pd.DataFrame | Dict[str, RiskParameter] = helper.load_risk_parameter(risk_parameters_path)
        self.data_path: str = data_path

        self._collaterals_amount_cache = DictCache()
        self._supplies_amount_cache = DictCache()
        self._supplies_cache = DictCache()
        self._borrows_amount_cache = DictCache()
        self._borrows_cache = DictCache()

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
        return json.dumps(self.description()._asdict())

    def description(self):
        return AaveMarketDescription(type(self).__name__, self._market_info.name, len(self._supplies), len(self._borrows))

    @property
    def market_info(self) -> MarketInfo:
        return self._market_info

    @property
    def data(self) -> pd.DataFrame:
        """
        environment data
        :return:
        :rtype:
        """
        return self._data

    @property
    def risk_parameters(self) -> pd.DataFrame:
        return self._risk_parameters

    def set_token_data(self, token_info: TokenInfo, value: pd.DataFrame):
        value = value.applymap(to_decimal)
        if isinstance(value, pd.DataFrame):
            value.columns = pd.MultiIndex.from_tuples([(token_info.name, c) for c in value.columns])
            self._data = pd.concat([self._data, value], axis="columns")
        else:
            raise ValueError()

    def load_data(self, chain: str, token_info_list: List[TokenInfo], start_date: date, end_date: date):
        self.logger.info(f"start load files from {start_date} to {end_date}...")
        for token_info in token_info_list:
            day = start_date
            df = pd.DataFrame()
            if token_info.address == "":
                raise DemeterError(f"address of {token_info.name} not set")
            while day <= end_date:
                path = os.path.join(
                    self.data_path,
                    f"{chain.lower()}-aave_v3-{token_info.address}-{day.strftime('%Y-%m-%d')}.minute.csv",
                )
                if not os.path.exists(path):
                    raise IOError(f"resource file {path} not found, please download with demeter-fetch: https://github.com/zelos-alpha/demeter-fetch")
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

    @data.setter
    def data(self, value):
        raise NotImplementedError("Aave market doesn't support set data with setter, please use set_token_data instead")

    @property
    def tokens(self) -> Set[TokenInfo]:
        return self._tokens

    @property
    def supplies_value(self) -> Dict[SupplyKey, Decimal]:
        if self._supplies_amount_cache.empty:
            for k, v in self._supplies.items():
                self._supplies_amount_cache.set(
                    k,
                    AaveV3CoreLib.get_amount(v.base_amount, self._market_status.data[k.token.name].liquidity_index)
                    * self._price_status[k.token.name],
                )
        return self._supplies_amount_cache.data

    @property
    def total_supply_value(self) -> Decimal:
        return Decimal(sum(self.supplies_value.values()))

    @property
    def collateral_value(self) -> Dict[SupplyKey, Decimal]:
        if self._collaterals_amount_cache.empty:
            for k, v in self._supplies.items():
                if v.collateral:
                    self._collaterals_amount_cache.set(k, self.supplies_value[k])
        return self._collaterals_amount_cache.data

    @property
    def total_collateral_value(self) -> Decimal:
        return Decimal(sum(self.collateral_value.values()))

    @property
    def borrows_value(self) -> Dict[BorrowKey, Decimal]:
        if self._borrows_amount_cache.empty:
            for k, v in self._borrows.items():
                self._borrows_amount_cache.set(
                    k,
                    AaveV3CoreLib.get_amount(v.base_amount, self._market_status.data[k.token.name].variable_borrow_index)
                    * self._price_status[k.token.name],
                )
        return self._borrows_amount_cache.data

    @property
    def total_borrows_value(self) -> Decimal:
        return Decimal(sum(self.borrows_value.values()))

    @property
    def supplies(self) -> Dict[SupplyKey, Supply]:
        if self._supplies_cache.empty:
            for key in self._supplies.keys():
                self._supplies_cache.set(key, self.get_supply(supply_key=key))
        return self._supplies_cache.data

    @property
    def supply_keys(self) -> List[SupplyKey]:
        return list(self._supplies.keys())

    @property
    def borrows(self) -> Dict[BorrowKey, Borrow]:
        if self._borrows_cache.empty:
            for key in self._borrows.keys():
                self._borrows_cache.set(key, self.get_borrow(key))
        return self._borrows_cache.data

    @property
    def borrow_keys(self) -> List[BorrowKey]:
        return list(self._borrows.keys())

    def set_market_status(
        self,
        data: MarketStatus,
        price: pd.Series,
    ):
        """
        set up market status, such as liquidity, price
        :param timestamp: current timestamp
        :type timestamp: datetime
        :param data: market status
        :type data: pd.Series | MarketStatus
        """
        if data.data is None:
            data.data = self.data.loc[data.timestamp]
        self._market_status = data

        self._price_status: pd.Series = price

        self._borrows_amount_cache.reset()
        self._supplies_amount_cache.reset()
        self._collaterals_amount_cache.reset()
        self._borrows_cache.reset()
        self._supplies_cache.reset()

        self.has_update = False

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
            rate_dict[k.token] = self._market_status.data[k.token.name].liquidity_rate

        return AaveV3CoreLib.get_apy(self.supplies_value, rate_dict)

    @property
    def borrow_apy(self) -> Decimal:
        rate_dict: Dict[TokenInfo, Decimal] = {}
        for k in self._borrows.keys():
            if k.interest_rate_mode == InterestRateMode.variable:
                rate_dict[k.token] = self._market_status.data[k.token.name].variable_borrow_rate
            else:
                rate_dict[k.token] = self._market_status.data[k.token.name].stable_borrow_rate

        return AaveV3CoreLib.get_apy(self.borrows_value, rate_dict)

    @property
    def total_apy(self) -> Decimal:
        total_supplies = self.total_supply_value
        total_borrows = self.total_borrows_value
        supply_apy = self.supply_apy
        borrow_apy = self.borrow_apy
        return AaveV3CoreLib.safe_div_zero(supply_apy * total_supplies - borrow_apy * total_borrows, total_supplies - total_borrows)

    def get_supply(self, supply_key: SupplyKey = None, token_info: TokenInfo = None) -> Supply:
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

    def get_borrow(self, borrow_key: BorrowKey):
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
        if not isinstance(token_info, list):
            token_info = [token_info]
        for t in token_info:
            self._tokens.add(t)

    def get_market_balance(self, prices: pd.Series | Dict[str, Decimal] = None) -> AaveBalance:
        """
        get market asset balance
        :return:
        :rtype:
        """
        # supplys = self.supplies
        # borrows = self.borrows
        rounding = Decimal("0.0001")
        total_supplies = self.total_supply_value.quantize(rounding)
        total_borrows = self.total_borrows_value.quantize(rounding)
        net_worth = total_supplies - total_borrows

        supply_apy = self.supply_apy.quantize(rounding)
        borrow_apy = self.borrow_apy.quantize(rounding)
        net_apy = AaveV3CoreLib.safe_div_zero(supply_apy * total_supplies - borrow_apy * total_borrows, total_supplies - total_borrows)

        return AaveBalance(
            net_value=net_worth,
            supplys_count=len(self._supplies),
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
        super().check_market()
        require(len(self.tokens) > 0, "should set tokens")
        for t in self.tokens:
            for col in AaveV3Market.REQUIRED_DATA_COLUMN:
                require((t.name, col) in self.data.columns, f"{t.name}.{col} not found in data")

    def update(self):
        self._liquidate()

    @property
    def market_status(self) -> AaveMarketStatus:
        return self._market_status

    def formatted_str(self):
        value = get_formatted_predefined(f"{self.market_info.name}({type(self).__name__})", STYLE["header3"]) + "\n"
        token_dict = {"tokens": ",".join([t.name for t in self._tokens])}
        value += get_formatted_from_dict(token_dict) + "\n"
        balance = self.get_market_balance()
        value += (
            get_formatted_from_dict(
                {
                    "net_value": "{:.2f}".format(balance.net_value),
                    "health_factor": "{:.2f}".format(balance.health_factor),
                    "borrow_balance": "{:.2f}".format(balance.borrows_value),
                    "supply_balance": "{:.2f}".format(balance.supplies_value),
                    "collateral_balance": "{:.2f}".format(balance.collaterals_value),
                    "supply_apy": "{:.2f}".format(balance.supply_apy),
                    "borrow_apy": "{:.2f}".format(balance.borrow_apy),
                    "net_apy": "{:.2f}".format(balance.net_apy),
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
    @float_param_formatter
    def supply(self, token_info: TokenInfo, amount: Decimal | float, collateral: bool = True) -> SupplyKey:
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
                token=token_info,
                amount=UnitDecimal(amount, token_info.name),
                collateral=collateral,
                deposit_after=UnitDecimal(AaveV3CoreLib.get_amount(self._supplies[key].base_amount, token_status.liquidity_index), token_info.name),
            )
        )
        self.has_update = True

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

    def change_collateral(self, collateral: bool, supply_key: SupplyKey = None, token_info: TokenInfo = None) -> SupplyKey:
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
        self.has_update = True

        return key

    @float_param_formatter
    def withdraw(
        self,
        supply_key: SupplyKey = None,
        amount: Decimal | float = None,
        token_info: TokenInfo = None,
    ):
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
            self._supplies[key].base_amount -= AaveV3CoreLib.get_base_amount(amount, self._market_status.data[key.token.name].liquidity_index)
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
                token=token_info,
                amount=UnitDecimal(amount, token_info.name),
                deposit_after=UnitDecimal(AaveV3CoreLib.get_amount(final_base_amount, token_status.liquidity_index), token_info.name),
            )
        )
        self.has_update = True

        pass

    def get_max_withdraw_amount(self, supply_key: SupplyKey = None, token_info: TokenInfo = None) -> Decimal:
        key, token_info = AaveV3Market.__get_supply_key(supply_key, token_info)
        return self.supplies[key].amount - AaveV3CoreLib.get_min_withdraw_kept_amount(
            token_info, self.supplies_value, self.borrows_value, self._risk_parameters, self._price_status[token_info.name]
        )

    def get_max_borrow_amount(self, token_info: TokenInfo):
        value = AaveV3CoreLib.get_max_borrow_value(self.collateral_value, self.borrows_value, self.risk_parameters)
        return value / self._price_status[token_info.name]

    @float_param_formatter
    def borrow(
        self,
        token_info: TokenInfo,
        amount: Decimal | float = None,
        interest_rate_mode: InterestRateMode = InterestRateMode.variable,
    ) -> BorrowKey:
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

        require(self.health_factor > AaveV3CoreLib.HEALTH_FACTOR_LIQUIDATION_THRESHOLD, "health factor lower than liquidation threshold")

        value = amount * self._price_status.loc[token_info.name]
        collateral_needed = sum(self.borrows.values()) + value / current_ltv
        require(collateral_needed <= collateral_balance, "collateral cannot cover new borrow")

        if interest_rate_mode == InterestRateMode.stable:
            require(self._risk_parameters.loc[token_info.name, "canBorrowStable"], "stable borrowing not enabled")

            is_using_as_collateral = (token_info in self._supplies) and (self._supplies[SupplyKey(token_info)].collateral is True)

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
                token=token_info,
                amount=UnitDecimal(amount, token_info.name),
                interest_rate_mode=interest_rate_mode,
                debt_after=UnitDecimal(AaveV3CoreLib.get_amount(self._borrows[key].base_amount, token_status.variable_borrow_index), token_info.name),
            )
        )
        self.has_update = True

        return key

    def get_max_repay_amount(self, key: BorrowKey = None, token_info: TokenInfo = None, interest_rate_mode: InterestRateMode = None) -> Decimal:
        (key, _, _) = AaveV3Market.__get_borrow_key(key, token_info, interest_rate_mode)
        return AaveV3CoreLib.get_amount(self._borrows[key].base_amount, self.market_status.data[key.token.name].variable_borrow_index)

    @staticmethod
    def __get_borrow_key(key: BorrowKey = None, token_info: TokenInfo = None, interest_rate_mode: InterestRateMode = None):
        if key is None:
            if token_info is None:
                raise DemeterError("either key or token should be filled")
            key = BorrowKey(token_info, interest_rate_mode)
        token_info = key.token
        interest_rate_mode = key.interest_rate_mode
        return key, token_info, interest_rate_mode

    def _get_swap_amount(self, from_token: TokenInfo, to_token: TokenInfo, amount: Decimal, swap_fee=0):
        return amount * (1 - swap_fee) * self._price_status.loc[from_token.name] / self._price_status.loc[to_token.name]

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
            require(self.supplies[repay_collateral_key].collateral, f"token {repay_collateral_token} is not in collateral")

            required_amount_in_collateral_token = self._get_swap_amount(borrow_token, repay_collateral_token, payback_amount)
            supply = self.get_supply(supply_key=repay_collateral_key)
            if required_amount_in_collateral_token > supply.amount:
                # contract will change payback amount instead of raise a error
                payback_amount = self._get_swap_amount(repay_collateral_token, borrow_token, supply.amount)

        payback_base_amount = AaveV3CoreLib.get_base_amount(payback_amount, token_status.variable_borrow_index)

        require(payback_base_amount != 0, "invalid amount")
        require(self._borrows[key] != 0, "no debt of selected type")
        require(self._borrows[key].base_amount >= payback_base_amount, "amount exceed debt")
        if repay_with_collateral:
            payback_amount_in_collateral = self._get_swap_amount(borrow_token, repay_collateral_token, payback_amount)
            self.__sub_supply_amount(SupplyKey(repay_collateral_token), payback_amount_in_collateral)
        else:
            self.broker.subtract_from_balance(borrow_token, payback_amount)
        debt = self.__sub_borrow_amount(key, payback_amount)
        self._record_action(
            RepayAction(
                market=self.market_info,
                token=borrow_token,
                amount=UnitDecimal(payback_amount, borrow_token.name),
                interest_rate_mode=interest_rate_mode,
                debt_after=UnitDecimal(AaveV3CoreLib.get_amount(debt, token_status.variable_borrow_index), borrow_token.name),
            )
        )
        self.has_update = True

        pass

    def __sub_supply_amount(self, key: SupplyKey, amount: Decimal) -> Decimal:
        if key not in self._supplies:
            if amount == Decimal(0):
                return Decimal(0)
            else:
                raise DemeterError(f"{key} not exist in supplies")
        self._supplies[key].base_amount = helper.sub_base_amount(
            self._supplies[key].base_amount, AaveV3CoreLib.get_base_amount(amount, self._market_status.data[key.token.name].liquidity_index)
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
            self._borrows[key].base_amount, AaveV3CoreLib.get_base_amount(amount, self._market_status.data[key.token.name].variable_borrow_index)
        )
        self._borrows_amount_cache.reset()
        self._borrows_cache.reset()
        if self._borrows[key].base_amount == DECIMAL_0:
            del self._borrows[key]
            return DECIMAL_0
        else:
            return self._borrows[key].base_amount

    def _liquidate(self):
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
                self._do_liquidate(max_supply_key.token, min_borrow_key.token, min_borrow_value, health_factor)
            except AssertionError:
                # if a liquidated is rejected, choose another delt token to liquidate
                pass
            health_factor = self.health_factor
        self.has_update = True

    def _do_liquidate(self, collateral_token: TokenInfo, delt_token: TokenInfo, delt_to_cover: Decimal, health_factor: Decimal):
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
            if health_factor > AaveV3CoreLib.CLOSE_FACTOR_HF_THRESHOLD
            else AaveV3CoreLib.MAX_LIQUIDATION_CLOSE_FACTOR
        )
        max_liquidatable_debt = total_debt * close_factor
        actual_debt_to_liquidate = max_liquidatable_debt if delt_to_cover > max_liquidatable_debt else delt_to_cover

        # validate delt
        is_collateral_enabled = self._risk_parameters.loc[collateral_token.name].liqThereshold != 0 and self._supplies[collateral_key].collateral

        require(is_collateral_enabled, "collateral cannot be liquidated")
        require(total_debt != DECIMAL_0, "specified currency not borrowed by user")

        user_collateral_balance = (
            self._supplies[SupplyKey(collateral_token)].base_amount * self._market_status.data[collateral_token.name].liquidity_index
        )

        # calculate actual amount
        should_collateral = self._price_status.loc[delt_token.name] * actual_debt_to_liquidate / self._price_status.loc[collateral_token.name]
        max_collateral_to_liquidate = should_collateral * (1 + liquidation_bonus)

        if max_collateral_to_liquidate > user_collateral_balance:
            actual_collateral_to_liquidate = user_collateral_balance
            actual_debt_to_liquidate = (self._price_status.loc[collateral_token.name] * actual_collateral_to_liquidate) / (
                self._price_status.loc[delt_token.name] * (1 + liquidation_bonus)
            )
        else:
            actual_collateral_to_liquidate = max_collateral_to_liquidate
            actual_debt_to_liquidate = actual_debt_to_liquidate
        self._supplies[collateral_key].base_amount = helper.sub_base_amount(
            self._supplies[collateral_key].base_amount, AaveV3CoreLib.get_base_amount(actual_collateral_to_liquidate, supply_index)
        )

        if self._supplies[collateral_key].base_amount == 0:
            del self._supplies[collateral_key]
        if variable_delt > actual_debt_to_liquidate:
            vari_debt_remaining_base = self.__sub_borrow_amount(variable_key, actual_debt_to_liquidate)
            stable_debt_remaining_base = self._borrows[stable_key].base_amount if stable_key in self._borrows else DECIMAL_0
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
                collateral_token=collateral_token,
                debt_token=delt_token,
                delt_to_cover=UnitDecimal(delt_to_cover, delt_token.name),
                collateral_used=UnitDecimal(actual_collateral_to_liquidate, collateral_token.name),
                variable_delt_liquidated=UnitDecimal(vari_debt_liquidated, delt_token.name),
                stable_delt_liquidated=UnitDecimal(stable_debt_liquidated, delt_token.name),
                health_factor_before=health_factor,
                health_factor_after=self.health_factor,
                collateral_after=UnitDecimal(
                    AaveV3CoreLib.get_amount(
                        self._supplies[collateral_key].base_amount if collateral_key in self._supplies else DECIMAL_0, supply_index
                    ),
                    collateral_token.name,
                ),
                variable_debt_after=UnitDecimal(AaveV3CoreLib.get_amount(vari_debt_remaining_base, borrow_index), delt_token.name),
                stable_delt_after=UnitDecimal(AaveV3CoreLib.get_amount(stable_debt_remaining_base, borrow_index), delt_token.name),
            )
        )
