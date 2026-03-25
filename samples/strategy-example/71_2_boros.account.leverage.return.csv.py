#!/usr/bin/env python3
"""
计算杠杆收益率
基于 boros.account.csv 数据，计算收益率并输出到 boros.account.leverage.return.csv
"""

import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime

# 读取CSV文件
input_file = 'result/boros.account.csv'
output_file = 'result/boros.account.leverage.return.csv'

# 读取CSV，跳过前两行（l1, l2是表头）
df = pd.read_csv(input_file, header=[0, 1])

# 重置索引，让timestamp成为普通列
df = df.reset_index()

# 查看列名
print("Columns:", df.columns.tolist()[:10])

# 获取timestamp列
timestamp_col = df.columns[0]
print(f"Timestamp column: {timestamp_col}")

# 提取需要的列
# Binance市场
binance_cols = {
    'net_value': ('binance_feb27', 'net_value'),
    'accrued_payment': ('binance_feb27', 'accrued_payment'),
    'accrued_fees': ('binance_feb27', 'accrued_fees'),
    'current_mark_rate': ('binance_feb27', 'current_mark_rate'),
}

# Hyperliquid市场
hyperliquid_cols = {
    'net_value': ('hyperliquid_feb27', 'net_value'),
    'accrued_payment': ('hyperliquid_feb27', 'accrued_payment'),
    'accrued_fees': ('hyperliquid_feb27', 'accrued_fees'),
    'current_mark_rate': ('hyperliquid_feb27', 'current_mark_rate'),
}

# 开仓规模
open_notional = Decimal('100')
open_margin = Decimal('20')

# 提取数据
binance_df = pd.DataFrame()
hyperliquid_df = pd.DataFrame()

for col_name, (market, field) in binance_cols.items():
    try:
        binance_df[col_name] = df[(market, field)]
    except KeyError:
        print(f"KeyError for binance {field}: {df.columns.tolist()[:5]}")

for col_name, (market, field) in hyperliquid_cols.items():
    try:
        hyperliquid_df[col_name] = df[(market, field)]
    except KeyError:
        print(f"KeyError for hyperliquid {field}")

# 转换时间戳
df['timestamp'] = pd.to_datetime(df[timestamp_col])

# 计算利率差 (diff_rate)
binance_rate = binance_df['current_mark_rate'].astype(float)
hyperliquid_rate = hyperliquid_df['current_mark_rate'].astype(float)
diff_rate = abs(binance_rate - hyperliquid_rate)

# 计算收益 (profit = open_notional * diff_rate)
profit = float(open_notional) * diff_rate

# 创建结果DataFrame
result_df = pd.DataFrame()
result_df['timestamp'] = df['timestamp']
result_df['diff_rate'] = diff_rate
result_df['profit'] = profit

# Binance市场：在00:00, 8:00, 16:00时间点，profit减去accrued_payment和accrued_fees
binance_accrued = binance_df['accrued_payment'].astype(float) + binance_df['accrued_fees'].astype(float)
hour = result_df['timestamp'].dt.hour
minute = result_df['timestamp'].dt.minute

# 判断是否为指定时间点 (00:00, 08:00, 16:00)
binance_settlement_hours = [0, 8, 16]
is_binance_settlement = (hour.isin(binance_settlement_hours)) & (minute == 0)

# 计算binance调整后的profit
result_df['profit_binance'] = profit.copy()
result_df.loc[is_binance_settlement, 'profit_binance'] = (
    profit[is_binance_settlement] - binance_accrued[is_binance_settlement]
)

# Hyperliquid市场：整点时间点，profit减去accrued_payment和accrued_fees
hyperliquid_accrued = hyperliquid_df['accrued_payment'].astype(float) + hyperliquid_df['accrued_fees'].astype(float)
is_hyperliquid_settlement = (minute == 0)

# 计算hyperliquid调整后的profit
result_df['profit_hyperliquid'] = profit.copy()
result_df.loc[is_hyperliquid_settlement, 'profit_hyperliquid'] = (
    profit[is_hyperliquid_settlement] - hyperliquid_accrued[is_hyperliquid_settlement]
)

# 总profit (取两个市场调整后的平均值或总和)
# 这里取两者的平均
result_df['profit_adjusted'] = (result_df['profit_binance'] + result_df['profit_hyperliquid']) / 2

# 计算收益率 (return_rate) = (当前profit - 上一个profit) / open_margin
# 使用累计profit来计算收益率
result_df['profit_cumulative'] = result_df['profit_adjusted'].cumsum()

# 计算每行与上一行的收益率
result_df['return_rate'] = result_df['profit_cumulative'].diff() / float(open_margin)

# 第一行没有前一行，设为NaN
result_df.loc[result_df.index[0], 'return_rate'] = np.nan

# 年化收益率 = (1 + minute_return_rate)^(minutes_per_year) - 1
# 使用简化公式：annualized_return = minute_return_rate * minutes_per_year
annualized_return_rate = result_df['return_rate'].mean()
print('\nannualized_return_rate', annualized_return_rate)

# 输出结果
print("\nResult DataFrame head:")
print(result_df.head(20))

print("\nResult DataFrame tail:")
print(result_df.tail(10))

# 保存到CSV
result_df.to_csv(output_file, index=False)
print(f"\n结果已保存到: {output_file}")
