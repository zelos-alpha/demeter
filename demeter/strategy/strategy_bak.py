class MetaStrategy(object):
    def __new__(cls, *args, **kwargs):
        pass

    def __init__(self):
        self._orders = []
        self._broker = None


class Strategy(MetaStrategy):
    def __init__(self):
        super().__init__()

    def start(self) -> None:
        """
        启动策略
        :return:
        """
        pass

    def stop(self) -> None:
        """
        停止策略
        :return:
        """
        pass

    def clear(self) -> None:
        """
        清理数据
        :return:
        """
        self._orders = []

    def next(self) -> None:
        """
        执行下一个bar
        :return:
        """
        pass

    def buy(self, data=None, asset=None, size=None, price=None):
        """
        执行买操作
        :param data: 在哪个data/bar 执行buy操作
        :param asset: 卖空资产
        :param size: buy 数量
        :param price: buy 价格，提供按照价格挂单，不提供按照start价格成交
        :return:
        """
        return self._broker.buy(data=data, asset=asset, size=size, price=price)

    def sell(self, data=None, asset=None, size=None, price=None):
        """
        执行卖操作
        :param data: 在哪个data/bar 执行sell操作
        :param asset: 卖空资产
        :param size: sell 数量
        :param price: sell 价格，提供按照价格挂单，不提供按照start价格成交
        :return:
        """
        return self._broker.sell(data=data, asset=asset, size=size, price=price)

    def add_liquidity(self, asset: str, size: float = 0.0):
        """
        添加流动性
        :return:
        """
        return self._broker.add_liquid(asset=asset, size=size)

    def remove_liquidity(self, position: float = 0.0):
        """
        移除流动性
        :return:
        """
        return self._broker.remove_liquid(position=position)

    def cancel(self, order):
        """
        执行取消操作
        :return:
        """
        self._broker.cancel(order)

    # def get_position(self, asset: str = None):
    #     """
    #     获取asset仓位
    #     :param asset:
    #     :return:
    #     """
    #     if not asset:
    #         return None
    #     else:
    #         return self._broker.get_position(asset=asset)

    def collect_fee(self):
        """

        :return:
        """
        self._broker.collect_fee()

    def _notify(self):
        """
        具体notify逻辑
        :return:
        """
        pass

    def notify_order(self):
        """
        通知订单
        :return:
        """
        pass

    def notify_trade(self):
        """
        通知交易
        :return:
        """
        pass

    def notify_fund(self):
        """
        通知资产
        :return:
        """
        cash = self._broker.get_cash()
        return cash

    def notify_position(self):
        """
        通知仓位
        :return:
        """
        position = self._broker.get_position()
        return position

    def add_indicator(self, indicator_class):
        """
        添加指标
        :param indicator_class:
        :return:
        """
        pass

    def add_analyzer(self, analyzer_class):
        """
        添加分析器
        :param analyzer_class:
        :return:
        """
        pass
