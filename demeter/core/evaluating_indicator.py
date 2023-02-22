from typing import Dict, List

import pandas as pd

from .._typing import UnitDecimal, DemeterError, EvaluatorEnum
from ..broker import AccountStatus, AccountStatusCommon
from .math_helper import max_draw_down_fast, annualized_returns, get_benchmark_returns


class Evaluator(object):
    """
    calculate evaluator indicator for strategy.
    """

    def __init__(self, init_status: AccountStatus, data: pd.DataFrame | AccountStatusCommon, prices: pd.DataFrame):
        self.init_status: AccountStatus = init_status
        self.end_status: AccountStatusCommon = data.iloc[-1]
        self.prices: pd.DataFrame = prices
        self.data: pd.DataFrame = data
        if len(data) < 2:
            raise DemeterError("not enough data")
        self.time_span_in_day = len(data.index) * (data.index[1] - data.index[0]).seconds / (60 * 60 * 24)
        self._result = None

    def run(self, enables: List[EvaluatorEnum]):
        if EvaluatorEnum.ALL in enables:
            enables = [x for x in EvaluatorEnum]
            enables = filter(lambda x: x.value > 0, enables)
        result_dict: Dict[EvaluatorEnum,UnitDecimal] = {}
        for request in enables:
            match request:
                case EvaluatorEnum.ANNUALIZED_RETURNS:
                    result = UnitDecimal(annualized_returns(self.init_status.net_value,
                                                            self.end_status.net_value,
                                                            self.time_span_in_day), "")
                case EvaluatorEnum.BENCHMARK_RETURNS:
                    result = UnitDecimal(get_benchmark_returns(self.init_status.net_value,
                                                               self.prices.iloc[0],
                                                               self.prices.iloc[-1],
                                                               self.time_span_in_day), "")
                case EvaluatorEnum.MAX_DRAW_DOWN:
                    result = UnitDecimal(max_draw_down_fast(self.data.net_value), "")
                case _:
                    raise DemeterError(f"{request} has not implied")
            result_dict[request] = result
        self._result = result_dict
        return result_dict

    @property
    def result(self) -> Dict[EvaluatorEnum,UnitDecimal]:
        return self._result
