#!/usr/bin/env python3
"""
分析 Boros Long 策略的持仓区间
- position_count > 0 则认为持仓
- 持仓时间统计为连续 position_count > 0 的区间
- 统计持仓区间数量、每个区间的持仓时间，并绘制图表
- 在图表中显示每个持仓周期的盈利数据
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings('ignore')

# 读取数据
print("Loading data...")
df = pd.read_csv(
    'result/boros.long.account.csv',
    header=[0, 1],
    index_col=0
)
df.index = pd.to_datetime(df.index)

# 获取总仓位数据
binance_position = df[('binance_dec26', 'position_count')].astype(float)
hl_position = df[('hyperliquid_dec26', 'position_count')].astype(float)
all_positions = binance_position + hl_position
net_value = df[('net_value', 'Unnamed: 1_level_1')].astype(float)

print(f"Data range: {df.index[0]} to {df.index[-1]}")
print(f"Total rows: {len(df)}")

# ============================================
# 找出所有连续持仓区间
# ============================================
holding_periods = []  # (start_time, end_time, duration_minutes, pnl)
in_position = False
current_start = None
current_start_nv = None

for i in range(len(all_positions)):
    timestamp = all_positions.index[i]
    position = all_positions.iloc[i]
    current_nv = net_value.iloc[i]
    
    if i == 0:
        if position > 0:
            in_position = True
            current_start = timestamp
            current_start_nv = current_nv
    else:
        prev_position = all_positions.iloc[i-1]
        
        # 进入持仓区间
        if prev_position == 0 and position > 0:
            in_position = True
            current_start = timestamp
            current_start_nv = current_nv
            
        # 退出持仓区间
        elif prev_position > 0 and position == 0:
            if in_position and current_start is not None:
                duration = (timestamp - current_start).total_seconds() / 60
                pnl = current_nv - current_start_nv
                if duration > 0:
                    holding_periods.append({
                        'start': current_start,
                        'end': timestamp,
                        'duration_minutes': duration,
                        'pnl': pnl
                    })
                in_position = False
                current_start = None
                
        # 保持在持仓区间内（position 仍然是 > 0）
        elif prev_position > 0 and position > 0:
            pass  # 继续持仓，不做任何操作
            
        # 从非持仓到非持仓（无持仓变化）
        else:
            pass

# 如果最后还在持仓区间
if in_position and current_start is not None:
    last_timestamp = all_positions.index[-1]
    last_nv = net_value.iloc[-1]
    duration = (last_timestamp - current_start).total_seconds() / 60
    pnl = last_nv - current_start_nv
    if duration > 0:
        holding_periods.append({
            'start': current_start,
            'end': last_timestamp,
            'duration_minutes': duration,
            'pnl': pnl
        })

# ============================================
# 统计结果
# ============================================
if len(holding_periods) > 0:
    durations = [p['duration_minutes'] for p in holding_periods]
    pnls = [p['pnl'] for p in holding_periods]
    
    total_holding_minutes = sum(durations)
    total_minutes_in_period = (df.index[-1] - df.index[0]).total_seconds() / 60
    holding_time_ratio = total_holding_minutes / total_minutes_in_period * 100
    
    print(f"\n{'='*60}")
    print(f"Holding Periods Analysis")
    print(f"{'='*60}")
    print(f"Number of holding periods: {len(holding_periods)}")
    print(f"Total holding time: {total_holding_minutes:.2f} minutes ({total_holding_minutes/60:.2f} hours)")
    print(f"Total period time: {total_minutes_in_period:.2f} minutes ({total_minutes_in_period/60:.2f} hours)")
    print(f"Holding time ratio: {holding_time_ratio:.2f}%")
    
    print(f"\n{'Duration statistics:'}")
    print(f"  Average: {np.mean(durations):.2f} minutes ({np.mean(durations)/60:.2f} hours)")
    print(f"  Median: {np.median(durations):.2f} minutes ({np.median(durations)/60:.2f} hours)")
    print(f"  Min: {np.min(durations):.2f} minutes")
    print(f"  Max: {np.max(durations):.2f} minutes ({np.max(durations)/60:.2f} hours)")
    
    print(f"\n{'PnL statistics:'}")
    print(f"  Total PnL: {sum(pnls):.4f}")
    print(f"  Winning periods: {sum(1 for p in pnls if p > 0)}/{len(pnls)}")
    print(f"  Win rate: {sum(1 for p in pnls if p > 0)/len(pnls)*100:.2f}%")
    
    # 打印所有持仓区间详情
    print(f"\n{'All holding periods (sorted by time):'}")
    print(f"{'#':<4} {'Start':<20} {'End':<20} {'Duration(min)':<15} {'PnL':<15}")
    print("-" * 75)
    for i, p in enumerate(holding_periods):
        print(f"{i+1:<4} {str(p['start'])[:19]:<20} {str(p['end'])[:19]:<20} {p['duration_minutes']:<15.2f} {p['pnl']:<15.4f}")
    
    # ============================================
    # 绘制图表 - 改进版
    # ============================================
    fig = plt.figure(figsize=(16, 14))
    
    # 子图1: 持仓时间线（在上方）
    ax1 = plt.subplot(2, 1, 1)
    ax1.set_title('Net Value with Holding Periods (Green = Position > 0)', fontsize=14, fontweight='bold')
    
    # 绘制净值的完整曲线（灰色背景）
    ax1.fill_between(net_value.index, net_value.values, alpha=0.2, color='gray')
    
    # 为每个持仓区间绘制绿色背景
    for p in holding_periods:
        ax1.axvspan(p['start'], p['end'], alpha=0.3, color='green')
    
    # 绘制净值曲线
    ax1.plot(net_value.index, net_value.values, color='#2E86AB', linewidth=0.5, label='Net Value')
    
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Net Value (USD)')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right')
    
    # 子图2: 每个持仓区间的持续时间和盈亏（按时间顺序）
    ax2 = plt.subplot(2, 1, 2)
    ax2.set_title('Holding Duration and PnL by Period (Ordered by Time)', fontsize=14, fontweight='bold')
    
    period_numbers = list(range(1, len(holding_periods) + 1))
    
    # 双Y轴
    ax2_twin = ax2.twinx()
    
    # 绘制持仓时间（柱状图）
    colors = ['green' if p > 0 else 'red' for p in pnls]
    bars = ax2.bar(period_numbers, durations, color=colors, alpha=0.6, label='Duration (min)')
    ax2.set_ylabel('Duration (minutes)', color='blue')
    ax2.tick_params(axis='y', labelcolor='blue')
    
    # 绘制盈亏（折线图，在右侧Y轴）
    line = ax2_twin.plot(period_numbers, pnls, 'o-', color='orange', linewidth=2, markersize=6, label='PnL')
    ax2_twin.set_ylabel('PnL', color='orange')
    ax2_twin.tick_params(axis='y', labelcolor='orange')
    ax2_twin.axhline(y=0, color='gray', linestyle='--', linewidth=1)
    
    # 在每个柱子上方标注盈亏值
    for i, (d, p) in enumerate(zip(durations, pnls)):
        if p > 0:
            ax2_twin.annotate(f'+{p:.2f}', (i+1, p), textcoords="offset points", 
                        xytext=(0, 5), ha='center', fontsize=7, color='green')
        else:
            ax2_twin.annotate(f'{p:.2f}', (i+1, p), textcoords="offset points",
                        xytext=(0, -10), ha='center', fontsize=7, color='red')
    
    ax2.set_xlabel('Holding Period # (chronological order)')
    ax2.set_xticks(period_numbers)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 添加图例
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    plt.tight_layout()
    
    # 保存图表
    output_path = 'result/holding_periods_analysis.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nChart saved to: {output_path}")
    
    plt.show()
    
else:
    print("No holding periods found!")

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
    samples/strategy-example/71_7_analyze_holding_periods.py

Output: 
  - Console output with statistics (all 27 holding periods with duration and PnL)
  - Chart: samples/strategy-example/result/holding_periods_analysis.png

Dependencies:
  - pandas, numpy, matplotlib
  - boros.long.account.csv (42MB, 154078 rows)
  - Date range: 2025-09-10 to 2025-12-25
""")