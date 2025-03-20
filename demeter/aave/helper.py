import logging
import os
from _decimal import Decimal
from datetime import timedelta, date
from typing import Dict, List

import pandas as pd

from demeter import DemeterError, ChainType, TokenInfo, MarketTypeEnum
from demeter.aave._typing import RiskParameter
from demeter.data import CacheManager
from demeter.utils import to_decimal

MIN_TOKEN_VALUE = (1e-18) - (1e-27)


def sub_base_amount(old_v, value):
    """
    | Subtract base amount.
    | Usually, max token decimal is 18. so if token value is below 1e-18, we consider it's 0
    | It's necessary because number here is kept in decimal instead of int256. so there will be calculation errors.
    """

    new_v = old_v - value
    if new_v < MIN_TOKEN_VALUE:
        return 0
    else:
        return new_v


REQUIRED_DATA_COLUMN = [
    "liquidity_rate",
    "stable_borrow_rate",
    "variable_borrow_rate",
    "liquidity_index",
    "variable_borrow_index",
]


def load_risk_parameter(token_setting_path: str) -> pd.DataFrame | Dict[str, RiskParameter]:
    """
    | Load risk parameter, and convert float to decimal.
    | Download by "demeter-fetch aave -h"

    :param token_setting_path: risk parameter file path
    :type token_setting_path: str
    :return: risk parameter dataframe
    :rtype: DataFrame | Dict[str, RiskParameter]
    """
    path = os.path.join(token_setting_path)
    if not os.path.exists(path):
        # raise DemeterError(f"risk parameter file {path} not exist, please download csv from https://www.config.fyi/")
        raise DemeterError(f"risk parameter file {path} not exist, please download csv with 'demeter-fetch aave -h'")
    rp = pd.read_csv(path)
    usdc = rp["symbol"] == "USDC"
    rp.loc[usdc, "symbol"] = rp.loc[usdc, "name"].apply(lambda x: "USDC" if x == "USD Coin" else "USDC.e")
    rp = rp[
        [
            "symbol",  # "symbol",
            "usageAsCollateralEnabled",  # "canCollateral",
            "baseLTVasCollateral",  # "LTV",
            "reserveLiquidationThreshold",  # "liqThereshold",
            "reserveLiquidationBonus",  # "liqBonus",
            "reserveFactor",  # "reserveFactor",
            "borrowingEnabled",  # "canBorrow",
            "optimalUsageRatio",  # "optimalUtilization",
            "variableRateSlope1",
            "variableRateSlope2",
            "baseVariableBorrowRate",
            "supplyCap",  # "supplyCap",
            "borrowCap",  # "borrowCap",
            "borrowableInIsolation",  # "borrowableInIsolation",
            "flashLoanEnabled",
        ]
    ]

    rp["reserveLiquidationBonus"] = rp["reserveLiquidationBonus"].apply(lambda x: Decimal(x - 10000)) / 10000
    rp[["baseLTVasCollateral", "reserveLiquidationThreshold", "reserveFactor"]] = (
        rp[["baseLTVasCollateral", "reserveLiquidationThreshold", "reserveFactor"]].map(lambda x: Decimal(x)) / 10000
    )
    rp[["optimalUsageRatio", "baseVariableBorrowRate", "variableRateSlope1", "variableRateSlope2"]] = (
        rp[["optimalUsageRatio", "baseVariableBorrowRate", "variableRateSlope1", "variableRateSlope2"]].map(
            lambda x: Decimal(x)
        )
        / 10**27
    )

    rp = rp.set_index("symbol")
    return rp


def load_aave_data(
    chain: ChainType, token_info_list: List[TokenInfo], start_date: date, end_date: date, data_path: str
):
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
    :param data_path: path to load data
    :type data_path: str
    """
    logger = logging.getLogger("Aave data")
    logger.info(f"{MarketTypeEnum.aave_v3.name} start load files from {start_date} to {end_date}...")
    data = pd.DataFrame()
    for token_info in token_info_list:
        cache_key = CacheManager.get_cache_key(
            MarketTypeEnum.aave_v3.name, start_date, end_date, chain.name, token_info.name
        )
        cache_df = CacheManager.load(cache_key)
        if cache_df is not None:
            data = _set_token_data(data, token_info, cache_df)
            continue

        day = start_date
        df = pd.DataFrame()
        if token_info.address == "":
            raise DemeterError(f"address of {token_info.name} not set")
        while day <= end_date:
            path = os.path.join(
                data_path,
                f"{chain.name.lower()}-aave_v3-{token_info.address}-{day.strftime('%Y-%m-%d')}.minute.csv",
            )
            if not os.path.exists(path):
                raise IOError(
                    f"resource file {path} not found, please download with demeter-fetch: https://github.com/zelos-alpha/demeter-fetch"
                )
            csv_converters = {n: to_decimal for n in REQUIRED_DATA_COLUMN}
            day_df = pd.read_csv(
                path,
                converters=csv_converters,
                index_col=0,
                parse_dates=True,
            )

            df = pd.concat([df, day_df])
            day += timedelta(days=1)

        CacheManager.save(cache_key, df)
        data = _set_token_data(data, token_info, df)

    logger.info("data has been prepared")
    return data


def _set_token_data(data: pd.DataFrame | None, token_info: TokenInfo, token_data: pd.DataFrame) -> pd.DataFrame():
    """
    Set aave pool data of one token. Usually demeter-fetch will keep one csv file for each token.

    :param token_info: which token to set
    :type token_info: TokenInfo
    :param token_data: data
    :type token_data: DataFrame
    """
    if data is not None and token_info.name in data:
        raise DemeterError(f"{token_info.name} has already set to data")
    if isinstance(token_data, pd.DataFrame):
        token_data = token_data.map(to_decimal)
        token_data.columns = pd.MultiIndex.from_tuples([(token_info.name, c) for c in token_data.columns])
        data = pd.concat([data, token_data], axis="columns")
        return data
    else:
        raise ValueError()
