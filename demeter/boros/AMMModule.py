from _typing import Trade, Side, TimeInForce, LiquidityMathParams, CancelData, LongShort, AddLiquiditySingleCashToAmmReq
from OrdersLib import OrdersLib
from BookAmmSwapBase import BookAmmSwapBase
from PaymentLib import PaymentLib
from LiquidityMath import LiquidityMathLib

class AMMModule:

    @staticmethod
    def addLiquiditySingleCashToAmm(req: AddLiquiditySingleCashToAmmReq):
        swapTrade, swapCashIn, swapTakerOtcFee = AMMModule._swapToAddLiquidity(req)
        netLpOut, netCashIn, netOtcFee = BookAmmSwapBase._mintAMM(req.maxCashIn, req.exactSizeIn)  # todo
        return netLpOut, netCashIn, netOtcFee

    @staticmethod
    def removeLiquiditySingleCashFromAmm():
        pass

    @staticmethod
    def _swapToAddLiquidity(req: AddLiquiditySingleCashToAmmReq) -> (Trade, int, int):
        params = AMMModule._createLiquidityMathParams(req)  # todo
        withBook, withAMM = AMMModule.approxSwapToAddLiquidity(params)  # todo
        orders = LongShort()
        if withBook:
            _, limitTick =  AMMModule._toSideAndLimitTick(params.ammSize)
            orders = OrdersLib.createOrders(TimeInForce.FOK, withBook, limitTick)
        emptyCancels = CancelData()
        swapTradeInterm, takerOtcFee = BookAmmSwapBase._swapBookAMM(withAMM, orders, emptyCancels)
        netCashIn = PaymentLib.toUpfrontFixedCost(swapTradeInterm, LiquidityMathLib.timeToMat(params)) + takerOtcFee
        return swapTradeInterm, netCashIn, takerOtcFee

    @staticmethod
    def _createLiquidityMathParams(req: AddLiquiditySingleCashToAmmReq) -> LiquidityMathParams:
        pass

    @staticmethod
    def approxSwapToAddLiquidity(params) -> (int, int):
        pass

    @staticmethod
    def _toSideAndLimitTick(ammSize) -> (Side, int):
        pass