import math
from decimal import Decimal
from typing import Dict

import pandas as pd

from demeter.squeeth import VaultKey, Vault
from demeter.utils import console_text


def calc_twap_price(prices: pd.Series) -> Decimal:
    """
    Calc TWAP(time weighted average price) as uniswap oracle.

    :param prices: given price array.
    :type prices: Series
    :return: TWAP price
    :rtype: Decimal
    """
    logged = prices.apply(lambda x: math.log(x, 1.0001))
    logged_sum = logged.sum()
    power = logged_sum / len(prices)
    avg_price = math.pow(1.0001, power)

    return Decimal(avg_price)


def vault_to_dataframe(vaults: Dict[VaultKey, Vault]) -> pd.DataFrame:
    """
    convert supply dict to a dataframe
    """
    vault_dict = {
        "id": [],
        "collateral_amount": [],
        "osqth_short_amount": [],
        "uni_nft_id": [],
    }
    for k, v in vaults.items():
        vault_dict["id"].append(v.id)
        vault_dict["collateral_amount"].append(console_text.format_value(v.collateral_amount))
        vault_dict["osqth_short_amount"].append(console_text.format_value(v.osqth_short_amount))
        vault_dict["uni_nft_id"].append(str(v.uni_nft_id))
    return pd.DataFrame(vault_dict)
