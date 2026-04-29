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
    'result/boros.long.account.csv',
    header=[0, 1],
    index_col=0
)

# 转换索引为 datetime
df.index = pd.to_datetime(df.index)

# ============== 提取关键数据 ==============
# net_value 数据
net_value = df[('net_value', 'Unnamed: 1_level_1')].astype(float)

# binance 仓位数据
binance_position = df[('binance_dec26', 'position_count')].astype(float)
binance_net_value = df[('binance_dec26', 'net_value')].astype(float)
binance_margin = df[('binance_dec26', 'open_margin')].astype(float)

# hyperliquid 仓位数据
hl_position = df[('hyperliquid_dec26', 'position_count')].astype(float)
hl_net_value = df[('hyperliquid_dec26', 'net_value')].astype(float)
hl_margin = df[('hyperliquid_dec26', 'open_margin')].astype(float)

# margin_utilization
binance_margin_util = df[('binance_dec26', 'margin_utilization')].astype(float)
hl_margin_util = df[('hyperliquid_dec26', 'margin_utilization')].astype(float)

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

# ============== 7. 交易次数 (Trade Count) ==============
# 交易次数通过头寸变化来估算
# 当 position 变化时算一次交易
trade_count = (position_changes != 0).sum()

# ============== 8. 再平衡次数 (Rebalance Count) ==============
# 再平衡定义为 binance/hyperliquid 头寸比例变化超过阈值
binance_hl_ratio = binance_position / (binance_position + hl_position + 1e-10)
ratio_changes = binance_hl_ratio.diff().abs().fillna(0)
rebalance_count = (ratio_changes > 0.05).sum()  # 超过5%变化视为再平衡

# ============== 9. 平均持仓时间 (Average Holding Minutes) ==============
# 计算每个仓位的持有时间，然后取平均
# 同时计算每个仓位的盈亏，用于计算胜率和盈利因子
all_positions = (binance_position + hl_position).astype(float)

holding_durations = []
position_pnls = []  # 每个持仓周期的盈亏
current_entry_time = None
current_entry_nv = None  # 开仓时的净值

for i in range(len(all_positions)):
    timestamp = all_positions.index[i]
    position = all_positions.iloc[i]
    current_nv = net_value.iloc[i]  # 当时的净值
    
    if i == 0:
        if position > 0:
            current_entry_time = timestamp
            current_entry_nv = current_nv
    else:
        prev_position = all_positions.iloc[i-1]
        
        # 开仓: 从 0 到 正数
        if prev_position == 0 and position > 0:
            current_entry_time = timestamp
            current_entry_nv = current_nv
            
        # 平仓: 从 正数 到 0
        elif prev_position > 0 and position == 0:
            if current_entry_time is not None:
                duration_minutes = (timestamp - current_entry_time).total_seconds() / 60
                pnl = current_nv - current_entry_nv  # 持仓期间的盈亏
                if duration_minutes > 0:
                    holding_durations.append(duration_minutes)
                    position_pnls.append(pnl)
                current_entry_time = None
                current_entry_nv = None
                
        # 换仓: 仓位 > 0 但与上一个不同
        elif prev_position != position and position > 0 and current_entry_time is not None:
            duration_minutes = (timestamp - current_entry_time).total_seconds() / 60
            pnl = current_nv - current_entry_nv
            if duration_minutes > 0:
                holding_durations.append(duration_minutes)
                position_pnls.append(pnl)
            current_entry_time = timestamp
            current_entry_nv = current_nv

# 检查最后是否还有未平仓的仓位
if current_entry_time is not None:
    last_timestamp = all_positions.index[-1]
    last_nv = net_value.iloc[-1]
    duration_minutes = (last_timestamp - current_entry_time).total_seconds() / 60
    pnl = last_nv - current_entry_nv
    if duration_minutes > 0:
        holding_durations.append(duration_minutes)
        position_pnls.append(pnl)

if len(holding_durations) > 0:
    avg_holding_minutes = np.mean(holding_durations)
else:
    avg_holding_minutes = 0

# ============== 10. 胜率 (Win Rate) ==============
# 基于每个持仓周期的盈亏计算（即每个 round-trip 的盈亏）
# 盈利的持仓次数 / 总持仓次数
if len(position_pnls) > 0:
    winning_positions = sum(1 for pnl in position_pnls if pnl > 0)
    win_rate = winning_positions / len(position_pnls) * 100
    
    # 盈利因子 = 总盈利 / 总亏损
    gross_profit = sum(pnl for pnl in position_pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in position_pnls if pnl < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
else:
    win_rate = 0
    profit_factor = 0

# ============== 11. 盈利因子 (Profit Factor) ==============
# 已在上方基于持仓周期计算

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
print(f"{'7. Trade Count':<30} {int(trade_count):>20}")
print(f"{'8. Rebalance Count':<30} {int(rebalance_count):>20}")
print(f"{'9. Avg Holding Minutes':<30} {avg_holding_minutes:>20.2f}")
print(f"{'10. Win Rate (%)':<30} {win_rate:>20.4f}")
print(f"{'11. Profit Factor':<30} {profit_factor:>20.4f}")
print(f"{'# of Positions':<30} {len(holding_durations):>20}")

# 额外统计
print(f"\n{'额外统计':<30} {'值':>20}")
print("-" * 50)
print(f"{'Initial Net Value':<30} {initial_value:>20.4f}")
print(f"{'Final Net Value':<30} {final_value:>20.4f}")
print(f"{'Max Net Value':<30} {net_value.max():>20.4f}")
print(f"{'Min Net Value':<30} {net_value.min():>20.4f}")
print(f"{'Total Capital':<30} {total_capital:>20.4f}")

print("\n" + "=" * 70)