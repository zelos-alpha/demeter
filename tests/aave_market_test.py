import unittest
from _decimal import Decimal
from datetime import datetime

import pandas as pd

from demeter import MarketInfo, ChainType, TokenInfo
from demeter.aave._typing import AaveV3PoolStatus, AaveTokenStatus, SupplyInfo, BorrowInfo, InterestRateMode
from demeter.aave.core import AaveV3CoreLib
from demeter.aave.market import AaveV3Market
from demeter.broker._typing import MarketTypeEnum
from tests.common import assert_equal_with_error


def to_decimal(v: int) -> Decimal:
    return Decimal(v / 10**27)


class UniLpDataTest(unittest.TestCase):
    def test_load_risk_parameter(self):
        market = AaveV3Market(MarketInfo("aave_test", MarketTypeEnum.aave_v3), ChainType.polygon)
        pass

    def test_apy_to_rate(self):
        print(AaveV3CoreLib.rate_to_apy(0.054385544255370350575778874))

    def test_status_calc(self):
        usdt = TokenInfo("USDT", 6)
        dai = TokenInfo("DAI", 6)
        matic = TokenInfo("WMATIC", 18)

        market = AaveV3Market(MarketInfo("aave_test", MarketTypeEnum.aave_v3), ChainType.polygon, tokens=[usdt, dai, matic])
        timestamp = datetime(2023, 9, 12, 15)

        price = pd.DataFrame(data={"USDT": Decimal(0.999990), "DAI": Decimal(1), "WMATIC": Decimal(0.509952)}, index=[timestamp])

        pool_stat = AaveV3PoolStatus(timestamp, {})
        pool_stat.tokens[dai] = AaveTokenStatus(
            liquidity_rate=to_decimal(20721780596069986118711585),
            stable_borrow_rate=to_decimal(54183967335086321747448589),
            variable_borrow_rate=to_decimal(33471738680690573979588711),
            liquidity_index=to_decimal(1024896375683851651969973538),
            variable_borrow_index=to_decimal(1043477569752596545043775819),
        )
        pool_stat.tokens[usdt] = AaveTokenStatus(
            liquidity_rate=to_decimal(19374318747418950359017069),
            stable_borrow_rate=to_decimal(54385544255370350575778874),
            variable_borrow_rate=to_decimal(31166051358525919566436671),
            liquidity_index=to_decimal(1046424838969468347281558168),
            variable_borrow_index=to_decimal(1061829096134252340370625412),
        )
        pool_stat.tokens[matic] = AaveTokenStatus(
            liquidity_rate=to_decimal(34590050812934499694395450),
            stable_borrow_rate=to_decimal(81000000000000000000000000),
            variable_borrow_rate=to_decimal(59301392614184653189709969),
            liquidity_index=to_decimal(1033989834711222334753899684),
            variable_borrow_index=to_decimal(1091266512915678985090375114),
        )
        market.set_market_status(timestamp=timestamp, data=pool_stat, price=price.iloc[0])
        market._supplies[dai] = SupplyInfo(Decimal(97.56471188217428), True)
        market._supplies[matic] = SupplyInfo(Decimal(19.35174760735758), True)
        market._borrows[matic] = BorrowInfo(Decimal(4.583153411559582), InterestRateMode.variable)
        market._borrows[usdt] = BorrowInfo(Decimal(4.709392084139431), InterestRateMode.stable)
        stat = market.get_market_balance()
        print(stat)
        # supplies
        assert_equal_with_error(stat.supplys[dai].value, Decimal("99.99"), 0.001)
        assert_equal_with_error(stat.supplys[dai].apy, Decimal("0.02093"), 0.001)
        assert_equal_with_error(stat.supplys[dai].amount, Decimal("99.99"), 0.001)

        assert_equal_with_error(stat.supplys[matic].value, Decimal("10.21"), 0.001)
        assert_equal_with_error(stat.supplys[matic].apy, Decimal("0.0352"), 0.001)
        assert_equal_with_error(stat.supplys[matic].amount, Decimal("20.01"), 0.001)

        assert_equal_with_error(stat.supply_balance, Decimal("110.19"), 0.001)
        assert_equal_with_error(stat.supply_apy, Decimal("0.02226"), 0.001)
        assert_equal_with_error(stat.collateral_balance, Decimal("110.18877975"), 0.001)

        # borrows
        assert_equal_with_error(stat.borrows[usdt].value, Decimal("5"), 0.001)
        assert_equal_with_error(stat.borrows[usdt].apy, Decimal("0.0559"), 0.001)
        assert_equal_with_error(stat.borrows[usdt].amount, Decimal("5"), 0.001)

        assert_equal_with_error(stat.borrows[matic].value, Decimal("2.55"), 0.001)
        assert_equal_with_error(stat.borrows[matic].apy, Decimal("0.0611"), 0.001)
        assert_equal_with_error(stat.borrows[matic].amount, Decimal("5"), 0.001)

        assert_equal_with_error(stat.borrow_balance, Decimal("7.55"), 0.001)
        assert_equal_with_error(stat.borrow_apy, Decimal("0.0576"), 0.001)

        assert_equal_with_error(stat.health_factor, Decimal("11.711114759422364164"), 0.001)
        assert_equal_with_error(stat.liquidation_threshold, Decimal("0.8025"), 0.001)
        assert_equal_with_error(stat.current_ltv, Decimal("0.7525"), 0.001)
        assert_equal_with_error(stat.net_apy, Decimal("0.01965"), 0.001)

        self.assertTrue(assert_equal_with_error(stat.net_value, Decimal("102.64"), 0.001))


        # net_apy=Decimal('0.01683792283834931728886791969'))
