from decimal import Decimal

from .action_history import ActionRecorder
from .market import Market
from .types import Asset, TokenInfo, MarketInfo
from .. import DemeterError, UnitDecimal
from ..utils.application import float_param_formatter


class Broker:
    def __int__(self, allow_negative_balance=False):
        self.allow_negative_balance = allow_negative_balance
        self._assets: {TokenInfo: Asset} = {}
        self._markets: {MarketInfo: Market} = {}
        self._action_recorder = ActionRecorder()

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
        market.broker = self
        market.action_recorder = self._action_recorder

    @float_param_formatter
    def add_asset(self, token: TokenInfo, amount: Decimal | float):  # TODO: 名字再想想
        """
        set initial balance for token

        :param token: which token to set
        :type token: TokenInfo
        :param amount: balance, eg: 1.2345
        :type amount: Decimal | float
        """
        if token in self._assets:
            asset: Asset = self._assets[token]
            asset.add(amount)
        else:
            self._assets[token] = Asset(token, amount)
        return self._assets[token].balance

    @float_param_formatter
    def sub_asset(self, token: TokenInfo, amount: Decimal | float):  # TODO: 名字再想想
        if token in self._assets:
            asset: Asset = self._assets[token]
            asset.sub(amount, allow_negative_balance=self.allow_negative_balance)
        else:
            if self.allow_negative_balance:
                self._assets[token] = Asset(token, 0 - amount)
            else:
                raise DemeterError(f"{token.name} doesn't exist in assets dict")
        return self._assets[token].balance

    def get_token_balance(self, token: TokenInfo):
        if token in self.assets:
            return self._assets[token].balance
        else:
            raise DemeterError(f"{token.name} doesn't exist in assets dict")

    def get_token_balance_with_unit(self, token: TokenInfo):
        return UnitDecimal(self.get_token_balance(token), token.name)
