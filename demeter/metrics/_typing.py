from enum import Enum


class MetricEnum(Enum):
    """
    Types of Strategy Evaluation

    Annualized Return（年化收益率）：衡量投资在一年内的平均收益率。
    Sharpe Ratio（夏普比率）：衡量单位风险下的超额收益率。
    Max Drawdown（最大回撤）：衡量投资组合从最高点到最低点的最大损失。
    Calmar Ratio（卡尔玛比率）：衡量单位最大回撤下的年化收益率。
    Sortino Ratio（索提诺比率）：类似于夏普比率，但只考虑下行风险。
    Alpha（阿尔法）：衡量投资组合在调整了系统性风险后的超额收益率。
    Beta（贝塔）：衡量投资组合相对于市场基准的系统性风险。
    Volatility（波动率）：衡量投资组合收益率的标准差。
    Information Ratio（信息比率）：衡量单位跟踪误差下的超额收益率。
    Treynor Ratio（特雷诺比率）：衡量单位系统性风险下的超额收益率。
    """

    return_value = "return"
    return_rate = "rate of return"
    annualized_return = "Annualized Return"
    benchmark_return = "Benchmark Return"
    max_drawdown = "Max Drawdown"

    # final_equity = 4
    # profit = 5
    net_value_up_down_rate = 6
    eth_up_down_rate = 7
    position_fee_profit = 8
    position_fee_annualized_returns = 9
    position_market_time_rate = 10

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
