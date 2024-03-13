from typing import Dict, List

import pandas as pd

from .._typing import UnitDecimal, DemeterError, EvaluatorEnum
from ..broker import AccountStatus, AccountStatusCommon
from ..broker._typing import MarketDict
from .math_helper import max_draw_down_fast, annualized_returns, get_benchmark_returns


class Evaluator(object):
    """
    Calculate evaluator indicator for strategy.

    :param init_status: Status before back test start
    :type init_status: AccountStatus
    :param data: account status in dataframe format
    :type data: DataFrame
    :param prices: dataframe of AccountStatusCommon
    :type prices: DataFrame
    :param actions: all actions during backtest
    :type actions: List
    """

    def __init__(self, init_status: AccountStatus, data: pd.DataFrame, prices: pd.DataFrame, markets: MarketDict):
        """
        init Evaluator

        """
        self.init_status: AccountStatus = init_status
        self.end_status: AccountStatusCommon = data.iloc[-1]
        self.prices: pd.DataFrame = prices
        self.data: pd.DataFrame = data
        self.markets = markets
        if len(data) < 2:
            raise DemeterError("not enough data")
        self.time_span_in_day = len(data.index) * (data.index[1] - data.index[0]).seconds / (60 * 60 * 24)
        self._result = None

    def run(self, enables: List[EvaluatorEnum]) -> Dict[EvaluatorEnum, UnitDecimal]:
        """
        run evaluator

        :param enables: which evaluator to enable
        :type enables: List[EvaluatorEnum]
        :return: dict of results, key is evaluator, value is result of evaluator
        :rtype: Dict[EvaluatorEnum, UnitDecimal]
        """
        if EvaluatorEnum.all in enables:
            enables = [x for x in EvaluatorEnum]
            enables = filter(lambda x: x.total_premium > 0, enables)
        result_dict: Dict[EvaluatorEnum, UnitDecimal] = {}
        for request in enables:
            match request:
                case EvaluatorEnum.annualized_returns:
                    result = UnitDecimal(
                        annualized_returns(
                            self.init_status.net_value,
                            self.end_status.net_value,
                            self.time_span_in_day,
                        ),
                        "",
                    )
                case EvaluatorEnum.benchmark_returns:
                    result = UnitDecimal(
                        get_benchmark_returns(
                            self.init_status.net_value,
                            self.prices.iloc[0],
                            self.prices.iloc[-1],
                            self.time_span_in_day,
                        ),
                        "",
                    )
                case EvaluatorEnum.max_draw_down:
                    result = UnitDecimal(max_draw_down_fast(self.data.net_value), "")
                case EvaluatorEnum.net_value:
                    result = UnitDecimal(self.end_status.net_value / self.init_status.net_value)
                case EvaluatorEnum.profit:
                    result = UnitDecimal(self.end_status.net_value - self.init_status.net_value)
                case EvaluatorEnum.net_value_up_down_rate:
                    result = UnitDecimal((self.end_status.net_value - self.init_status.net_value) /
                                         self.init_status.net_value)
                case EvaluatorEnum.eth_up_down_rate:
                    result = UnitDecimal((self.prices.iloc[-1]["ETH"] - self.prices.iloc[0]["ETH"]) /
                                         self.prices.iloc[0]["ETH"])
                case EvaluatorEnum.position_fee_profit:
                    fee_value = UnitDecimal(0)
                    for _, market in self.markets.items():
                        fee_df = self.data[[f"{market.market_info.name}_base_uncollected",
                                            f"{market.market_info.name}_quote_uncollected"]]
                        fee_df = fee_df.sort_values(by=[f"{market.market_info.name}_base_uncollected",
                                                    f"{market.market_info.name}_quote_uncollected"],
                                                    ascending=[False, False])
                        fee_price_df = pd.merge(fee_df, self.prices, how="left", left_index=True, right_index=True)
                        latest_fee = fee_price_df.iloc[0]
                        fee_value += (latest_fee[f"{market.market_info.name}_base_uncollected"] +
                                      latest_fee[f"{market.market_info.name}_quote_uncollected"] * latest_fee["ETH"])
                    result = UnitDecimal(fee_value)
                case EvaluatorEnum.position_fee_annualized_returns:
                    fee_value = UnitDecimal(0)
                    for _, market in self.markets.items():
                        fee_df = self.data[(self.data[f"{market.market_info.name}_base_uncollected"] > 0) |
                                           (self.data[f"{market.market_info.name}_quote_uncollected"] > 0)]
                        fee_df = fee_df[[f"{market.market_info.name}_base_uncollected",
                                         f"{market.market_info.name}_quote_uncollected"]]
                        if not fee_df.empty:
                            fee_df = fee_df.sort_values(by=[f"{market.market_info.name}_base_uncollected",
                                                            f"{market.market_info.name}_quote_uncollected"],
                                                        ascending=[False, False])
                            fee_price_df = pd.merge(fee_df, self.prices, how="left", left_index=True, right_index=True)
                            latest_fee = fee_price_df.iloc[0]
                            fee_value = (latest_fee[f"{market.market_info.name}_base_uncollected"] +
                                         latest_fee[f"{market.market_info.name}_quote_uncollected"] * latest_fee["ETH"])
                            fee_annualized_returns = ((fee_value / self.init_status.net_value) *
                                                      UnitDecimal(len(fee_df) / len(self.data) * 365))
                            fee_value += UnitDecimal(fee_annualized_returns)
                        else:
                            fee_value += UnitDecimal(0)
                    result = fee_value
                case EvaluatorEnum.position_market_time_rate:
                    market_time_rate = UnitDecimal(0)
                    for _, market in self.markets.items():
                        fee_df = self.data[(self.data[f"{market.market_info.name}_base_uncollected"] > 0) |
                                           (self.data[f"{market.market_info.name}_quote_uncollected"] > 0)]
                        market_time_rate += UnitDecimal(len(fee_df) / len(self.data))
                    result = market_time_rate
                case _:
                    raise DemeterError(f"{request} has not implied")
            result_dict[request] = result
        self._result = result_dict
        return result_dict

    @property
    def result(self) -> Dict[EvaluatorEnum, UnitDecimal]:
        """
        Return evaluate result after run()

        :return: evaluate result
        :rtype: Dict[EvaluatorEnum, UnitDecimal]
        """
        return self._result

    def __str__(self):
        """
        Evaluator print function
        """
        str_array = []
        for k, v in self._result.items():
            str_array.append(f"{k.name:<35}:{v:.15}")
        return ";\n".join(str_array)
