#!/usr/bin/env python3
"""
计算 Boros Long 策略的平均持仓时间

方法：
1. 从 position_count 列识别每个仓位的开设和平仓时间点
2. 计算每次持仓的持续时间
3. 计算所有持仓时间的加权平均值

数据源: samples/strategy-example/result/boros.long.account.csv
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 读取数据
print("Loading data...")
df = pd.read_csv(
    'samples/strategy-example/result/boros.long.account.csv',
    header=[0, 1],
    index_col=0
)
df.index = pd.to_datetime(df.index)

# 获取总仓位数据 (binance + hyperliquid)
binance_pos = df[('binance_dec26', 'position_count')].astype(float)
hl_pos = df[('hyperliquid_dec26', 'position_count')].astype(float)
total_pos = binance_pos + hl_pos

print(f"Data range: {df.index[0]} to {df.index[-1]}")
print(f"Total rows: {len(df)}")

# ============================================
# 计算每个仓位的持有时间
# ============================================
# 方法：
# 1. position 从 0 -> 正数：开仓
# 2. position 从正数 -> 0：平仓
# 3. 每次持仓时间 = 平仓时间 - 开仓时间

holding_durations = []
current_entry_time = None

for i, (timestamp, position) in enumerate(total_pos.items()):
    if i == 0:
        # 初始状态
        if position > 0:
            current_entry_time = timestamp
    else:
        prev_position = total_pos.iloc[i-1]
        
        # 检测开仓 (从 0 到 正数)
        if prev_position == 0 and position > 0:
            current_entry_time = timestamp
            
        # 检测平仓 (从 正数 到 0)
        elif prev_position > 0 and position == 0:
            if current_entry_time is not None:
                duration_minutes = (timestamp - current_entry_time).total_seconds() / 60
                if duration_minutes > 0:
                    holding_durations.append(duration_minutes)
                current_entry_time = None
            
        # 检测变化 (position 不为 0 且与上一个不同) - 可能换仓
        elif prev_position != position and position > 0 and current_entry_time is not None:
            # 可能是部分平仓又开仓，按新开仓算
            duration_minutes = (timestamp - current_entry_time).total_seconds() / 60
            if duration_minutes > 0:
                holding_durations.append(duration_minutes)
            current_entry_time = timestamp

# 检查最后是否还有未平仓的仓位
if current_entry_time is not None:
    last_timestamp = total_pos.index[-1]
    duration_minutes = (last_timestamp - current_entry_time).total_seconds() / 60
    if duration_minutes > 0:
        holding_durations.append(duration_minutes)

# ============================================
# 计算结果
# ============================================
if len(holding_durations) > 0:
    holding_durations = np.array(holding_durations)
    
    avg_holding_minutes = holding_durations.mean()
    median_holding_minutes = np.median(holding_durations)
    total_holding_minutes = holding_durations.sum()
    max_holding_minutes = holding_durations.max()
    min_holding_minutes = holding_durations.min()
    
    print(f"\n{'='*60}")
    print(f"Boros Long Average Holding Time Analysis")
    print(f"{'='*60}")
    print(f"Number of positions (round-trips): {len(holding_durations)}")
    print(f"Average holding time: {avg_holding_minutes:.2f} minutes ({avg_holding_minutes/60:.2f} hours)")
    print(f"Median holding time: {median_holding_minutes:.2f} minutes ({median_holding_minutes/60:.2f} hours)")
    print(f"Max holding time: {max_holding_minutes:.2f} minutes ({max_holding_minutes/60:.2f} hours)")
    print(f"Min holding time: {min_holding_minutes:.2f} minutes ({min_holding_minutes/60:.2f} hours)")
    print(f"Total holding time: {total_holding_minutes:.2f} minutes ({total_holding_minutes/60:.2f} hours)")
    
    # 按小时统计分布
    print(f"\nHolding time distribution:")
    bins = [0, 60, 360, 1440, 4320, 10080]  # 1h, 6h, 1d, 3d, 1w
    labels = ['<1h', '1h-6h', '6h-1d', '1d-3d', '>3d']
    hist, _ = np.histogram(holding_durations, bins=bins)
    for label, count in zip(labels, hist):
        print(f"  {label}: {count} ({count/len(holding_durations)*100:.1f}%)")
else:
    print("No position data found!")

# ============================================
# 输出完整重跑指引
# ============================================
print(f"\n{'='*60}")
print(f"Complete Re-run Guide")
print(f"{'='*60}")
print(f"""
Data Location: samples/strategy-example/result/boros.long.account.csv

Run Command:
  /Users/florije/PycharmProjects/demeter/venv/bin/python \\
    samples/strategy-example/71_6_analyze_avg_holding.py

Output: Results printed to console

Dependencies:
  - pandas
  - numpy
  - boros.long.account.csv (42MB, 154078 rows)
  - Date range: 2025-09-10 to 2025-12-25
""")