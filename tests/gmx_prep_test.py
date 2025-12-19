import datetime
import unittest
import pprint
import pandas as pd

from demeter import TokenInfo, MarketInfo, MarketTypeEnum, ChainType
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
        self.online_status = { # position on height 411058750
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

    def _get_market(self):
        market = GmxV2PerpMarket(self.market_info, self.pool)
        market.load_config("tests/data/gmx_config_0x70d95587d40A2caf56bd97485aB3Eec10Bee6336.json")
        data = load_gmx_v2_data(
            ChainType.arbitrum,
            "0x70d95587d40a2caf56bd97485ab3eec10bee6336",
            datetime.date(2025, 12, 15),
            datetime.date(2025, 12, 15),
            "/data/gmx_v2/arbitrum",
        )
        price = get_price_from_v2_data(data, self.pool)
        market.data = data
        return market, data, price

    def get_position(self):
        return Position(
            market=self.pool,
            collateralToken=self.weth,
            isLong=True,
            sizeInUsd=self.online_status["position"]["numbers"]["sizeInUsd"],
            sizeInTokens=self.online_status["position"]["numbers"]["sizeInTokens"],
            collateralAmount=self.online_status["position"]["numbers"]["collateralAmount"],
            pendingImpactAmount=self.online_status["position"]["numbers"]["pendingImpactAmount"],
            borrowingFactor=self.online_status["position"]["numbers"]["borrowingFactor"],
            fundingFeeAmountPerSize=self.online_status["position"]["numbers"]["fundingFeeAmountPerSize"],
            longTokenClaimableFundingAmountPerSize=self.online_status["position"]["numbers"][
                "longTokenClaimableFundingAmountPerSize"
            ],
            shortTokenClaimableFundingAmountPerSize=self.online_status["position"]["numbers"][
                "shortTokenClaimableFundingAmountPerSize"
            ],
        )

    def test_position_info(self):
        market, data, price = self._get_market()

        market.set_market_status(GmxV2LpMarketStatus(data.index[-1], data.iloc[-1]), price.iloc[-1])
        pos_key = PositionKey(self.pool, self.weth, True)
        market.positions[pos_key] = self.get_position()
        position_info = market.get_position_info(pos_key)

        pprint.pprint(position_info)

        compare_position_info(position_info, self.online_status)

    def test_position_value(self):
        market, data, price = self._get_market()
        market.set_market_status(GmxV2LpMarketStatus(data.index[-1], data.iloc[-1]), price.iloc[-1])
        pos_key = PositionKey(self.pool, self.weth, True)
        market.positions[pos_key] = self.get_position()
        position_value = market.get_position_value(pos_key)

        pp = DecimalPrettyPrinter(indent=2, width=120)
        pp.pprint(position_value)


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
