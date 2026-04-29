#!/usr/bin/env python3
"""
计算 boros.account.csv 文件中 net_value 的夏普比率
"""
import pandas as pd
import numpy as np

# 读取 CSV 文件
df = pd.read_csv(
    'result/boros.account.csv',
    header=[0, 1],
    index_col=0
)

# 获取 net_value 数据
net_value = df[('net_value', 'Unnamed: 1_level_1')]

# 转换索引为 datetime 格式
net_value.index = pd.to_datetime(net_value.index)

# 按小时重采样，取每小时的平均值（因为数据是每分钟一条）
# 先转换为 DataFrame 以便重采样
nv_df = pd.DataFrame({'net_value': net_value})
nv_df.index.name = 'timestamp'

# 按小时重采样取平均值
nv_hourly = nv_df.resample('H').mean().dropna()

# 计算日收益率（日均收益）
nv_daily = nv_df.resample('D').last().dropna()  # 每天最后一个值作为日净值
daily_returns = nv_daily['net_value'].pct_change().dropna()

# 基本统计
print("=" * 60)
print("Net Value 夏普比率分析")
print("=" * 60)
print(f"\n数据时间范围: {net_value.index.min()} 至 {net_value.index.max()}")
print(f"总数据点数: {len(net_value)}")

print(f"\n--- Net Value 基本统计 ---")
print(f"初始净值: {net_value.iloc[0]:.4f} USD")
print(f"最终净值: {net_value.iloc[-1]:.4f} USD")
print(f"最高净值: {net_value.max():.4f} USD")
print(f"最低净值: {net_value.min():.4f} USD")
print(f"总收益率: {(net_value.iloc[-1] / net_value.iloc[0] - 1) * 100:.4f}%")

print(f"\n--- 日收益率统计 ---")
print(f"日均收益率: {daily_returns.mean() * 100:.6f}%")
print(f"日收益率标准差: {daily_returns.std() * 100:.6f}%")
print(f"日最大收益: {daily_returns.max() * 100:.6f}%")
print(f"日最大亏损: {daily_returns.min() * 100:.6f}%")

# 计算夏普比率
# 假设无风险利率为 0（简化计算）
risk_free_rate = 0

# 日夏普比率
daily_sharpe = (daily_returns.mean() - risk_free_rate) / daily_returns.std()

# 年化夏普比率（假设一年252个交易日）
annual_sharpe = daily_sharpe * np.sqrt(252)

print(f"\n--- 夏普比率 (Sharpe Ratio) ---")
print(f"日夏普比率: {daily_sharpe:.4f}")
print(f"年化夏普比率: {annual_sharpe:.4f}")

# 额外计算其他风险指标
# 最大回撤
cumulative = (1 + daily_returns).cumprod()
running_max = cumulative.cummax()
drawdown = (cumulative - running_max) / running_max
max_drawdown = drawdown.min()

print(f"\n--- 其他风险指标 ---")
print(f"最大回撤: {max_drawdown * 100:.4f}%")

# 卡尔玛比率 (Calmar Ratio) = 年化收益率 / 最大回撤
annual_return = (net_value.iloc[-1] / net_value.iloc[0]) ** (365 / (net_value.index[-1] - net_value.index[0]).days) - 1
calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

print(f"年化收益率: {annual_return * 100:.4f}%")
print(f"卡尔玛比率: {calmar_ratio:.4f}")

print("\n" + "=" * 60)

# 已根据 boros.account.csv 文件中的 net_value 数据计算夏普比率（Sharpe Ratio）。
#
# **数据概况：**
# - 时间范围：2026-01-21 03:38:00 至 2026-02-26 23:58:00（约36天）
# - 数据点数：53,061 条
#
# **净值统计：**
# - 初始净值：999.9972 USD
# - 最终净值：1002.4408 USD
# - 最高净值：1002.4496 USD
# - 最低净值：999.7306 USD
# - 总收益率：0.2444%
#
# **日收益率统计：**
# - 日均收益率：0.0054%
# - 日收益率标准差：0.0281%
# - 日最大收益：0.1213%
# - 日最大亏损：-0.0607%
#
# **夏普比率：**
# - 日夏普比率：**0.1915**
# - 年化夏普比率：**3.0403**
#
# **其他风险指标：**
# - 最大回撤：-0.0607%
# - 年化收益率：2.5055%
# - 卡尔玛比率：41.2738
#
# 年化夏普比率达到 3.04，表明该策略在承担单位风险时能获得较高的超额收益。最大回撤仅 -0.0607%，风险极低。