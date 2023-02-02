from decimal import Decimal

from .types import Asset, TokenInfo, Market, MarketInfo


class Broker:
    def __int__(self):
        self._assets: {TokenInfo: Asset} = {}
        self._markets: {MarketInfo: Market} = {}

    # region properties

    @property
    def markets(self):
        return self._markets

    @property
    def assets(self):
        return self._assets

    @property
    def assets_net_value(self):
        return Decimal(0)

    @property
    def markets_net_value(self):
        return Decimal(0)

    @property
    def net_value(self):
        return self.assets_net_value + self.markets_net_value

    # endregion

    def add_market(self, market_info: MarketInfo, market: Market):
        """
        Set a new market to broker,
        User should initialize market before set to broker(Because there are too many initial parameters)
        :param market_info:
        :type market_info:
        :param market:
        :type market:
        :return:
        :rtype:
        """
        self._markets[market_info] = market
