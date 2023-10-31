from typing import Dict, List

import pandas as pd

from .._typing import UnitDecimal, DemeterError, EvaluatorEnum
from ..broker import AccountStatus, AccountStatusCommon
from .math_helper import max_draw_down_fast, annualized_returns, get_benchmark_returns


class Evaluator(object):
    """
    Calculate evaluator indicator for strategy.

    :param init_status:
    :type init_status: AccountStatus
    :param data:
    :type data: pd.DataFrame | AccountStatusCommon
    :param prices:
    :type prices: DataFrame
    :param actions:
    :type actions: List
    """

    def __init__(
        self,
        init_status: AccountStatus,
        data: pd.DataFrame | AccountStatusCommon,
        prices: pd.DataFrame,
        actions: List
    ):
        """
        init Evaluator

        """
        self.init_status: AccountStatus = init_status
        self.end_status: AccountStatusCommon = data.iloc[-1]
        self.prices: pd.DataFrame = prices
        self.data: pd.DataFrame = data
        self.actions = actions
        if len(data) < 2:
            raise DemeterError("not enough data")
        self.time_span_in_day = len(data.index) * (data.index[1] - data.index[0]).seconds / (60 * 60 * 24)
        self._result = None

    def run(self, enables: List[EvaluatorEnum]):
        """
        run evaluator
        :param enables:
        :return: result_dict
        """
        if EvaluatorEnum.all in enables:
            enables = [x for x in EvaluatorEnum]
            enables = filter(lambda x: x.value > 0, enables)
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
                case EvaluatorEnum.NET_VALUE:
                    result = UnitDecimal(self.end_status.net_value / self.init_status.net_value)
                case EvaluatorEnum.PROFIT:
                    result = UnitDecimal(self.end_status.net_value - self.init_status.net_value)
                case EvaluatorEnum.NET_VALUE_UP_DOWN_RATE:
                    result = UnitDecimal((self.end_status.net_value - self.init_status.net_value) /
                                         self.init_status.net_value)
                case EvaluatorEnum.ETH_UP_DOWN_RATE:
                    result = UnitDecimal((self.prices.iloc[-1]['ETH'] - self.prices.iloc[0]['ETH']) /
                                         self.prices.iloc[0]['ETH'])
                case EvaluatorEnum.POSITION_FEE_PROFIT:
                    fee_df = self.data[['market1_base_uncollected', 'market1_quote_uncollected']]
                    fee_df.sort_values(by=['market1_base_uncollected', 'market1_quote_uncollected'], ascending=[False, False], inplace=True)
                    fee_price_df = pd.merge(fee_df, self.prices, how='left', left_index=True, right_index=True)
                    latest_fee = fee_price_df.iloc[0]
                    fee_value = latest_fee['market1_base_uncollected'] * latest_fee['ETH'] + latest_fee[
                        'market1_quote_uncollected']
                    result = UnitDecimal(fee_value)
                case EvaluatorEnum.POSITION_FEE_ANNUALIZED_RETURNS:
                    fee_df = self.data[(self.data['market1_base_uncollected'] > 0) |
                                       (self.data['market1_quote_uncollected'] > 0)]
                    fee_df = fee_df[['market1_base_uncollected', 'market1_quote_uncollected']]
                    fee_df.sort_values(by=['market1_base_uncollected', 'market1_quote_uncollected'],
                                       ascending=[False, False], inplace=True)
                    fee_price_df = pd.merge(fee_df, self.prices, how='left', left_index=True, right_index=True)
                    latest_fee = fee_price_df.iloc[0]
                    fee_value = latest_fee['market1_base_uncollected'] * latest_fee['ETH'] + latest_fee[
                        'market1_quote_uncollected']
                    fee_annualized_returns = (fee_value / self.init_status.net_value) * UnitDecimal(len(fee_df) /
                                                                                                    len(self.data) *
                                                                                                    365)
                    result = UnitDecimal(fee_annualized_returns)
                case EvaluatorEnum.POSITION_MARKET_TIME_RATE:
                    fee_df = self.data[
                        (self.data['market1_base_uncollected'] > 0) | (self.data['market1_quote_uncollected'] > 0)]
                    result = UnitDecimal(len(fee_df) / len(self.data))
                case _:
                    raise DemeterError(f"{request} has not implied")
            result_dict[request] = result
        self._result = result_dict
        return result_dict

    @property
    def result(self) -> Dict[EvaluatorEnum, UnitDecimal]:
        """
        return Evaluator._result property
        :return:
        """
        return self._result

    def __str__(self):
        """
        Evaluator print function
        :return:
        """
        str_array = []
        for k, v in self._result.items():
            str_array.append(f"{k.name}:{v}")
        return "; ".join(str_array)
