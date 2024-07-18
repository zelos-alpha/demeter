from enum import Enum


class MetricEnum(Enum):
    return_value = "Return"
    return_rate = "Rate of Return"
    annualized_return = "Annualized Return"
    max_draw_down = "Max Draw Down"
    sharpe_ratio = "Sharpe Ratio"
    volatility = "Volatility"
    alpha = "alpha"
    beta = "beta"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
