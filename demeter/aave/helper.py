import os
from _decimal import Decimal
from typing import Dict

import pandas as pd

from demeter import DemeterError
from demeter.aave._typing import RiskParameter

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


def load_risk_parameter(token_setting_path:str) -> pd.DataFrame | Dict[str, RiskParameter]:
    """
    | Load risk parameter, and convert float to decimal.
    | Files are downloaded from: https://www.config.fyi, please choose the right chain

    :param token_setting_path: risk parameter file path
    :type token_setting_path: str
    :return: risk parameter dataframe
    :rtype: DataFrame | Dict[str, RiskParameter]
    """
    path = os.path.join(token_setting_path)
    if not os.path.exists(path):
        raise DemeterError(f"risk parameter file {path} not exist, please download csv from https://www.config.fyi/")
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

    rp["LTV"] = rp["LTV"].str.rstrip("%").apply(lambda x: Decimal(x)) / 100
    rp["liqBonus"] = rp["liqBonus"].str.rstrip("%").apply(lambda x: Decimal(x)) / 100
    rp["liqThereshold"] = rp["liqThereshold"].str.rstrip("%").apply(lambda x: Decimal(x)) / 100
    rp = rp.set_index("symbol")
    return rp
