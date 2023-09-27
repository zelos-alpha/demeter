import os
from _decimal import Decimal
from typing import Dict

import pandas as pd

from demeter import DemeterError
from demeter.aave._typing import RiskParameter


def load_risk_parameter(token_setting_path) -> pd.DataFrame | Dict[str, RiskParameter]:
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
