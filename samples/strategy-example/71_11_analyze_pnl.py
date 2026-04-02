"""
PnL Analysis Script for Boros Long Account
Analyzes net value, market rates, and position holding periods
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Read the CSV file with proper header handling
df = pd.read_csv('samples/strategy-example/result/boros.long.account.csv', 
                 skiprows=2,  # Skip the two header rows
                 header=None)

# Assign column names based on the structure
col_names = [
    'timestamp',
    'total_net_value',
    'tokens',
    # Binance columns
    'binance_net_value',
    'binance_realized_pnl',
    'binance_unrealized_pnl',
    'binance_accrued_payment',
    'binance_accrued_fees',
    'binance_mtm_value',
    'binance_upfront_fixed_cost',
    'binance_upfront_opening_fee',
    'binance_position_count',
    'binance_open_notional',
    'binance_pay_fixed_notional',
    'binance_receive_fixed_notional',
    'binance_current_mark_rate',
    'binance_open_margin',
    'binance_margin_utilization',
    'binance_leverage',
    'binance_required_margin',
    # Hyperliquid columns
    'hyperliquid_net_value',
    'hyperliquid_realized_pnl',
    'hyperliquid_unrealized_pnl',
    'hyperliquid_accrued_payment',
    'hyperliquid_accrued_fees',
    'hyperliquid_mtm_value',
    'hyperliquid_upfront_fixed_cost',
    'hyperliquid_upfront_opening_fee',
    'hyperliquid_position_count',
    'hyperliquid_open_notional',
    'hyperliquid_pay_fixed_notional',
    'hyperliquid_receive_fixed_notional',
    'hyperliquid_current_mark_rate',
    'hyperliquid_open_margin',
    'hyperliquid_margin_utilization',
    'hyperliquid_leverage',
    'hyperliquid_required_margin',
    # Price
    'price'
]

df.columns = col_names

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"数据形状: {df.shape}")
print(f"日期范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")

# Calculate total position count (both markets combined)
df['total_position_count'] = df['binance_position_count'] + df['hyperliquid_position_count']

# Define holding periods - when position_count > 0 for continuous periods
df['is_holding'] = df['total_position_count'] > 0

# Identify holding period changes
df['holding_change'] = df['is_holding'].ne(df['is_holding'].shift())
df['holding_period_id'] = df['holding_change'].cumsum()

# Calculate PnL for each holding period
holding_periods = df[df['is_holding']].groupby('holding_period_id').agg({
    'timestamp': ['min', 'max', 'count'],
    'total_net_value': ['first', 'last', 'min', 'max'],
    'binance_position_count': 'max',
    'hyperliquid_position_count': 'max',
    'binance_realized_pnl': 'last',
    'hyperliquid_realized_pnl': 'last'
}).reset_index()

holding_periods.columns = ['period_id', 'start_time', 'end_time', 'duration_minutes', 
                          'nv_start', 'nv_end', 'nv_min', 'nv_max',
                          'binance_positions', 'hyperliquid_positions',
                          'binance_rpnl', 'hyperliquid_rpnl']

# Calculate net change for each period
holding_periods['nv_change'] = holding_periods['nv_end'] - holding_periods['nv_start']
holding_periods['pnl'] = holding_periods['nv_change']
holding_periods['duration_hours'] = holding_periods['duration_minutes'] / 60

# Sort by PnL (ascending to show biggest losses first)
holding_periods_sorted = holding_periods.sort_values('pnl', ascending=True)

print("\n=== 亏损最多的前20个持仓周期 ===")
print(f"{'周期ID':<8} {'开始时间':<20} {'结束时间':<20} {'时长(小时)':<12} {'起始净值':<12} {'结束净值':<12} {'净值变化':<12}")
print("-" * 110)

top_20_losses = holding_periods_sorted.head(20)
for idx, row in top_20_losses.iterrows():
    print(f"{int(row['period_id']):<8} {str(row['start_time'])[:19]:<20} {str(row['end_time'])[:19]:<20} {row['duration_hours']:<12.2f} {row['nv_start']:<12.4f} {row['nv_end']:<12.4f} {row['pnl']:<12.4f}")

# Also show summary statistics
print("\n=== 总体统计 ===")
print(f"总持仓周期数量: {len(holding_periods)}")
print(f"盈利周期数量: {len(holding_periods[holding_periods['pnl'] > 0])}")
print(f"亏损周期数量: {len(holding_periods[holding_periods['pnl'] < 0])}")
print(f"平均持仓时长: {holding_periods['duration_hours'].mean():.2f} 小时")
print(f"总净值变化: {holding_periods['pnl'].sum():.4f}")

# Show the top 20 loss details in a more detailed format
print("\n=== 亏损最多的前20个持仓周期详细信息 ===")
for idx, row in top_20_losses.iterrows():
    print(f"\n周期 {int(row['period_id'])}:")
    print(f"  开始时间: {row['start_time']}")
    print(f"  结束时间: {row['end_time']}")
    print(f"  持仓时长: {row['duration_hours']:.2f} 小时 ({row['duration_minutes']:.0f} 分钟)")
    print(f"  起始净值: {row['nv_start']:.6f}")
    print(f"  结束净值: {row['nv_end']:.6f}")
    print(f"  净值变化: {row['pnl']:.6f}")
    print(f"  Binance持仓数: {int(row['binance_positions'])}")
    print(f"  Hyperliquid持仓数: {int(row['hyperliquid_positions'])}")

# Save to CSV
holding_periods_sorted.to_csv('samples/strategy-example/result/holding_periods_analysis.csv', index=False)
print(f"\n完整分析数据已保存至: samples/strategy-example/result/holding_periods_analysis.csv")
