from SweepProcessUtils import SweepProcessUtils

class CoreStateUtils:
    @staticmethod
    def _initUser():
        pass

    @staticmethod
    def _shortcutSettleAndGet():
        nLongOrders, nShortOrders, shortcutted = CoreStateUtils._initUserCoreData()
        settle = SweepProcessUtils._sweepProcess()


    @staticmethod
    def _initUserCoreData() -> (int, int, bool):
        pass