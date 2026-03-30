### 已根据 boros.long.account.csv 文件计算各项策略绩效指标。

**数据概况：**
- 时间范围：2025-09-10 至 2025-12-25（约106天）
- 数据点数：154,078 条

### 已根据 boros.long.account.csv 分析持仓区间并绘制图表。

**分析结果：**

| 指标 | 值 |
|------|------|
| **持仓区间数量** | 27 个 |
| **总持仓时间** | 150,258 分钟 (2,504 小时≈104天) |
| **总周期时间** | 154,077 分钟 (2,568 小时≈107天) |
| **持仓时间占比** | 97.52% |

**持仓时间统计：**
- 平均持仓时间：5,565.11 分钟 (≈92.75 小时≈3.9天)
- 中位数持仓时间：242 分钟 (≈4小时)
- 最短持仓：1 分钟
- 最长持仓：99,369 分钟 (≈1,656 小时≈69天)

**盈亏统计：**
- 盈利区间：23/27 (85.19%)
- 亏损区间：4/27 (14.81%)
- 总 PnL：-11.074

**重跑指引：**
```
数据文件：samples/strategy-example/result/boros.long.account.csv
数据范围：2025-09-10 至 2025-12-25（106天）

运行命令：
/Users/florije/PycharmProjects/demeter/venv/bin/python \
  samples/strategy-example/71_7_analyze_holding_periods.py

输出：
  - 控制台统计信息
  - 图表：samples/strategy-example/result/holding_periods_analysis.png
```

**分析脚本：**
- [`samples/strategy-example/71_7_analyze_holding_periods.py`](samples/strategy-example/71_7_analyze_holding_periods.py:1) - 持仓区间分析脚本
- 输出图表：`samples/strategy-example/result/holding_periods_analysis.png`

### 已根据 boros.long.account.csv 文件计算各项策略绩效指标，并修正了计算逻辑。

**重跑指引：**
```
数据文件：samples/strategy-example/result/boros.long.account.csv
数据范围：2025-09-10 至 2025-12-25（106天，154078条数据）

运行命令：
/Users/florije/PycharmProjects/demeter/venv/bin/python \
  samples/strategy-example/71_5_analyze_boros_long.py

输出目录：直接打印到控制台
```

**修正后的绩效指标（基于持仓周期/round-trip）：**

| 指标 | 值 | 说明 |
|------|------|------|
| **1. Cumulative Return** | -0.3517% | 真实事件 |
| **2. Annualized Return** | -1.2057% | 真实事件 |
| **3. Return on Posted Margin** | -2.3845% | 时间加权 |
| **4. Return on Total Capital** | -3.6060% | 基于 notional |
| **5. Max Drawdown** | -0.7796% | 真实事件 |
| **6. Volatility (年化)** | 1.3851% | 日频 std×√365 |
| **7. Trade Count** | 53 | proxy: 仓位变化 |
| **8. Rebalance Count** | 53 | proxy: 比例>5% |
| **9. Avg Holding Minutes** | **5565.11** | 基于27个仓位的真实持仓时间 |
| **10. Win Rate** | **85.19%** | 基于持仓周期（27个中23个盈利） |
| **11. Profit Factor** | **0.2878** | 基于持仓周期盈亏 |
| **# of Positions** | 27 | 实际持仓周期数 |

**关键修正说明：**
- **平均持仓时间**：现在基于每个仓位的开仓到平仓时间戳计算，而非采样频率
- **胜率/盈利因子**：现在基于每个持仓周期（round-trip）的盈亏计算，而非日频收益
- **波动率**：先重采样到日频再用 √365 年化

**分析脚本：** [`samples/strategy-example/71_5_analyze_boros_long.py`](samples/strategy-example/71_5_analyze_boros_long.py:1)