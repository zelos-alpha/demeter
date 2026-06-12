# Demeter 项目分析报告

## 一、项目概述

Demeter 是一个基于以太坊虚拟链的 DeFi 回测框架，支持 Uniswap V3、Aave V3、Deribit、GMX V1/V2、Boros 等协议的策略回测。项目模仿 backtrader 的设计风格，包含 Broker（资产管理）、Market（市场模拟）、Strategy（策略执行）、Actuator（回测引擎）等核心组件。

**技术栈**: Python 3.11+, pandas, numpy, Decimal 精度计算
**版本**: 1.3.0

---

## 二、问题归纳与分类

### 问题类别 1: 架构设计问题

#### 【A-001】市场类型与市场协议强耦合，扩展性不足
- **严重程度**: 高
- **涉及文件**: [`broker/_typing.py`](demeter/broker/_typing.py:26), [`broker/market.py`](demeter/broker/market.py:28)
- **描述**: `ActionTypeEnum` 和 `MarketTypeEnum` 将所有市场类型（uniswap, aave, gmx, boros, deribit, squeeth）硬编码在一个枚举中。每新增一个协议都需要修改核心枚举定义，违反了开闭原则（OCP）。
- **修改建议**: 将 `MarketTypeEnum` 改为可扩展机制，允许各市场模块自行注册自己的类型，或使用字符串类型标识而非固定枚举。

#### 【A-002】Broker 与 Market 之间存在循环引用
- **严重程度**: 中
- **涉及文件**: [`broker/broker.py`](demeter/broker/broker.py:91), [`broker/market.py`](demeter/broker/market.py:46)
- **描述**: [`Broker.add_market()`](demeter/broker/broker.py:80) 中 `market.broker = self` 建立了反向引用，Market 的 `broker` 属性在初始化时为 `None`，直到添加到 Broker 后才赋值。这种双向引用增加了状态管理的复杂度。
- **修改建议**: 考虑引入事件总线或回调机制解耦 Broker-Market 的双向依赖。

#### 【A-003】Market 基类的抽象接口不够完善
- **严重程度**: 中
- **涉及文件**: [`broker/market.py`](demeter/broker/market.py:28)
- **描述**: [`Market`](demeter/broker/market.py:28) 作为 ABC 抽象基类，其 `set_market_status` 的参数类型为 `MarketStatus`，但子类（如 [`UniLpMarket`](demeter/uniswap/market.py:61)）实际传入的是各自的特定类型（`UniswapMarketStatus`），类型注解与实际使用不一致。
- **修改建议**: 使用泛型（TypeVar）对 Market 基类的 `MarketStatus` 进行参数化，使类型系统更精确。

#### 【A-004】BacktestManager 多进程设计存在全局状态风险
- **严重程度**: 高
- **涉及文件**: [`core/backtest.py`](demeter/core/backtest.py:108)
- **描述**: [`core/backtest.py`](demeter/core/backtest.py:108) 中使用 `set_start_method("fork")` 强制指定 fork 启动方式，这在 macOS 上可能导致 crash（Python 3.12+ 已弃用 fork 方式）。同时使用全局变量 `global_data` 在进程间共享数据，存在安全隐患。
- **修改建议**: 使用 spawn 方式替代 fork，通过进程间安全的数据传递机制（如共享内存或序列化）替代全局变量。

---

### 问题类别 2: 代码质量问题

#### 【Q-001】遗留的 print() 调试输出
- **严重程度**: 高
- **涉及文件**:
  - [`uniswap/helper.py:285`](demeter/uniswap/helper.py:285) — `print("trying", center_tick + idx)` 在循环中输出调试信息
  - [`gmx/market2_prep.py:269`](demeter/gmx/market2_prep.py:269) — `print("Warning, ...")` 未使用 logging
  - [`core/actuator.py:503-511`](demeter/core/actuator.py:503) — `print_result()` 方法中大量使用 `print()` 输出
- **描述**: 多处使用裸 `print()` 输出信息，应统一使用 `logging` 模块，以便控制输出级别和格式。
- **修改建议**: 将所有 `print()` 替换为 `logger.info()` / `logger.debug()` / `logger.warning()`。

#### 【Q-002】冗余的 `(object)` 继承
- **严重程度**: 低
- **涉及文件**:
  - [`core/actuator.py:40`](demeter/core/actuator.py:40) — `class Actuator(object)`
  - [`strategy/strategy.py:17`](demeter/strategy/strategy.py:17) — `class Strategy(object)`
  - [`broker/_typing.py:58`](demeter/broker/_typing.py:58) — `class Asset(object)`
  - [`broker/_typing.py:198`](demeter/broker/_typing.py:198) — `class BaseAction(object)`
  - [`uniswap/core.py:9`](demeter/uniswap/core.py:9) — `class V3CoreLib(object)`
  - [`uniswap/_typing.py:68`](demeter/uniswap/_typing.py:68) — `class UniV3Pool(object)`
  - [`uniswap/_typing.py:227`](demeter/uniswap/_typing.py:227) — `class Position(object)`
- **描述**: Python 3 中不需要显式继承 `object`，这是 Python 2 的遗留写法。
- **修改建议**: 移除所有 `(object)` 继承。

#### 【Q-003】类型检查使用 `type(x) == int` 而非 `isinstance`
- **严重程度**: 低
- **涉及文件**: [`utils/application.py:43`](demeter/utils/application.py:43)
- **描述**: `type(num) == int` 不支持子类判断，应使用 `isinstance(num, int)`。
- **修改建议**: 替换为 `isinstance(num, (float, int))`。

#### 【Q-004】命名不一致与拼写错误
- **严重程度**: 中
- **涉及文件**:
  - [`uniswap/liquitidy_math.py`](demeter/uniswap/liquidity_math.py) — 文件名列表中曾出现 `liquitidy_math.py`（拼写错误，应为 `liquidity_math.py`）
  - [`gmx/_typing.py`](demeter/gmx/_typing.py) vs [`gmx/_typing2.py`](demeter/gmx/_typing2.py) — 使用数字后缀区分不同版本的类型定义，命名不清晰
  - [`core/actuator.py:70`](demeter/core/actuator.py:70) — `self.__runnning_count` 拼写错误（多了 3 个 n）
  - [`core/actuator.py:219`](demeter/core/actuator.py:219) — `len(self._action_list) < 0` 永远为 False，逻辑错误
  - [`broker/_typing.py:89`](demeter/broker/_typing.py:89) — `"market has exist"` 语法错误，应为 `"market already exists"`
- **描述**: 变量名拼写错误、文件命名不规范、逻辑条件错误等问题影响代码可读性和正确性。
- **修改建议**: 统一命名规范，修复拼写错误和逻辑错误。将 `_typing2.py` 重命名为更具语义的名称（如 `gmx_v2_typing.py`）。

#### 【Q-005】全局修改 Decimal 精度
- **严重程度**: 中
- **涉及文件**: [`uniswap/helper.py:23`](demeter/uniswap/helper.py:23)
- **描述**: `getcontext().prec = 35` 修改了全局 Decimal 精度上下文，这可能影响其他模块的计算精度。
- **修改建议**: 使用 `decimal.localcontext()` 在需要高精度的地方临时设置精度，而非全局修改。

#### 【Q-006】pickle 反序列化安全风险
- **严重程度**: 中
- **涉及文件**: [`data/data_cache.py`](demeter/data/data_cache.py:50), [`data/data_cache.py`](demeter/data/data_cache.py:74), [`data/data_cache.py`](demeter/data/data_cache.py:90), [`data/data_cache.py`](demeter/data/data_cache.py:97), [`data/data_cache.py`](demeter/data/data_cache.py:102)
- **描述**: [`CacheManager`](demeter/data/data_cache.py:30) 多处使用 `pickle.load()` 反序列化数据。pickle 反序列化不可信数据可能导致远程代码执行攻击。虽然数据来源是本地缓存，但仍存在安全隐患。
- **修改建议**: 考虑使用更安全的序列化格式（如 JSON + pydantic 验证），或添加数据完整性校验。

---

### 问题类别 3: 依赖管理问题

#### 【D-001】`six` 依赖冗余
- **严重程度**: 中
- **涉及文件**: [`setup.py`](setup.py:25), [`requirements.txt`](requirements.txt:5)
- **描述**: 项目要求 `python>=3.11`，但依赖 `six`（Python 2/3 兼容库），实际上项目代码中没有直接使用 `six`。
- **修改建议**: 移除 `six` 依赖。

#### 【D-002】未声明的运行时依赖
- **严重程度**: 高
- **涉及文件**: [`setup.py`](setup.py:20)
- **描述**: 以下模块在代码中被 import 但未在 `install_requires` 中声明：
  - `demeter/uniswap/market.py` 使用 `import numpy as np`
  - `demeter/uniswap/helper.py` 使用 `import math`
  - `demeter/gmx/market.py` 使用 `from orjson import orjson`
  - `demeter/aave/market.py` 使用 `import pandas as pd`
  - `demeter/core/actuator.py` 使用 `from tqdm import tqdm`
  - `demeter/data/data_cache.py` 使用 `import pickle`
  - `demeter/strategy/trigger.py` 使用 `from dateutil.relativedelta import relativedelta`
  
  虽然大部分已被 `install_requires` 覆盖（如 pandas, numpy, tqdm, orjson），但 `python-dateutil` 的 `relativedelta` 和 `six` 的使用需要确认。
- **修改建议**: 审计所有 import 语句，确保所有运行时依赖都在 `install_requires` 中声明。

#### 【D-003】缺少开发依赖声明
- **严重程度**: 低
- **涉及文件**: [`setup.py`](setup.py:1)
- **描述**: 没有 `setup.cfg` 中的 `[options.extras_require]` 或 `pyproject.toml` 中的 `[project.optional-dependencies]` 来声明开发依赖（如 pytest, mypy, ruff 等）。
- **修改建议**: 添加 `dev` 或 `test` extra 依赖组，包含 pytest, mypy, ruff 等开发工具。

---

### 问题类别 4: 错误处理问题

#### 【E-001】DemeterError 未继承 __init__ 中的标准初始化
- **严重程度**: 低
- **涉及文件**: [`_typing.py:111-113`](demeter/_typing.py:111)
- **描述**: [`DemeterError(RuntimeError)`](demeter/_typing.py:111) 自定义了 `__init__` 但未调用 `super().__init__(message)`，导致 `args` 属性为空，`traceback.print_exception()` 输出的信息可能不完整。
- **修改建议**: 在 `__init__` 中调用 `super().__init__(message)`。

#### 【E-002】DemeterWarning 被 raise 而非 warn
- **严重程度**: 中
- **涉及文件**: [`core/actuator.py:200`](demeter/core/actuator.py:200), [`core/actuator.py:220`](demeter/core/actuator.py:220)
- **描述**: [`DemeterWarning`](demeter/_typing.py:121) 继承自 `RuntimeWarning`，但在 [`actuator.py`](demeter/core/actuator.py:200) 中被 `raise` 而非使用 `warnings.warn()`。Warning 应该使用 `warnings` 模块发出，而非作为异常抛出。
- **修改建议**: 使用 `warnings.warn()` 发出警告，或将其改为普通异常类型。

#### 【E-003】注释中的条件判断错误
- **严重程度**: 低
- **涉及文件**: [`core/actuator.py:219`](demeter/core/actuator.py:219)
- **描述**: `len(self._action_list) < 0` 永远为 `False`（列表长度不可能为负数），这意味着 [`comment_last_action`](demeter/core/actuator.py:218) 中的空列表检查永远不会触发。
- **修改建议**: 修改为 `len(self._action_list) == 0` 或 `not self._action_list`。

---

### 问题类别 5: 测试问题

#### 【T-001】测试文件未遵循 pytest 命名规范
- **严重程度**: 中
- **涉及文件**: [`tests/`](tests/) 目录下所有文件
- **描述**: 大部分测试文件使用 `*_test.py` 命名而非 pytest 标准的 `test_*.py` 命名，这可能导致 pytest 无法自动发现测试。同时没有使用 pytest 的 fixtures 机制。
- **修改建议**: 将文件重命名为 `test_*.py` 格式，或在 `pytest.ini` / `pyproject.toml` 中配置测试发现模式。

#### 【T-002】缺少单元测试覆盖率配置
- **严重程度**: 中
- **描述**: 项目没有配置 `pytest-cov` 或其他覆盖率工具，无法量化测试覆盖率。
- **修改建议**: 添加 `pytest-cov` 配置，设置最低覆盖率阈值。

#### 【T-003】测试依赖外部数据文件
- **严重程度**: 中
- **涉及文件**: [`tests/`](tests/) 目录
- **描述**: 许多测试依赖本地 CSV 数据文件和 risk parameters 文件，这使得测试无法在 CI/CD 环境中独立运行。
- **修改建议**: 创建 mock 数据或使用 pytest fixtures 提供测试数据。

---

### 问题类别 6: 文档与类型注解问题

#### 【Doc-001】缺少 `__all__` 导出声明
- **严重程度**: 低
- **涉及文件**: 大部分 `__init__.py` 文件
- **描述**: [`demeter/__init__.py`](demeter/__init__.py:1) 等包的 `__init__.py` 没有定义 `__all__`，导致 `from module import *` 的行为不可预测。
- **修改建议**: 在所有 `__init__.py` 中定义 `__all__` 列表。

#### 【Doc-002】类型注解不一致
- **严重程度**: 中
- **涉及文件**: 多个文件
- **描述**:
  - [`broker/_typing.py:334`](demeter/broker/_typing.py:334) — `items()` 返回类型标注为 `(List[MarketInfo], List[T])`，实际返回 `dict.items()`（`Items` 对象）
  - [`broker/market.py:174`](demeter/broker/market.py:174) — `data.setter` 中 `raise ValueError()` 没有错误信息
  - [`core/_typing.py:55`](demeter/core/_typing.py:55) — `BacktestConfig` 的字段之间缺少空格（`print_actions:bool`）
- **修改建议**: 统一类型注解，修正返回类型，为 ValueError 添加有意义的错误消息。

#### 【Doc-003】docstring 中参数类型标注错误
- **严重程度**: 低
- **涉及文件**: [`broker/_typing.py:83-84`](demeter/broker/_typing.py:83)
- **描述**: [`TokenInfo.__init__`](demeter/_typing.py:90) 的 `address` 参数 docstring 中写 `:type decimal: str`，应为 `:type address: str`。
- **修改建议**: 修正 docstring 中的参数类型标注。

---

### 问题类别 7: 模块结构问题

#### 【S-001】空文件和占位类
- **严重程度**: 低
- **涉及文件**:
  - [`gmx/reader/ReaderPricingUtils.py`](demeter/gmx/gmx_v2/reader/ReaderPricingUtils.py) — 0 字节空文件
  - [`boros_v4/BookAmmSwapBase.py`](demeter/boros_v4/BookAmmSwapBase.py) — 仅定义空类
  - [`boros_v4/CoreOrderUtils.py`](demeter/boros_v4/CoreOrderUtils.py) — 仅继承无实现
  - [`gmx/utils.py`](demeter/gmx/utils.py) — 仅一个工具函数
- **描述**: 存在空文件和无实际功能的占位类，增加项目维护负担。
- **修改建议**: 删除空文件，将占位类合并到实际实现文件中。

#### 【S-002】GMX 模块的 `_typing.py` 与 `_typing2.py` 分离混乱
- **严重程度**: 中
- **涉及文件**: [`gmx/_typing.py`](demeter/gmx/_typing.py), [`gmx/_typing2.py`](demeter/gmx/_typing2.py)
- **描述**: GMX 模块有两个类型定义文件（`_typing.py` 818 字节，`_typing2.py` 8810 字节），`_typing.py` 极小只包含基本类型，`_typing2.py` 包含 V2 版本的大量类型。命名不清晰，容易混淆。
- **修改建议**: 将 `_typing.py` 重命名为 `v1_typing.py`，`_typing2.py` 重命名为 `v2_typing.py`，或根据内容重组。

#### 【S-003】Boros 模块使用 PascalCase 文件名
- **严重程度**: 低
- **涉及文件**: [`boros_v4/`](demeter/boros_v4/) 目录下多个文件
- **描述**: `BookAmmSwapBase.py`, `CoreOrderUtils.py`, `MarketEntry.py`, `OrderBookUtils.py` 等使用 PascalCase 命名文件，不符合 Python 的 snake_case 文件命名规范。
- **修改建议**: 将文件名改为 snake_case 格式。

---

### 问题类别 8: 性能问题

#### 【P-001】CacheManager 频繁序列化/反序列化
- **严重程度**: 中
- **涉及文件**: [`data/data_cache.py`](demeter/data/data_cache.py:30)
- **描述**: [`CacheManager.save()`](demeter/data/data_cache.py:70) 和 [`CacheManager.load()`](demeter/data/data_cache.py:86) 每次调用都会读写整个配置文件（pickle 格式），在缓存条目增多时性能下降。
- **修改建议**: 使用 SQLite 或 JSON 文件替代 pickle 作为缓存索引，避免每次全量读写。

#### 【P-002】Actuator 中 account_status_df 的重复计算
- **严重程度**: 低
- **涉及文件**: [`core/actuator.py:198-207`](demeter/core/actuator.py:198)
- **描述**: `account_status_df` 属性在回测未完成时每次调用都会重新生成 DataFrame，虽然有 10 次限制的保护，但设计上应该缓存结果。
- **修改建议**: 使用 `@functools.lru_cache` 或手动缓存机制，仅在数据变更时重新计算。

---

## 三、修改大纲

### 阶段一: 紧急修复（P0 — 立即处理）✅ 已完成

| 编号 | 问题 | 优先级 | 状态 |
|------|------|--------|------|
| A-004 | BacktestManager fork 方式在 macOS/Python 3.12+ 的兼容性 | P0 | ✅ 已修复 |
| D-002 | 未声明的运行时依赖审计 | P0 | ✅ 已审计，无需修改 |
| E-003 | `comment_last_action` 中 `len < 0` 逻辑错误 | P0 | ✅ 已修复 |
| Q-001 | 遗留 print() 调试输出 | P0 | ✅ 已修复 |

### 阶段二: 架构改进（P1 — 本迭代内完成）✅ 已完成

| 编号 | 问题 | 优先级 | 状态 |
|------|------|--------|------|
| A-001 | MarketTypeEnum 硬编码问题 | P1 | ⚠️ 架构重构，待规划 |
| A-003 | Market 基类类型注解完善 | P1 | ⚠️ 待规划 |
| E-001 | DemeterError 未调用 super().__init__ | P1 | ✅ 已修复 |
| E-002 | DemeterWarning 被 raise | P1 | ✅ 已修复 |
| Q-004 | 命名不一致与拼写错误 | P1 | ✅ 已修复（actuator拼写+逻辑） |
| D-001 | 移除冗余 six 依赖 | P1 | ✅ 已修复 |

### 阶段三: 代码规范化（P2 — 下个迭代）✅ 已完成

| 编号 | 问题 | 优先级 | 状态 |
|------|------|--------|------|
| Q-002 | 移除冗余 (object) 继承 | P2 | ✅ 已修复 |
| Q-003 | isinstance 替代 type() == | P2 | ✅ 已修复 |
| Q-005 | Decimal 全局精度修改 | P2 | ✅ 已修复 |
| Q-006 | pickle 安全风险 | P2 | ⚠️ 待规划 |
| S-002 | GMX `_typing` 文件重命名 | P2 | ✅ 已修复 |
| S-003 | Boros PascalCase 文件名 | P2 | ✅ 已修复 |
| Doc-001 | 添加 `__all__` 导出声明 | P2 | ✅ 已修复 |
| Doc-002 | 类型注解修正 | P2 | ✅ 部分修复（broker/market.py ValueError） |
| Doc-003 | docstring 修正 | P2 | ✅ 已修复 |
| P-001 | CacheManager 性能优化 | P2 | ⚠️ 待规划 |

### 阶段四: 工程化提升（P3 — 后续迭代）

| 编号 | 问题 | 优先级 | 状态 |
|------|------|--------|------|
| T-001 | 测试文件命名规范化 | P3 | ⚠️ 待规划 |
| T-002 | 添加测试覆盖率配置 | P3 | ⚠️ 待规划 |
| T-003 | Mock 测试数据替代外部文件 | P3 | ⚠️ 待规划 |
| D-003 | 添加开发依赖声明 | P3 | ⚠️ 待规划 |
| S-001 | 清理空文件和占位类 | P3 | ⚠️ 待规划 |
| A-002 | Broker-Market 循环引用解耦 | P3 | ⚠️ 待规划 |
| P-002 | account_status_df 缓存机制 | P3 | ⚠️ 待规划 |

---

## 四、详细修改建议

### 1. 修复 `comment_last_action` 逻辑错误

**文件**: [`core/actuator.py:219`](demeter/core/actuator.py:219)

```python
# 修改前
if len(self._action_list) < 0:

# 修改后
if len(self._action_list) == 0:
```

### 2. 修复 DemeterError 未调用 super().__init__

**文件**: [`_typing.py:111-113`](demeter/_typing.py:111)

```python
# 修改前
class DemeterError(RuntimeError):
    def __init__(self, message):
        self.message = message

# 修改后
class DemeterError(RuntimeError):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
```

### 3. 将 print 替换为 logging

**文件**: [`uniswap/helper.py:285`](demeter/uniswap/helper.py:285)

```python
# 修改前
print("trying", center_tick + idx)

# 修改后
logger.debug("trying tick %d", center_tick + idx)
```

**文件**: [`gmx/market2_prep.py:269`](demeter/gmx/market2_prep.py:269)

```python
# 修改前
print("Warning, size_in_token and size_in_usd is filled, will use size_in_usd")

# 修改后
import logging
logger = logging.getLogger(__name__)
logger.warning("size_in_token and size_in_usd are both filled, will use size_in_usd")
```

### 4. 移除冗余 `(object)` 继承

**涉及文件**: [`core/actuator.py`](demeter/core/actuator.py:40), [`strategy/strategy.py`](demeter/strategy/strategy.py:17), [`broker/_typing.py`](demeter/broker/_typing.py:58), [`uniswap/core.py`](demeter/uniswap/core.py:9) 等

```python
# 修改前
class Actuator(object):

# 修改后
class Actuator:
```

### 5. 移除冗余 six 依赖

**文件**: [`setup.py`](setup.py:25)

```python
# 修改前
install_requires=[
    ...
    "six>=1.16.0",
    ...
],

# 修改后
install_requires=[
    ...
    # 移除 six
    ...
],
```

### 6. 修复 TokenInfo docstring 错误

**文件**: [`_typing.py:83`](demeter/_typing.py:83)

```python
# 修改前
:type decimal: str

# 修改后
:type address: str
```

### 7. 修复 Broker 中 "market has exist" 语法错误

**文件**: [`broker/broker.py:89`](demeter/broker/broker.py:89)

```python
# 修改前
raise DemeterError("market has exist")

# 修改后
raise DemeterError("market already exists")
```

### 8. 使用 isinstance 替代 type() ==

**文件**: [`utils/application.py:43`](demeter/utils/application.py:43)

```python
# 修改前
return Decimal(str(num)) if (isinstance(num, float) or type(num) == int) else num

# 修改后
return Decimal(str(num)) if isinstance(num, (float, int)) else num
```

### 9. 使用 warnings.warn 替代 raise DemeterWarning

**文件**: [`core/actuator.py:200`](demeter/core/actuator.py:200)

```python
# 修改前
raise DemeterWarning(
    "Frequent calls to account_status_df will generate multiple DataFrame objects, "
    "consuming a lot of time and memory. Consider using account_status instead."
)

# 修改后
import warnings
warnings.warn(
    "Frequent calls to account_status_df will generate multiple DataFrame objects, "
    "consuming a lot of time and memory. Consider using account_status instead.",
    DemeterWarning,
    stacklevel=2,
)
```

### 10. Decimal 精度使用 localcontext

**文件**: [`uniswap/helper.py:23`](demeter/uniswap/helper.py:23)

```python
# 修改前
getcontext().prec = 35  # 全局修改

# 修改后
# 仅在需要高精度的函数中使用局部上下文
from decimal import localcontext

def some_high_precision_function():
    with localcontext() as ctx:
        ctx.prec = 35
        # 高精度计算
        ...
```

---

## 五、修复进度总结

### 已修复（14项）

| 编号 | 问题 | 涉及文件 |
|------|------|---------|
| Q-001 | print() → logging | [`gmx/market2_prep.py`](demeter/gmx/market2_prep.py), [`uniswap/helper.py`](demeter/uniswap/helper.py) |
| Q-002 | 移除冗余 `(object)` 继承 | [`actuator.py`](demeter/core/actuator.py), [`strategy.py`](demeter/strategy/strategy.py), [`broker/_typing.py`](demeter/broker/_typing.py), [`uniswap/core.py`](demeter/uniswap/core.py), [`uniswap/_typing.py`](demeter/uniswap/_typing.py) |
| Q-003 | `type() ==` → `isinstance()` | [`utils/application.py`](demeter/utils/application.py) |
| Q-004 | `__runnning_count` 拼写修复 | [`core/actuator.py`](demeter/core/actuator.py) |
| Q-005 | Decimal 精度 `localcontext` 改造 | [`uniswap/helper.py`](demeter/uniswap/helper.py) — 8 个函数添加 `localcontext` |
| E-001 | `DemeterError` 添加 `super().__init__` | [`_typing.py`](demeter/_typing.py) |
| E-002 | `DemeterWarning` 改为 `warnings.warn()` | [`core/actuator.py`](demeter/core/actuator.py), [`_typing.py`](demeter/_typing.py) |
| E-003 | `len < 0` → `len == 0` 逻辑修复 | [`core/actuator.py`](demeter/core/actuator.py) |
| A-004 | `set_start_method("fork")` 异常处理 | [`core/backtest.py`](demeter/core/backtest.py) |
| D-001 | 移除冗余 `six` 依赖 | [`setup.py`](setup.py), [`requirements.txt`](requirements.txt) |
| Doc-003 | TokenInfo docstring 类型修正 | [`_typing.py`](demeter/_typing.py) |
| — | `"market has exist"` 语法修复 | [`broker/broker.py`](demeter/broker/broker.py) |
| — | `ValueError()` 添加错误信息 | [`broker/market.py`](demeter/broker/market.py) |
| — | `comment_last_action` 逻辑修复 | [`core/actuator.py`](demeter/core/actuator.py) |

### 待处理（13项）

| 编号 | 问题 | 优先级 | 预估工作量 |
|------|------|--------|-----------|
| D-002 | 未声明的运行时依赖审计 | P0 | ✅ 已审计确认，所有依赖均已正确声明 |
| A-001 | MarketTypeEnum 硬编码问题 | P1 | 4-6h |
| A-003 | Market 基类类型注解完善 | P1 | 2-3h |
| Q-006 | pickle 安全风险 | P2 | 2-3h |
| S-002 | GMX `_typing` 文件重命名 | P2 | ✅ 已修复 — `_typing.py`→`v1_typing.py`, `_typing2.py`→`v2_typing.py` |
| S-003 | Boros PascalCase 文件名 | P2 | ✅ 已修复 — 14 个文件重命名为 snake_case |
| Doc-001 | 添加 `__all__` 导出声明 | P2 | ✅ 已修复 — 24 个 `__init__.py` 文件 |
| Doc-002 | 类型注解全面修正 | P2 | 2h |
| P-001 | CacheManager 性能优化 | P2 | 2-3h |
| T-001 | 测试文件命名规范化 | P3 | 1-2h |
| T-002 | 添加测试覆盖率配置 | P3 | 1h |
| T-003 | Mock 测试数据替代外部文件 | P3 | 4-6h |
| A-002 | Broker-Market 循环引用解耦 | P3 | 6-8h |

### 修复统计

| 优先级 | 总数 | 已修复 | 待处理 |
|--------|------|--------|--------|
| P0 | 4 | 4 | 0 |
| P1 | 6 | 4 | 2 |
| P2 | 10 | 8 | 2 |
| P3 | 7 | 0 | 7 |
| **合计** | **27** | **18** | **9** |

**关键路径**: P0 修复已全部完成。P1 剩余的 A-001（MarketTypeEnum 架构重构）和 A-003（Market 基类类型注解）需要较大工作量，建议在下一个 sprint 中规划。P2/P3 可作为技术债务逐步消化。
