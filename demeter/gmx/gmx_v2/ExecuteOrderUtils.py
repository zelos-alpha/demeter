from .IncreaseOrderUtils import IncreaseOrderUtils
from .DecreaseOrderUtils import DecreaseOrderUtils
from .SwapOrderUtils import SwapOrderUtils
from ._typing import PoolConfig, GmxV2PoolStatus, Order, OrderType, ExecuteOrderParams, Market
from .._typing2 import GmxV2Pool


class ExecuteOrderUtils:

    @staticmethod
    def isIncreaseOrder(order: Order) -> bool:
        return (order.orderType == OrderType.MarketIncrease or
                order.orderType == OrderType.LimitIncrease or
                order.orderType == OrderType.StopIncrease)

    @staticmethod
    def isDecreaseOrder(order: Order) -> bool:
        return (order.orderType == OrderType.MarketDecrease or
                order.orderType == OrderType.LimitDecrease or
                order.orderType == OrderType.StopLossDecrease or
                order.orderType == OrderType.Liquidation)

    @staticmethod
    def isSwapOrder(order: Order) -> bool:
        return (order.orderType == OrderType.MarketSwap or
                order.orderType == OrderType.LimitSwap)

    @staticmethod
    def executeOrder(
            market: str,
            initialCollateralToken: str,
            swapPath,
            orderType,
            sizeDeltaUsd,
            initialCollateralDeltaAmount,
            triggerPrice,
            acceptablePrice,
            isLong,
            decreasePositionSwapType,
            marketToken,
            indexToken,
            longToken,
            shortToken,
            pool_status: GmxV2PoolStatus,
            pool_config: PoolConfig,
            pool: GmxV2Pool):
        order = Order(
            market=market,
            initialCollateralToken=initialCollateralToken,
            swapPath=swapPath,
            orderType=orderType,
            sizeDeltaUsd=sizeDeltaUsd,
            initialCollateralDeltaAmount=initialCollateralDeltaAmount,
            triggerPrice=triggerPrice,
            acceptablePrice=acceptablePrice,
            isLong=isLong,
            decreasePositionSwapType=decreasePositionSwapType
        )
        _market = Market(
            marketToken=marketToken,
            indexToken=indexToken,
            longToken=longToken,
            shortToken=shortToken
        )
        params = ExecuteOrderParams(order=order, swapPathMarkets=[], market=_market)
        if ExecuteOrderUtils.isIncreaseOrder(params.order):
            return IncreaseOrderUtils.processOrder(params, pool_status, pool_config, pool)
        elif ExecuteOrderUtils.isDecreaseOrder(params.order):
            return DecreaseOrderUtils.processOrder(params, pool_status, pool_config, pool)
        elif ExecuteOrderUtils.isSwapOrder(params.order):
            return SwapOrderUtils.processOrder(params, pool_status, pool_config)
