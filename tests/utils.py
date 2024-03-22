from decimal import Decimal

import pandas as pd

from demeter.uniswap import UniLpMarket


def get_mock_data(market: UniLpMarket, tick, amount0=0, amount1=0, total_l=Decimal(0)):
    DATA_SIZE = 5
    index = pd.date_range("2022-10-8 8:0:0", periods=DATA_SIZE, freq="min")
    netAmount0 = pd.Series(data=[0] * DATA_SIZE, index=index)
    netAmount1 = pd.Series(data=[0] * DATA_SIZE, index=index)
    closeTick = pd.Series(data=[tick] * DATA_SIZE, index=index)
    openTick = pd.Series(data=[tick] * DATA_SIZE, index=index)
    lowestTick = pd.Series(data=[tick] * DATA_SIZE, index=index)
    highestTick = pd.Series(data=[tick] * DATA_SIZE, index=index)
    inAmount0 = pd.Series(data=[amount0] * DATA_SIZE, index=index)
    inAmount1 = pd.Series(data=[amount1] * DATA_SIZE, index=index)
    currentLiquidity = pd.Series(data=[Decimal(total_l)] * DATA_SIZE, index=index)
    df = pd.DataFrame(index=index)
    df["netAmount0"] = netAmount0
    df["netAmount1"] = netAmount1
    df["closeTick"] = closeTick
    df["openTick"] = openTick
    df["lowestTick"] = lowestTick
    df["highestTick"] = highestTick
    df["inAmount0"] = inAmount0
    df["inAmount1"] = inAmount1
    df["currentLiquidity"] = currentLiquidity
    market.add_statistic_column(df)
    return df
