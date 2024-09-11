import pandas as pd
from datetime import datetime
from decimal import Decimal
from typing import Dict, Callable

from ._typing import Asset, TokenInfo, AccountStatus, MarketDict, AssetDict, BaseAction, MarketTypeEnum
from .market import Market
from .._typing import DemeterError, UnitDecimal, STABLE_COINS
from ..utils import get_formatted_from_dict, get_formatted_predefined, STYLE, float_param_formatter


class Broker:
    """
    Broker supports different order types, checking a submitted order cash requirements against current cash,
    keeping track of cash and value for each iteration of actuator and keeping the current position on different datas.

    :param allow_negative_balance: allow cash balance can be negative value or not. Default is False
    :type allow_negative_balance: bool
    :param record_action_callback: A callback function used to notify actions(buy/sell). When new actions is taken, this function will be called, and action instance will be passed as parameter. function should be like: def callback(action:BaseAction)
    :type record_action_callback: Callable[[BaseAction], None]
    """

    def __init__(self, allow_negative_balance=False, record_action_callback: Callable[[BaseAction], None] = None):
        """
        init Broker

        """
        self.allow_negative_balance = allow_negative_balance
        self._assets: AssetDict[Asset] = AssetDict()
        self._markets: MarketDict[Market] = MarketDict()
        self._record_action_callback: Callable[[BaseAction], None] = record_action_callback
        self.quote_token = None

    # region properties

    @property
    def markets(self) -> MarketDict[Market]:
        """
        markets managed by this broker

        :return: a dict of markets, key type is MarketKey.
        :rtype: MarketDict[Market]
        """
        return self._markets

    @property
    def assets(self) -> AssetDict[Asset]:
        """
        All assets managed by this broker.

        :return: A dict of assets, key type is TokenInfo
        :rtype: AssetDict[Asset]
        """
        return self._assets

    # endregion

    def __str__(self):
        """
        Return description of this broker in json string.

        :return: json string
        :type: str
        """
        return '{{"assets":[{}],"markets":[{}]}}'.format(
            ",".join(f"{asset}" for asset in self._assets.values()), ",".join(f"{v}" for k, v in self.markets.items())
        )

    def add_market(self, market: Market):
        """
        | Set a new market to broker,
        | User should initialize market before set to broker(Because there are too many initial parameters)

        :param market: market to add, can be uniswap market or aave market etc.
        :type market: Market
        """
        if market.market_info in self._markets:
            raise DemeterError("market has exist")
        self._markets[market.market_info] = market
        market.broker = self
        market._record_action_callback = self._record_action_callback

    @float_param_formatter
    def add_to_balance(self, token: TokenInfo, amount: Decimal | float) -> Asset:
        """
        Add token amount to wallet of broker, if token key is not exist. will generate a new record

        :param token: which token to set
        :type token: TokenInfo
        :param amount: balance, e.g. 1.2345
        :type amount: Decimal | float
        :return: Asset instance
        :rtype: Asset
        """
        if token in self._assets:
            asset: Asset = self._assets[token]
        else:
            asset: Asset = self.__add_asset(token)
        asset.add(amount)
        return asset

    @float_param_formatter
    def set_balance(self, token: TokenInfo, amount: Decimal | float) -> Asset:
        """
        Set token amount to wallet of broker. Old value will be overwritten

        :param token: which token to set, TokenInfo(name='usdc', decimal=6)
        :type token: TokenInfo
        :param amount: amount of token, e.g. 10.00
        :type amount:  Decimal | float
        :return: Asset instance
        :rtype: Asset

        """
        asset: Asset = self.__add_asset(token)
        asset.balance = amount
        return asset

    @float_param_formatter
    def subtract_from_balance(self, token: TokenInfo, amount: Decimal | float) -> Asset:
        """
        | subtract token amount from wallet of broker.
        | Wallet balance may be negative if allow_negative_balance==True
        | if token key is not exist. will generate a new record, unless broker.allow_negative_balance==False

        :param token: which token to set
        :type token: TokenInfo
        :param amount: Decimal or float type
        :type amount:  Decimal | float
        :return: Asset instance
        :rtype: Asset
        """
        if token in self._assets:
            asset: Asset = self._assets[token]
            asset.sub(amount, allow_negative_balance=self.allow_negative_balance)
        else:
            if self.allow_negative_balance:
                asset: Asset = self.__add_asset(token)
                asset.balance = 0 - amount
            else:
                raise DemeterError(f"{token.name} doesn't exist in assets dict")
        return asset

    def __add_asset(self, token: TokenInfo) -> Asset:
        self._assets[token] = Asset(token, 0)
        return self._assets[token]

    def get_token_balance(self, token: TokenInfo) -> Decimal:
        """
        Get balance of token, if token has not set, will raise an error

        :param token: which token to find.
        :type token: TokenInfo
        :return: balance of this token, e.g. 1.2345
        :rtype: Decimal
        """
        if token in self.assets:
            return self._assets[token].balance
        else:
            raise DemeterError(f"{token.name} doesn't exist in assets dict")

    def get_token_balance_with_unit(self, token: TokenInfo) -> UnitDecimal:
        """
        Get balance of token with unit

        :param token: which token to find.
        :type token: TokenInfo
        :return: balance of this token, e.g. 1.2345 eth
        :rtype: UnitDecimal
        """
        return UnitDecimal(self.get_token_balance(token), token.name)

    def get_account_status(self, prices: pd.Series | Dict[str, Decimal], timestamp=datetime | None) -> AccountStatus:
        """
        Get account status, including net value, cash balance and balance in all markets

        :param prices: current price, e.g. ('eth', Decimal('1610.553895752868641174609110')) ('usdc', 1)
        :type prices: pd.Series | Dict[str, Decimal]
        :param timestamp: current timestamp
        :type timestamp: datetime
        :return: balances
        :rtype: AccountStatus

        """
        account_status = AccountStatus(timestamp=timestamp)
        market_sum = Decimal(0)
        for k, v in self.markets.items():
            ms = v.get_market_balance()
            account_status.market_status[k] = ms
            if v.quote_token == self.quote_token:
                market_sum += ms.net_value
            else:
                market_sum += ms.net_value * prices[v.quote_token.name]
        account_status.market_status.set_default_key(self.markets.get_default_key())

        for k, v in self.assets.items():
            account_status.asset_balances[k] = v.balance
        asset_sum = sum([v * prices[k.name] for k, v in account_status.asset_balances.items()])

        account_status.net_value = asset_sum + market_sum
        return account_status

    def formatted_str(self):
        """
        Get formatted broker description string to print in console

        :return: str info of broker
        :rtype: str
        """

        str_to_print = get_formatted_predefined("Token balance in broker", STYLE["header2"]) + "\n"
        balances = {}
        for asset in self._assets.values():
            balances[asset.name] = asset.balance
        str_to_print += get_formatted_from_dict(balances) + "\n"
        str_to_print += get_formatted_predefined("Position value in markets", STYLE["header2"]) + "\n"
        for market in self._markets.values():
            str_to_print += market.formatted_str() + "\n"
        return str_to_print

    def _check_quote_token(self):
        if self.quote_token is None:
            raise DemeterError("Quote token of broker not set")

        market_types = set([x.market_info.type for x in self.markets.values()])
        has_usd_market = {
            MarketTypeEnum.squeeth, MarketTypeEnum.aave_v3
        }.intersection(market_types)

        if has_usd_market:
            if self.quote_token.name not in STABLE_COINS:
                raise DemeterError("squeeth/AAVE market must quote by stable coin or None")

    def check_backtest(self):
        """
        check backtest result, including index of data, prices
        """
        # ensure a market exist
        if len(self.markets) < 1:
            raise DemeterError("No market assigned")

        data_length = []  # [1440]
        for market in self.markets.values():
            data_length.append(len(market.data.index))
            market.check_market()  # check each market, including assets

        self._check_quote_token()
