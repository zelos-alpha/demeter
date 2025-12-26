import datetime
import unittest
import pprint
import pandas as pd

from demeter import TokenInfo, MarketInfo, MarketTypeEnum, ChainType, Broker
from demeter.gmx import GmxV2Pool, GmxV2PerpMarket, load_gmx_v2_data, get_price_from_v2_data
from demeter.gmx._typing2 import GmxV2LpMarketStatus
from demeter.gmx.gmx_v2 import PositionKey, Position
from decimal import Decimal

pd.options.display.float_format = "{:.10f}".format


pd.options.display.max_columns = None
pd.set_option("display.width", 5000)
pd.set_option("display.max_rows", None)
pd.set_option("display.precision", 3)


class TestActuator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestActuator, self).__init__(*args, **kwargs)
        self.market_info: MarketInfo = MarketInfo("GMX", MarketTypeEnum.gmx_v2_prep)
        self.usdc = TokenInfo(name="usdc", decimal=6)
        self.weth = TokenInfo(name="weth", decimal=18)
        self.pool: GmxV2Pool = GmxV2Pool(self.weth, self.usdc, self.weth)
        self.usdc_decimal = 10**6
        self.weth_decimal = 10**18
        self.online_status = {  # position on height 411058750
            "positionKey": "08de94d44038c84029b1f841e06fa7517bf87e0a33d082e041f14bea9a224684",
            "position": {
                "addresses": {
                    "account": "0x784F8B525d652A83e4AE85e573c31F17f2DbcA0D",
                    "market": "0x70d95587d40A2caf56bd97485aB3Eec10Bee6336",
                    "collateralToken": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                },
                "numbers": {
                    "sizeInUsd": 16.86998407270779,
                    "sizeInTokens": 5192318360596643 / self.weth_decimal,
                    "collateralAmount": 1996884608983643 / self.weth_decimal,
                    "pendingImpactAmount": -1170331909584 / self.weth_decimal,
                    "borrowingFactor": 0.28235092360718117,
                    "fundingFeeAmountPerSize": 166777321907949805520045425044 / 10 ** (15 + 18),
                    "longTokenClaimableFundingAmountPerSize": 4527337741737576110700834270 / 10 ** (15 + 18),
                    "shortTokenClaimableFundingAmountPerSize": 7804503553381844840 / 10 ** (15 + 6),
                    "increasedAtTime": 1765527627,
                    "decreasedAtTime": 0,
                },
                "flags": {"isLong": True},
            },
            "fees": {
                "funding": {
                    "fundingFeeAmount": 11288328580581 / self.weth_decimal,
                    "claimableLongTokenAmount": 0,
                    "claimableShortTokenAmount": 0,
                    "latestFundingFeeAmountPerSize": 167446458792248522286279227107 / 10 ** (15 + 18),
                    "latestLongTokenClaimableFundingAmountPerSize": 4527337741737576110700834270 / 10 ** (15 + 18),
                    "latestShortTokenClaimableFundingAmountPerSize": 7804503553381844840 / 10 ** (15 + 6),
                },
                "borrowing": {
                    "borrowingFeeUsd": 0.018411593601688297,
                    "borrowingFeeAmount": 6210601951667 / self.weth_decimal,
                    "borrowingFeeReceiverFactor": 0.37,
                    "borrowingFeeAmountForFeeReceiver": 2297922722116 / self.weth_decimal,
                },
                "ui": {
                    "uiFeeReceiver": "0x0000000000000000000000000000000000000000",
                    "uiFeeReceiverFactor": 0.0,
                    "uiFeeAmount": 0,
                },
                "liquidation": {
                    "liquidationFeeUsd": 0.0,
                    "liquidationFeeAmount": 0,
                    "liquidationFeeReceiverFactor": 0.0,
                    "liquidationFeeAmountForFeeReceiver": 0,
                },
                "collateralTokenPrice": {"min": 2964542526629899, "max": 2964542526629899},
                "positionFeeFactor": 0.0004,
                "protocolFeeAmount": 2276234383034 / self.weth_decimal,
                "positionFeeReceiverFactor": 0.37,
                "feeReceiverAmount": 3140091444953 / self.weth_decimal,
                "feeAmountForPool": 5346642190058 / self.weth_decimal,
                "positionFeeAmountForPool": 1434027661312 / self.weth_decimal,
                "positionFeeAmount": 2276234383034 / self.weth_decimal,
                "totalCostAmountExcludingFunding": 8486836334701 / self.weth_decimal,
                "totalCostAmount": 19775164915282 / self.weth_decimal,
                "totalDiscountAmount": 0,
            },
            "executionPriceResult": {
                "priceImpactUsd": 0.0088656926316445,
                "executionPrice": 2966249989850745,
                "balanceWasImproved": True,
                "proportionalPendingImpactUsd": -0.003469498716233746,
                "totalImpactUsd": 0.005396193915410754,
                "priceImpactDiffUsd": 0.0,
            },
            "basePnlUsd": -1.477135480917805,
            "uncappedBasePnlUsd": -1.477135480917805,
            "pnlAfterPriceImpactUsd": -1.4682697882861604,
        }

    def _get_market(self, day: datetime.date):
        market = GmxV2PerpMarket(self.market_info, self.pool)
        market.load_config("tests/data/gmx_config_0x70d95587d40A2caf56bd97485aB3Eec10Bee6336.json")
        data = load_gmx_v2_data(
            ChainType.arbitrum,
            "0x70d95587d40a2caf56bd97485ab3eec10bee6336",
            day,
            day,
            "/data/gmx_v2/arbitrum",
        )
        price = get_price_from_v2_data(data, self.pool)
        market.data = data
        broker = Broker()
        broker.add_to_balance(self.weth, 10)
        broker.add_to_balance(self.usdc, 30000)
        broker.add_market(market)
        return broker, market, data, price

    def get_position(self):
        return Position(
            market=self.pool,
            collateralToken=self.weth,
            isLong=True,
            sizeInUsd=float(self.online_status["position"]["numbers"]["sizeInUsd"]),
            sizeInTokens=float(self.online_status["position"]["numbers"]["sizeInTokens"]),
            collateralAmount=float(self.online_status["position"]["numbers"]["collateralAmount"]),
            pendingImpactAmount=float(self.online_status["position"]["numbers"]["pendingImpactAmount"]),
            borrowingFactor=float(self.online_status["position"]["numbers"]["borrowingFactor"]),
            fundingFeeAmountPerSize=float(self.online_status["position"]["numbers"]["fundingFeeAmountPerSize"]),
            longTokenClaimableFundingAmountPerSize=float(
                self.online_status["position"]["numbers"]["longTokenClaimableFundingAmountPerSize"]
            ),
            shortTokenClaimableFundingAmountPerSize=float(
                self.online_status["position"]["numbers"]["shortTokenClaimableFundingAmountPerSize"]
            ),
        )

    def test_position_info(self):
        broker, market, data, price = self._get_market(datetime.date(2025, 12, 15))

        market.set_market_status(GmxV2LpMarketStatus(data.index[-1], data.iloc[-1]), price.iloc[-1])
        pos_key = PositionKey(self.pool, self.weth, True)
        market.positions[pos_key] = self.get_position()
        position_info = market.get_position_info(pos_key)

        pprint.pprint(position_info)

        compare_position_info(position_info, self.online_status)

    def test_position_value(self):
        broker, market, data, price = self._get_market(datetime.date(2025, 12, 15))
        market.set_market_status(GmxV2LpMarketStatus(data.index[-1], data.iloc[-1]), price.iloc[-1])
        pos_key = PositionKey(self.pool, self.weth, True)
        market.positions[pos_key] = self.get_position()
        position_value = market.get_position_value(pos_key)

        pp = DecimalPrettyPrinter(indent=2, width=120)
        pp.pprint(position_value)

    def test_increase(self):
        broker, market, data, price = self._get_market(datetime.date(2025, 12, 15))
        market.set_market_status(GmxV2LpMarketStatus(data.index[-1], data.iloc[-1]), price.iloc[-1])
        market: GmxV2PerpMarket = market
        pos, fee = market.increase_position(self.weth, 1, True, 10)
        print()
        pprint.pprint(pos)

    def test_increase_again(self):
        broker, market, data, price = self._get_market(datetime.date(2025, 12, 15))
        market.set_market_status(GmxV2LpMarketStatus(data.index[-1], data.iloc[-1]), price.iloc[-1])
        market: GmxV2PerpMarket = market
        pos, fee = market.increase_position(self.weth, 1, True, 10)

        pprint.pprint(pos)
        pprint.pprint(fee)
        pos1, fee1 = market.increase_position(self.weth, 1, True, 10)
        print()

        pprint.pprint(pos1)
        pprint.pprint(fee1)
        pos_key = PositionKey(self.pool, self.weth, True)
        position_value = market.get_position_value(pos_key)
        pprint.pprint(position_value)

    def test_increase_with_real_tx(self):
        # create: https://arbiscan.io/tx/0xf1f6a980fd9b8ab38563922f721da8e94b05b9c7ccbca7fac6b2304d022b663a#eventlog
        # execute: https://arbiscan.io/tx/0xc1ec383cd7d9541050f13b9d14c88369a85b7d92d962c85ece9a8e1adfede219#eventlog
        broker, market, data, price = self._get_market(datetime.date(2025, 12, 15))
        t = pd.Timestamp("2025-12-15 0:3:00")

        data.loc[t, "longPrice"] = 3075.745500562432
        data.loc[t, "indexPrice"] = 3075.745500562432
        market.set_market_status(GmxV2LpMarketStatus(t, data.loc[t]), price.loc[t])
        market: GmxV2PerpMarket = market
        pos, fee = market.increase_position(self.usdc, 68.273675, True, size_in_usd=3180.8620630609335)

        actual = Position(
            market=pos.market,
            collateralToken=pos.collateralToken,
            isLong=pos.isLong,
            sizeInUsd=3180862063060933415616579375000000 / 10**30,
            sizeInTokens=1034175962373765892 / 10**18,
            collateralAmount=67001171 / 10**6,
            pendingImpactAmount=803489072178226 / 10**18,
            borrowingFactor=283225263025121251393134047384 / 10**30,
            fundingFeeAmountPerSize=478756936585289340755 / 10**15 / 10**6,
            longTokenClaimableFundingAmountPerSize=4527337741737576110700834270 / 10**15 / 10**18,
            shortTokenClaimableFundingAmountPerSize=7804503553381844840 / 10**15 / 10**6,
        )
        print()
        print("fees", fee.totalCostAmount, 1.272504)
        compare_position(pos, actual)
        # pendingImpactAmount is not good

    def test_decrease(self):

        broker, market, data, price = self._get_market(datetime.date(2025, 12, 15))
        t = pd.Timestamp("2025-12-15 0:3:00")

        data.loc[t, "longPrice"] = 3075.745500562432
        data.loc[t, "indexPrice"] = 3075.745500562432
        market.set_market_status(GmxV2LpMarketStatus(t, data.loc[t]), price.loc[t])
        market: GmxV2PerpMarket = market
        pos, fee = market.increase_position(self.usdc, 68.273675, True, size_in_usd=3180.8620630609335)
        result, values, fee = market.decrease_position(self.usdc, True)
        print()
        pprint.pprint(result)
        pprint.pprint(values)
        pprint.pprint(fee)

    def test_decrease_with_real_tx(self):
        broker, market, data, price = self._get_market(datetime.date(2025, 11, 11))
        t = pd.Timestamp("2025-11-11 8:0:00")

        market.set_market_status(GmxV2LpMarketStatus(t, data.loc[t]), price.loc[t])
        market: GmxV2PerpMarket = market
        pos_key = PositionKey(self.pool, self.usdc, False)
        # create tx: https://arbiscan.io/tx/0x02137934a839707a3f50867dbe060a8a37110f7423a7eedc9f8ce9c2c1f7aa3b#eventlog
        market.positions[pos_key] = Position(
            market=self.pool,
            collateralToken=self.usdc,
            isLong=False,
            sizeInUsd=4997447833987034101200000000000 / 10**30,
            sizeInTokens=1383404069853044 / 10**18,
            collateralAmount=4998001 / 10**6,
            pendingImpactAmount=327124583431 / 10**18,
            borrowingFactor=105079854500834548595245759986 / 10**30,
            fundingFeeAmountPerSize=16430523650556113223 / 10**6 / 10**15,
            longTokenClaimableFundingAmountPerSize=53813026953928182158142398553 / 10**18 / 10**15,
            shortTokenClaimableFundingAmountPerSize=487153067489763188841 / 10**6 / 10**15,
        )
        position_value = market.get_position_value(pos_key)
        print()
        pprint.pprint(position_value)
        # https://arbiscan.io/tx/0xdc0b6556700a893657ff1b51b065ef83e68db316cdcf365853982caf733bb77b
        result, values, fee = market.decrease_position(self.usdc, False)
        pprint.pprint(result)
        pprint.pprint(values)
        pprint.pprint(fee)
        # pendingImpactAmount and borrrow amount is not good, will use AI generate some compare code

    def test_liquidation_with_real_tx(self):

        # increase tx: https://arbiscan.io/tx/0x6cb8663d3a13cfdd40b0721caf6fa6e48e1648d0bfc95defa02a1fe408b1cf98#eventlog
        # liquidation tx:https://arbiscan.io/tx/0x6512f4109613d913bcb0da1f713226d594b900ac9f19a2e610681b9dcec0aab2#eventlog
        broker, market, data, price = self._get_market(datetime.date(2025, 12, 11))
        t = pd.Timestamp("2025-12-11 1:14:00")
        data.loc[t, "indexPrice"] = 3256.461267663455
        data.loc[t, "longPrice"] = 3256.461267663455
        data.loc[t, "shortPrice"] = 0.999793838373229150000000
        market.set_market_status(GmxV2LpMarketStatus(t, data.loc[t]), price.loc[t])
        market: GmxV2PerpMarket = market
        action_list = []
        def record_action(action):
            action_list.append(action)
        market._record_action_callback =record_action
        pos_key = PositionKey(self.pool, self.usdc, True)
        market.positions[pos_key] = Position(
            market=self.pool,
            collateralToken=self.usdc,
            isLong=True,
            sizeInUsd=16590814454276798868214048800000000 / 10**30,
            sizeInTokens=4919469975661200694 / 10**18,
            collateralAmount=663545936 / 10**6,
            pendingImpactAmount=-2038219224234325 / 10**18,
            borrowingFactor=281970144601482118172241780776 / 10**30,
            fundingFeeAmountPerSize=476208932773322718744 / 10**6 / 10**15,
            longTokenClaimableFundingAmountPerSize=4527337741737576110700834270 / 10**18 / 10**15,
            shortTokenClaimableFundingAmountPerSize=7804503553381844840 / 10**6 / 10**15,
        )
        position_value = market.get_position_value(pos_key)  # pnl should be negative
        print()
        pprint.pprint(position_value)
        # # https://arbiscan.io/tx/0xdc0b6556700a893657ff1b51b065ef83e68db316cdcf365853982caf733bb77b
        # result, values, fee = market.decrease_position(self.usdc, False)
        # pprint.pprint(result)
        # pprint.pprint(values)
        # pprint.pprint(fee)
        market.update()
        output_amount = action_list[0].outputAmount
        assert compare_value(output_amount, 43.837458, 0.003)
        pass

def compare_value(a,val, allowed_error):
    error = abs(float(a)-val)/val
    return error < allowed_error

def compare_position(val, actual):
    rows = [
        ["sizeInUsd", val.sizeInUsd, actual.sizeInUsd],
        ["sizeInTokens", val.sizeInTokens, actual.sizeInTokens],
        ["collateralAmount", val.collateralAmount, actual.collateralAmount],
        ["pendingImpactAmount", val.pendingImpactAmount, actual.pendingImpactAmount],
        ["borrowingFactor", val.borrowingFactor, actual.borrowingFactor],
        ["fundingFeeAmountPerSize", val.fundingFeeAmountPerSize, actual.fundingFeeAmountPerSize],
        [
            "longTokenClaimableFundingAmountPerSize",
            val.longTokenClaimableFundingAmountPerSize,
            actual.longTokenClaimableFundingAmountPerSize,
        ],
        [
            "shortTokenClaimableFundingAmountPerSize",
            val.shortTokenClaimableFundingAmountPerSize,
            actual.shortTokenClaimableFundingAmountPerSize,
        ],
    ]

    df = pd.DataFrame(rows, columns=["name", "demeter", "actual"])
    df["diff"] = 100 * (df["demeter"] - df["actual"]) / df["actual"]
    df["danger"] = abs(df["diff"]) >= 0.1  # error larger than 0.1%
    print(df)


class DecimalPrettyPrinter(pprint.PrettyPrinter):
    def format(self, obj, context, maxlevels, level):
        if isinstance(obj, Decimal):
            return (f"Decimal('{obj:.6f}')", True, False)
        return super().format(obj, context, maxlevels, level)


def compare_position_info(info, online_val: dict):
    rows = []

    rows.append(
        [
            "fees.funding.fundingFeeAmount",
            info.fees.funding.fundingFeeAmount,
            online_val["fees"]["funding"]["fundingFeeAmount"],
        ]
    )
    rows.append(
        [
            "fees.funding.claimableLongTokenAmount",
            info.fees.funding.claimableLongTokenAmount,
            online_val["fees"]["funding"]["claimableLongTokenAmount"],
        ]
    )
    rows.append(
        [
            "fees.funding.claimableShortTokenAmount",
            info.fees.funding.claimableShortTokenAmount,
            online_val["fees"]["funding"]["claimableShortTokenAmount"],
        ]
    )
    rows.append(
        [
            "fees.funding.latestFundingFeeAmountPerSize",
            info.fees.funding.latestFundingFeeAmountPerSize,
            online_val["fees"]["funding"]["latestFundingFeeAmountPerSize"],
        ]
    )
    rows.append(
        [
            "fees.funding.latestLongTokenClaimableFundingAmountPerSize",
            info.fees.funding.latestLongTokenClaimableFundingAmountPerSize,
            online_val["fees"]["funding"]["latestLongTokenClaimableFundingAmountPerSize"],
        ]
    )
    rows.append(
        [
            "fees.funding.latestShortTokenClaimableFundingAmountPerSize",
            info.fees.funding.latestShortTokenClaimableFundingAmountPerSize,
            online_val["fees"]["funding"]["latestShortTokenClaimableFundingAmountPerSize"],
        ]
    )

    rows.append(
        [
            "fees.borrowing.borrowingFeeUsd",
            info.fees.borrowing.borrowingFeeUsd,
            online_val["fees"]["borrowing"]["borrowingFeeUsd"],
        ]
    )
    rows.append(
        [
            "fees.borrowing.borrowingFeeAmount",
            info.fees.borrowing.borrowingFeeAmount,
            online_val["fees"]["borrowing"]["borrowingFeeAmount"],
        ]
    )

    rows.append(["fees.positionFeeFactor", info.fees.positionFeeFactor, online_val["fees"]["positionFeeFactor"]])
    rows.append(["fees.positionFeeAmount", info.fees.positionFeeAmount, online_val["fees"]["positionFeeAmount"]])
    rows.append(["fees.protocolFeeAmount", info.fees.protocolFeeAmount, online_val["fees"]["protocolFeeAmount"]])
    rows.append(
        [
            "fees.totalCostAmountExcludingFunding",
            info.fees.totalCostAmountExcludingFunding,
            online_val["fees"]["totalCostAmountExcludingFunding"],
        ]
    )
    rows.append(["fees.totalCostAmount", info.fees.totalCostAmount, online_val["fees"]["totalCostAmount"]])
    rows.append(["fees.positionFeeAmount", info.fees.positionFeeAmount, online_val["fees"]["positionFeeAmount"]])

    rows.append(
        [
            "executionPriceResult.priceImpactUsd",
            info.executionPriceResult.priceImpactUsd,
            online_val["executionPriceResult"]["priceImpactUsd"],
        ]
    )
    rows.append(
        [
            "executionPriceResult.totalImpactUsd",
            info.executionPriceResult.totalImpactUsd,
            online_val["executionPriceResult"]["totalImpactUsd"],
        ]
    )
    rows.append(["basePnlUsd", info.basePnlUsd, online_val["basePnlUsd"]])
    rows.append(["pnlAfterPriceImpactUsd", info.pnlAfterPriceImpactUsd, online_val["pnlAfterPriceImpactUsd"]])

    df = pd.DataFrame(rows, columns=["name", "demeter", "actual"])
    df["diff"] = 100 * (df["demeter"] - df["actual"]) / df["actual"]
    df["danger"] = abs(df["diff"]) >= 0.1  # error larger than 0.1%
    print(df)
