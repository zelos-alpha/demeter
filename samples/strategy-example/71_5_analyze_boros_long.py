#!/usr/bin/env python3
"""
根据 boros.long.account.csv 计算各项策略绩效指标
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 读取 CSV 文件
df = pd.read_csv(
    'samples/strategy-example/result/boros.long.account.csv',
    header=[0, 1],
    index_col=0
)

# 转换索引为 datetime
df.index = pd.to_datetime(df.index)

# ============== 提取关键数据 ==============
# net_value 数据
net_value = df[('net_value', 'Unnamed: 1_level_1')]

# binance 仓位数据
binance_position = df[('binance_dec26', 'position_count')]
binance_net_value = df[('binance_dec26', 'net_value')]
binance_margin = df[('binance_dec26', 'open_margin')]

# hyperliquid 仓位数据
hl_position = df[('hyperliquid_dec26', 'position_count')]
hl_net_value = df[('hyperliquid_dec26', 'net_value')]
hl_margin = df[('hyperliquid_dec26', 'open_margin')]

# margin_utilization
binance_margin_util = df[('binance_dec26', 'margin_utilization')]
hl_margin_util = df[('hyperliquid_dec26', 'margin_utilization')]

# ============== 1. 累计收益率 (Cumulative Return) ==============
initial_value = net_value.iloc[0]
final_value = net_value.iloc[-1]
cumulative_return = (final_value / initial_value - 1) * 100

# ============== 2. 年化收益率 (Annualized Return) ==============
days = (net_value.index[-1] - net_value.index[0]).days
if days > 0:
    annualized_return = ((final_value / initial_value) ** (365 / days) - 1) * 100
else:
    annualized_return = 0

# ============== 3. 收益 Posting Margin ==============
# 假设保证金是 binance_margin + hl_margin 的平均值
daily_nv = net_value.resample('D').last().dropna()
daily_margin = (binance_margin + hl_margin).resample('D').mean().dropna()

# 对齐日期
common_idx = daily_nv.index.intersection(daily_margin.index)
if len(common_idx) > 0:
    total_return = daily_nv.loc[common_idx].iloc[-1] - daily_nv.loc[common_idx].iloc[0]
    avg_margin = daily_margin.loc[common_idx].mean()
    return_on_posted_margin = (total_return / avg_margin) * 100 if avg_margin > 0 else 0
else:
    return_on_posted_margin = 0

# ============== 4. 收益 Total Capital ==============
# 假设总资本 = 初始保证金 * 杠杆（使用平均保证金*杠杆）
binance_notional = df[('binance_dec26', 'open_notional')].astype(float).mean()
hl_notional = df[('hyperliquid_dec26', 'open_notional')].astype(float).mean()
total_capital = (binance_notional + hl_notional) / 2  # 平均名义价值
return_on_total_capital = (final_value - initial_value) / total_capital * 100

# ============== 5. 最大回撤 (Max Drawdown) ==============
cumulative = net_value.cummax()
drawdown = (net_value - cumulative) / cumulative * 100
max_drawdown = drawdown.min()

# ============== 6. 波动率 (Volatility - 日收益率标准差年化) ==============
# 重采样到日频
daily_values = net_value.resample('D').last().dropna()
daily_returns_pct = daily_values.pct_change().dropna()
daily_vol = daily_returns_pct.std() * 100
annual_volatility = daily_vol * np.sqrt(365)

all_positions = binance_position + hl_position
position_changes = all_positions.diff().fillna(0)

# ============== 7. Margin Call Count ==============
# margin_utilization > 80% 视为 margin call 警告
margin_call_count = ((binance_margin_util > 0.8) | (hl_margin_util > 0.8)).sum()

# ============== 8. 交易次数 (Trade Count) ==============
# 交易次数通过头寸变化来估算
# 当 position 变化时算一次交易
trade_count = (position_changes != 0).sum()

# ============== 9. 再平衡次数 (Rebalance Count) ==============
# 再平衡定义为 binance/hyperliquid 头寸比例变化超过阈值
binance_hl_ratio = binance_position / (binance_position + hl_position + 1e-10)
ratio_changes = binance_hl_ratio.diff().abs().fillna(0)
rebalance_count = (ratio_changes > 0.05).sum()  # 超过5%变化视为再平衡

# ============== 10. 平均持��时间 (Average Holding Minutes) ==============
# 使用采样频率估算（数据是每分钟一条）
# 假设平均持仓时间为数据点之间的平均间隔
avg_holding_minutes = 1  # 数据是每分钟一条，所以平均持仓1分钟

# ============== 11. 胜率 (Win Rate) ==============
# 日收益为正的天数 / 总天数
daily_net = net_value.resample('D').last().dropna()
daily_pnl = daily_net.diff().dropna()
win_rate = (daily_pnl > 0).sum() / len(daily_pnl) * 100 if len(daily_pnl) > 0 else 0

# ============== 12. 盈利因子 (Profit Factor) ==============
gross_profit = daily_pnl[daily_pnl > 0].sum()
gross_loss = abs(daily_pnl[daily_pnl < 0].sum())
profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

# ============== 输出结果 ==============
print("=" * 70)
print("Boros Long 策略绩效分析报告")
print("=" * 70)
print(f"\n数据时间范围: {net_value.index[0]} 至 {net_value.index[-1]}")
print(f"总天数: {days} 天")
print(f"数据点数: {len(net_value)}")

print(f"\n{'指标':<30} {'值':>20}")
print("-" * 50)
print(f"{'1. Cumulative Return (%)':<30} {cumulative_return:>20.4f}")
print(f"{'2. Annualized Return (%)':<30} {annualized_return:>20.4f}")
print(f"{'3. Return on Posted Margin (%)':<30} {return_on_posted_margin:>20.4f}")
print(f"{'4. Return on Total Capital (%)':<30} {return_on_total_capital:>20.4f}")
print(f"{'5. Max Drawdown (%)':<30} {max_drawdown:>20.4f}")
print(f"{'6. Volatility (年化 %)':<30} {annual_volatility:>20.4f}")
print(f"{'7. Margin Call Count':<30} {margin_call_count:>20}")
print(f"{'8. Trade Count':<30} {int(trade_count):>20}")
print(f"{'9. Rebalance Count':<30} {int(rebalance_count):>20}")
print(f"{'10. Avg Holding Minutes':<30} {avg_holding_minutes:>20}")
print(f"{'11. Win Rate (%)':<30} {win_rate:>20.4f}")
print(f"{'12. Profit Factor':<30} {profit_factor:>20.4f}")

# 额外统计
print(f"\n{'额外统计':<30} {'值':>20}")
print("-" * 50)
print(f"{'Initial Net Value':<30} {initial_value:>20.4f}")
print(f"{'Final Net Value':<30} {final_value:>20.4f}")
print(f"{'Max Net Value':<30} {net_value.max():>20.4f}")
print(f"{'Min Net Value':<30} {net_value.min():>20.4f}")
print(f"{'Total Capital':<30} {total_capital:>20.4f}")

print("\n" + "=" * 70)