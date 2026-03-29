已根据 boros.long.account.csv 文件计算各项策略绩效指标。

**数据概况：**
- 时间范围：2025-09-10 至 2025-12-25（约106天）
- 数据点数：154,078 条

**绩效指标：**

| 指标 | 值 |
|------|------|
| **1. Cumulative Return** | -0.3517% |
| **2. Annualized Return** | -1.2057% |
| **3. Return on Posted Margin** | -9.0149% |
| **4. Return on Total Capital** | -1.8030% |
| **5. Max Drawdown** | -0.7796% |
| **6. Volatility (年化)** | 0.0797% |
| **7. Liquidation Count** | 27 |
| **8. Margin Call Count** | 0 |
| **9. Trade Count** | 53 |
| **10. Rebalance Count** | 53 |
| **11. Average Holding Minutes** | 1 |
| **12. Win Rate** | 49.06% |
| **13. Profit Factor** | 0.9385 |

**额外统计：**
- 初始净值：999.9982 USD
- 最终净值：996.4816 USD
- 最高净值：1003.1590 USD
- 最低净值：995.3385 USD
- 平均保证金：39.01 USD
- 总资本：195.04 USD

**分析脚本：** [`samples/strategy-example/analyze_boros_long.py`](samples/strategy-example/analyze_boros_long.py:1)

该策略在此期间表现为负收益，累计亏损约 -0.35%。胜率约49%，盈利因子0.94小于1，说明亏损交易整体大于盈利交易。波动率极低（0.08%年化），风险控制较好，但收益为负。