#!/usr/bin/env python3
"""
绘制 boros.account.csv 中 net_value 随时间变化的曲线图
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 读取 CSV 文件，跳过第一行（l1 表头），使用第二行作为列名
df = pd.read_csv(
    'result/boros.account.csv',
    header=[0, 1],  # 使用前两行作为多层索引列名
    index_col=0     # 第一列作为索引（时间）
)

# 获取 net_value 数据
# 列名是 ('net_value', 'Unnamed: 1_level_1') 因为第一行l1后面没有值
net_value = df[('net_value', 'Unnamed: 1_level_1')]

# 转换索引为 datetime 格式
net_value.index = pd.to_datetime(net_value.index)

# 打印基本信息
print(f"数据时间范围: {net_value.index.min()} 至 {net_value.index.max()}")
print(f"数据点数量: {len(net_value)}")
print(f"net_value 范围: {net_value.min():.4f} 至 {net_value.max():.4f}")

# 创建图表
fig, ax = plt.subplots(figsize=(14, 7))

# 绘制 net_value 曲线
ax.plot(net_value.index, net_value.values, linewidth=0.8, color='#2E86AB', label='Net Value')

# 设置标题和标签
ax.set_title('Net Value Curve Over Time (boros.account.csv)', fontsize=14, fontweight='bold')
ax.set_xlabel('Time', fontsize=12)
ax.set_ylabel('Net Value (USD)', fontsize=12)

# 格式化 x 轴日期显示
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))  # 每7天显示一个刻度
plt.xticks(rotation=45)

# 添加网格
ax.grid(True, alpha=0.3, linestyle='--')

# 添加图例
ax.legend(loc='upper right')

# 调整布局
plt.tight_layout()

# 保存图表
output_path = 'result/net_value_curve.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n图表已保存至: {output_path}")

# 显示图表
plt.show()