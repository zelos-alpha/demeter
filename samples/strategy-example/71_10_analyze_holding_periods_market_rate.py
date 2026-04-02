#!/usr/bin/env python3
"""
分析 Boros Long 策略的持仓周期
- remaining_notional 连续大于0则认为是持仓周期
- 绘制每个持仓周期内两个市场 market_rate 的变化曲线
- 同时显示总净值 (net_value)
- 每个仓位一个文件，文件放到 boros_long 文件夹里面
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
import os
warnings.filterwarnings('ignore')

# 设置输出目录
OUTPUT_DIR = 'boros_long'

# 读取数据
print("Loading data...")
df = pd.read_csv(
    'boros.long.account.csv',
    header=[0, 1],
    index_col=0
)
df.index = pd.to_datetime(df.index)

print(f"Data range: {df.index[0]} to {df.index[-1]}")
print(f"Total rows: {len(df)}")

# ============================================
# 获取 remaining_notional 和 market_rate 数据
# ============================================
# 使用 open_notional 作为 remaining_notional 的代理
# Binace: column 50 (open_notional)
# Hyperliquid: column 67 (open_notional)
binance_open_notional = df[('binance_dec26', 'open_notional')].astype(float)
hl_open_notional = df[('hyperliquid_dec26', 'open_notional')].astype(float)

# 总 remaining_notional = 两个市场的 open_notional 之和
remaining_notional = binance_open_notional + hl_open_notional

# market_rate - Binace: column 53 (current_mark_rate)
# market_rate - Hyperliquid: column 70 (current_mark_rate)
binance_market_rate = df[('binance_dec26', 'current_mark_rate')].astype(float)
hl_market_rate = df[('hyperliquid_dec26', 'current_mark_rate')].astype(float)

# 获取每个市场的 net_value
binance_net_value = df[('binance_dec26', 'net_value')].astype(float)
hl_net_value = df[('hyperliquid_dec26', 'net_value')].astype(float)

# 总 net_value = 两个市场的 net_value 之和
net_value = binance_net_value + hl_net_value

print(f"\nRemaining notional stats:")
print(f"  Min: {remaining_notional.min()}")
print(f"  Max: {remaining_notional.max()}")
print(f"  Mean: {remaining_notional.mean():.2f}")

print(f"\nBinance market_rate stats:")
print(f"  Min: {binance_market_rate.min():.6f}")
print(f"  Max: {binance_market_rate.max():.6f}")
print(f"  Mean: {binance_market_rate.mean():.6f}")

print(f"\nHyperliquid market_rate stats:")
print(f"  Min: {hl_market_rate.min():.6f}")
print(f"  Max: {hl_market_rate.max():.6f}")
print(f"  Mean: {hl_market_rate.mean():.6f}")

# ============================================
# 找出所有连续持仓周期
# ============================================
holding_periods = []  # (start_idx, end_idx, start_time, end_time)
in_position = False
current_start_idx = None

for i in range(len(remaining_notional)):
    timestamp = remaining_notional.index[i]
    rn = remaining_notional.iloc[i]
    
    if i == 0:
        if rn > 0:
            in_position = True
            current_start_idx = i
    else:
        prev_rn = remaining_notional.iloc[i-1]
        
        # 进入持仓周期
        if prev_rn == 0 and rn > 0:
            in_position = True
            current_start_idx = i
            
        # 退出持仓周期
        elif prev_rn > 0 and rn == 0:
            if in_position and current_start_idx is not None:
                holding_periods.append({
                    'start_idx': current_start_idx,
                    'end_idx': i - 1,
                    'start': remaining_notional.index[current_start_idx],
                    'end': remaining_notional.index[i - 1]
                })
            in_position = False
            current_start_idx = None
            
        # 保持在持仓周期内
        elif prev_rn > 0 and rn > 0:
            pass
        
        # 从非持仓到非持仓
        else:
            pass

# 如果最后还在持仓区间
if in_position and current_start_idx is not None:
    last_idx = len(remaining_notional) - 1
    holding_periods.append({
        'start_idx': current_start_idx,
        'end_idx': last_idx,
        'start': remaining_notional.index[current_start_idx],
        'end': remaining_notional.index[last_idx]
    })

print(f"\n{'='*60}")
print(f"Holding Periods Analysis")
print(f"{'='*60}")
print(f"Number of holding periods: {len(holding_periods)}")

# ============================================
# 为所有持仓周期绘制一个综合图表
# ============================================
print(f"\nGenerating combined chart...")

# 创建综合图表
fig, ax1 = plt.subplots(figsize=(16, 8))

# 左Y轴: Binance & Hyperliquid Market Rate (使用同一坐标轴)
color_bn = '#2E86AB'
color_hl = '#E94F37'
ax1.set_xlabel('Time', fontsize=12)
ax1.set_ylabel('Market Rate', fontsize=12)
ax1.plot(binance_market_rate.index, binance_market_rate.values, color=color_bn, linewidth=0.8, alpha=0.7, label='Binance Market Rate')
ax1.plot(hl_market_rate.index, hl_market_rate.values, color=color_hl, linewidth=0.8, alpha=0.7, label='Hyperliquid Market Rate')
ax1.tick_params(axis='y')

# 右Y轴: Net Value
ax2 = ax1.twinx()
color_nv = '#28A745'
ax2.set_ylabel('Net Value (USD)', color=color_nv, fontsize=12)
ax2.plot(net_value.index, net_value.values, color=color_nv, linewidth=1.2, linestyle='--', alpha=0.8, label='Net Value')
ax2.tick_params(axis='y', labelcolor=color_nv)

# 为每个持仓周期添加不同颜色的背景区域
colors = plt.cm.tab20(np.linspace(0, 1, 20))
extra_colors = plt.cm.tab20b(np.linspace(0, 1, 20))
extra_colors2 = plt.cm.tab20c(np.linspace(0, 1, 20))
all_colors = np.vstack([colors, extra_colors, extra_colors2])

for idx, period in enumerate(holding_periods):
    start_time = period['start']
    end_time = period['end']
    color = all_colors[idx % len(all_colors)]
    ax1.axvspan(start_time, end_time, alpha=0.15, color=color, zorder=0)

# 设置标题
plt.title(f'Boros Long Strategy - All {len(holding_periods)} Holding Periods\nBinance & Hyperliquid Market Rate (Same Axis) + Net Value', 
          fontsize=14, fontweight='bold')

# 设置X轴日期格式
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

# 合并图例
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)

# 添加网格
ax1.grid(True, alpha=0.3)

plt.tight_layout()

# 保存综合图表
output_path = os.path.join(OUTPUT_DIR, 'all_holding_periods.png')
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"  Saved: all_holding_periods.png")

# ============================================
# 图2: Binance Market Rate vs Net Value 线图
# ============================================
print(f"\nGenerating Binance Market Rate & Net Value chart...")

fig, ax1 = plt.subplots(figsize=(14, 6))

# 左Y轴: Binance Market Rate
color = '#2E86AB'
ax1.set_xlabel('Time', fontsize=12)
ax1.set_ylabel('Binance Market Rate', color=color, fontsize=12)
ax1.plot(binance_market_rate.index, binance_market_rate.values, color=color, linewidth=0.8, alpha=0.7, label='Binance Market Rate')
ax1.tick_params(axis='y', labelcolor=color)

# 右Y轴: Net Value
ax2 = ax1.twinx()
color = '#28A745'
ax2.set_ylabel('Net Value (USD)', color=color, fontsize=12)
ax2.plot(net_value.index, net_value.values, color=color, linewidth=1.0, alpha=0.8, label='Net Value')
ax2.tick_params(axis='y', labelcolor=color)

plt.title('Binance Market Rate & Net Value Over Time', fontsize=14, fontweight='bold')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
ax1.grid(True, alpha=0.3)
plt.tight_layout()

output_path = os.path.join(OUTPUT_DIR, 'binance_rate_netvalue_line.png')
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"  Saved: binance_rate_netvalue_line.png")

# ============================================
# 图3: Hyperliquid Market Rate vs Net Value 线图
# ============================================
print(f"Generating Hyperliquid Market Rate & Net Value chart...")

fig, ax1 = plt.subplots(figsize=(14, 6))


# 左Y轴: Hyperliquid Market Rate
color = '#E94F37'
ax1.set_xlabel('Time', fontsize=12)
ax1.set_ylabel('Hyperliquid Market Rate', color=color, fontsize=12)
ax1.plot(hl_market_rate.index, hl_market_rate.values, color=color, linewidth=0.8, alpha=0.7, label='Hyperliquid Market Rate')
ax1.tick_params(axis='y', labelcolor=color)

# 右Y轴: Net Value
ax2 = ax1.twinx()
color = '#28A745'
ax2.set_ylabel('Net Value (USD)', color=color, fontsize=12)
ax2.plot(net_value.index, net_value.values, color=color, linewidth=1.0, alpha=0.8, label='Net Value')
ax2.tick_params(axis='y', labelcolor=color)

plt.title('Hyperliquid Market Rate & Net Value Over Time', fontsize=14, fontweight='bold')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
ax1.grid(True, alpha=0.3)
plt.tight_layout()

output_path = os.path.join(OUTPUT_DIR, 'hyperliquid_rate_netvalue_line.png')
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"  Saved: hyperliquid_rate_netvalue_line.png")

# ============================================
# 图4: Binance市场各自的 net_value & market_rate 线图
# ============================================
print(f"\nGenerating Binance Market - Net Value & Market Rate chart...")

fig, ax1 = plt.subplots(figsize=(14, 6))

# 左Y轴: Binance Market Rate
color = '#2E86AB'
ax1.set_xlabel('Time', fontsize=12)
ax1.set_ylabel('Binance Market Rate', color=color, fontsize=12)
ax1.plot(binance_market_rate.index, binance_market_rate.values, color=color, linewidth=0.8, alpha=0.7, label='Binance Market Rate')
ax1.tick_params(axis='y', labelcolor=color)

# 右Y轴: Binance Net Value
ax2 = ax1.twinx()
color = '#28A745'
ax2.set_ylabel('Binance Net Value (USD)', color=color, fontsize=12)
ax2.plot(binance_net_value.index, binance_net_value.values, color=color, linewidth=1.0, alpha=0.8, label='Binance Net Value')
ax2.tick_params(axis='y', labelcolor=color)

plt.title('Binance Market - Net Value & Market Rate Over Time', fontsize=14, fontweight='bold')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
ax1.grid(True, alpha=0.3)
plt.tight_layout()

output_path = os.path.join(OUTPUT_DIR, 'binance_market_rate_netvalue.png')
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"  Saved: binance_market_rate_netvalue.png")

# ============================================
# 图5: Hyperliquid市场各自的 net_value & market_rate 线图
# ============================================
print(f"Generating Hyperliquid Market - Net Value & Market Rate chart...")

fig, ax1 = plt.subplots(figsize=(14, 6))


# 左Y轴: Hyperliquid Market Rate
color = '#E94F37'
ax1.set_xlabel('Time', fontsize=12)
ax1.set_ylabel('Hyperliquid Market Rate', color=color, fontsize=12)
ax1.plot(hl_market_rate.index, hl_market_rate.values, color=color, linewidth=0.8, alpha=0.7, label='Hyperliquid Market Rate')
ax1.tick_params(axis='y', labelcolor=color)

# 右Y轴: Hyperliquid Net Value
ax2 = ax1.twinx()
color = '#28A745'
ax2.set_ylabel('Hyperliquid Net Value (USD)', color=color, fontsize=12)
ax2.plot(hl_net_value.index, hl_net_value.values, color=color, linewidth=1.0, alpha=0.8, label='Hyperliquid Net Value')
ax2.tick_params(axis='y', labelcolor=color)

plt.title('Hyperliquid Market - Net Value & Market Rate Over Time', fontsize=14, fontweight='bold')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
ax1.grid(True, alpha=0.3)
plt.tight_layout()

output_path = os.path.join(OUTPUT_DIR, 'hyperliquid_market_rate_netvalue.png')
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"  Saved: hyperliquid_market_rate_netvalue.png")

print(f"\n{'='*60}")
print(f"Complete!")
print(f"{'='*60}")
print(f"Charts saved to: {OUTPUT_DIR}")
print(f"Total holding periods: {len(holding_periods)}")
