import unittest
from _decimal import Decimal
from datetime import datetime

import pandas as pd

from demeter import MarketInfo, ChainType, TokenInfo
from demeter.aave._typing import AaveV3PoolStatus, AaveTokenStatus, SupplyInfo, BorrowInfo, InterestRateMode
from demeter.aave.market import AaveV3Market
from demeter.broker._typing import MarketTypeEnum


def to_decimal(v: int) -> Decimal:
    return Decimal(v / 10**27)


class UniLpDataTest(unittest.TestCase):
    def test_load_risk_parameter(self):
        market = AaveV3Market(MarketInfo("aave_test", MarketTypeEnum.aave_v3), ChainType.polygon)
        pass

    def test_status_calc(self):
        usdt = TokenInfo("USDT", 6)
        dai = TokenInfo("DAI", 6)
        matic = TokenInfo("WMATIC", 18)

        market = AaveV3Market(MarketInfo("aave_test", MarketTypeEnum.aave_v3), ChainType.polygon, tokens=[usdt, dai, matic])
        timestamp = datetime(2023, 9, 12, 15)

        price = pd.DataFrame(data={"USDT": Decimal(0.999598), "DAI": Decimal(1), "WMATIC": Decimal(0.506555)}, index=[timestamp])

        pool_stat = AaveV3PoolStatus(timestamp, {})
        pool_stat.tokens[dai] = AaveTokenStatus(
            liquidity_rate=to_decimal(20618610459679756942997966),
            stable_borrow_rate=to_decimal(54173347710542180724910051),
            variable_borrow_rate=to_decimal(33386781684337445799280413),
            liquidity_index=to_decimal(1024839710712801476539512034),
            variable_borrow_index=to_decimal(1043383981539585578259609534),
        )
        pool_stat.tokens[usdt] = AaveTokenStatus(
            liquidity_rate=to_decimal(23719995286005250328109648),
            stable_borrow_rate=to_decimal(54360683940880674487519593),
            variable_borrow_rate=to_decimal(34885471527045395900156740),
            liquidity_index=to_decimal(1046358832776403596848245044),
            variable_borrow_index=to_decimal(1061730242601724774370383670),
        )
        pool_stat.tokens[matic] = AaveTokenStatus(
            liquidity_rate=to_decimal(25474751379557487782478702),
            stable_borrow_rate=to_decimal(49673900557777754599000492),
            variable_borrow_rate=to_decimal(32717303904444282193003448),
            liquidity_index=to_decimal(1026405399242023849353791296),
            variable_borrow_index=to_decimal(1040666653010712180520712643),
        )
        market.set_market_status(timestamp=timestamp, data=pool_stat, price=price.iloc[0])
        market._supplies[dai] = SupplyInfo(Decimal(97.5654356254924), True)
        market._supplies[matic] = SupplyInfo(Decimal(19.49312470196752), True)
        market._borrows[matic] = BorrowInfo(Decimal(4.805325370336146), InterestRateMode.variable)
        market._borrows[usdt] = BorrowInfo(Decimal(4.709392084139431), InterestRateMode.stable)
        stat = market.get_market_balance()

        print(stat)
