# force_stored 数据修复模块问题分析与改进方案

> **文档版本**：V1.0
> **创建日期**：2026-03-21
> **文档目的**：第一性原理审视 force_stored 数据修复模块的完整设计，识别问题并提出系统性改进方案

---

## 1. 模块全景调研

### 1.1 相关文件清单

| 文件路径 | 功能说明 |
|---------|---------|
| `task1_collector.py` | 主采集入口，包含 force_stored 校验与修复逻辑 |
| `core/processor/data_validator.py` | 数据完整性校验器（5W1H、评分、领域等字段校验） |
| `core/processor/combined_processor.py` | AI 合并处理器（翻译+摘要+5W1H+评分，单次 LLM 调用） |
| `core/storage/database.py` | 数据库访问层（NewsDatabase、NewsData 数据结构） |
| `scripts/tools/repair_history_data.py` | 历史数据修复脚本（修复 NULL 字段标记为 force_stored） |
| `scripts/tools/fix_history_data.py` | 历史数据修复脚本（校验 NULL 状态数据） |
| `docs/WORKFLOW_V3.md` | 工作流详细说明文档 |
| `README.md` | 项目说明文档 |

### 1.2 数据状态流转设计（来自 README）

```
AI处理 → 校验
   ├─ valid/remediated → passed → 向量化 → 热度评分 → 存储
   └─ 其他 → force_stored (repair_count=0) → 向量化 → 存储

修复循环（Task1 阶段11）
   force_stored 数据:
   ├─ repair_count >= 1 → abandoned（放弃修复）
   ├─ 修复成功 → passed
   └─ 修复失败 → force_stored (repair_count += 1)

最终状态:
   passed     → 正常参与 Task2 报告生成
   force_stored → 等待下次修复
   abandoned  → 放弃修复，保留数据但不参与处理
```

---

## 2. 第一性原理分析

### 2.1 设计目的推导

从代码和文档分析，force_stored 机制的设计目的为：

**核心目的**：在保证数据完整性的前提下，最大化有效数据的入库率。

**子目标**：
1. **容错性**：AI 处理可能因网络波动、模型响应异常等原因失败，需要一种机制保存不完整但有价值的数据
2. **异步修复**：将校验失败的数据先入库，后续通过重试机制尝试修复，而不是直接丢弃
3. **资源保护**：通过 repair_count 限制单条数据的修复尝试次数，防止无限重试消耗资源
4. **数据分级**：
   - `passed`：完全合格，直接参与报告生成
   - `force_stored`：暂时不合格，等待后续修复或下次采集周期再处理
   - `abandoned`：永久不合格，保留但不使用

### 2.2 数据流分析

```
[RSS信源]
    ↓
[RSSCollector 采集]
    ↓
[FieldNormalizer 字段规范化]
    ↓
[CombinedProcessor AI处理] → 返回 combined_result
    ↓
[DataValidator 校验] → validate_combined_result()
    ├─ status='valid' → combined_processing_status='passed'
    ├─ status='remediated' → combined_processing_status='passed'
    ├─ status='default_filled' → combined_processing_status='passed'
    └─ 其他 → combined_processing_status='force_stored', repair_count=0
    ↓
[_store_batch_to_database] → NewsData 对象
    ↓
[NewsDatabase.insert_news_batch] → 写入 SQLite
    ↓
[阶段11 _reprocess_pending_news]
    ↓
db.get_news_by_status('force_stored') → 获取待修复数据
    ↓
[CombinedProcessor 再次处理]
    ↓
[DataValidator 再次校验]
    ├─ 通过 → combined_processing_status='passed'
    └─ 不通过 → combined_processing_status='force_stored', repair_count+=1
```

---

## 3. 存在的问题清单

### 3.1 问题严重度分类

| 严重度 | 问题编号 | 问题描述 | 影响范围 |
|-------|---------|---------|---------|
| 🔴 严重 | P1 | `abandoned_count` 变量未初始化 | 程序运行时崩溃（UnboundLocalError） |
| 🔴 严重 | P2 | `repair_count` 字段在数据库中不存在 | 修复机制完全失效，数据无限循环 |
| 🔴 严重 | P3 | `repair_count` 字段在 NewsData 类中不存在 | 写入时字段被静默忽略 |
| 🟡 中等 | P4 | 重试逻辑只有 1 次机会 | 大部分 force_stored 数据被直接丢弃 |
| 🟡 中等 | P5 | 校验失败后的 AI 补救机制未启用 | 缺少中间层修复机会 |
| 🟡 中等 | P6 | `_fill_default_values` 评分标准不一致 | 与 CombinedProcessor 默认评分不匹配 |
| 🟢 低 | P7 | 历史修复脚本使用旧字段名 | score/score_timeliness 等已废弃的字段 |

### 3.2 详细问题分析

---

#### P1: `abandoned_count` 变量未初始化

**位置**：[task1_collector.py#L928-930](file:///c:\Users\matrix\Desktop\news_workflow\news_analyzer\task1_collector.py#L928-930)

**代码**：
```python
success_count = 0
fail_count = 0
still_pending = 0
# ❌ abandoned_count 未初始化！
```

**触发位置**：[task1_collector.py#L940](file:///c:\Users\matrix\Desktop\news_workflow\news_analyzer\task1_collector.py#L940)
```python
abandoned_count += 1  # UnboundLocalError
```

**运行结果**：程序崩溃，报错 `UnboundLocalError: local variable 'abandoned_count' referenced before assignment`

**触发条件**：当 force_stored 数据的 repair_count >= 1 时会触发（但由于 P2/P3，repair_count 永远无法 >= 1，所以此 Bug 目前不会被触发）

---

#### P2: `repair_count` 字段在数据库中不存在

**位置**：[database.py#L241-276](file:///c:\Users\matrix\Desktop\news_workflow\news_analyzer\core\storage\database.py#L241-276)（建表语句）

**问题**：数据库建表语句中 `news` 表没有 `repair_count` 列，但代码逻辑依赖此字段。

**数据库表实际字段**：
```
id, title, translated_title, link, source, source_name, pub_date, content, summary,
who, what, when_time, where_place, why, how,
domain, tags, keywords,
source_score, heat_score, influence_score, value_score, final_score,
extraction_method, raw_item_json, raw_news_id,
embedding, created_at, updated_at
```

**缺失字段**：`repair_count`, `combined_processing_status`, `validation_status`

**SQLite 行为**：INSERT 时如果字段不存在，该字段的值被静默忽略，不会报错。

---

#### P3: `repair_count` 字段在 NewsData 类中不存在

**位置**：[database.py#L30-61](file:///c:\Users\matrix\Desktop\news_workflow\news_analyzer\core\storage\database.py#L30-61)（NewsData 定义）

**代码**：
```python
@dataclass
class NewsData:
    news_id: str
    title: str
    # ... 其他字段 ...
    extraction_method: Optional[str] = None
    raw_item_json: Optional[str] = None
    raw_news_id: Optional[int] = None
    # ❌ repair_count 不存在
    # ❌ combined_processing_status 不存在
    # ❌ validation_status 不存在
```

**影响**：
1. `_store_batch_to_database` 中 `NewsData(..., combined_processing_status=..., repair_count=...)` 传入时，多余参数被 Python 数据类忽略（dataclass 只会接收定义的字段）
2. `_news_to_dict` 转换时，这些字段不会被包含在字典中
3. 最终 INSERT SQL 中这些字段为 NULL

---

#### P4: 重试逻辑只有 1 次机会

**位置**：[task1_collector.py#L937-942](file:///c:\Users\matrix\Desktop\news_workflow\news_analyzer\task1_collector.py#L937-L942)

**代码**：
```python
if current_repair_count >= 1:
    updates = {'combined_processing_status': 'abandoned'}
    self.db.update_news(news_id, updates)
    abandoned_count += 1
    logger.warning(f"修复次数超限，标记为abandoned: {news.get('title', '')[:30]}...")
    continue
```

**设计问题**：
- 条件是 `repair_count >= 1`，意味着 repair_count=0 时才会修复
- 修复后 repair_count 变为 1
- 下次（实际上是同一个批次内的下一次循环迭代）立即变为 abandoned
- 实际只有 **0 次真正修复机会**

**最终结果**：
- repair_count=0 的数据进入修复流程
- 修复失败，repair_count 变为 1（但由于 P2，写入后仍为 NULL）
- 下次循环（如果有）会看到 repair_count=0（因为读取返回 NULL，默认为 0）
- 数据陷入无限修复循环

---

#### P5: AI 补救机制未启用

**位置**：[data_validator.py#L47-58](file:///c:\Users\matrix\Desktop\news_workflow\news_analyzer\core\processor\data_validator.py#L47-58)

**代码**：
```python
if has_errors:
    remediation_result = self._attempt_ai_remediation(news, result, validation_results)
    if remediation_result:
        return {'status': 'remediated', 'results': validation_results, 'remediation': remediation_result}
    else:
        default_values = self._fill_default_values(result, validation_results)
        return {'status': 'default_filled', 'results': validation_results, 'default_values': default_values}
```

**问题**：
```python
def __init__(self, ai_provider: Optional[Callable] = None):
    self.ai_provider = ai_provider  # 默认为 None
```

**调用位置**：[task1_collector.py#L459](file:///c:\Users\matrix\Desktop\news_workflow\news_analyzer\task1_collector.py#L459)
```python
validation_result = self.data_validator.validate_combined_result(news, news.get('combined_result', {}))
```

**分析**：DataValidator 实例化时没有传入 ai_provider，所以 `_attempt_ai_remediation` 永远返回 None，失去了在首次校验失败时尝试 AI 自动补救的机会。

---

#### P6: `_fill_default_values` 评分标准不一致

**位置 1**：[task1_collector.py#L880-899](file:///c:\Users\matrix\Desktop\news_workflow\news_analyzer\task1_collector.py#L880-899)
```python
def _fill_default_values(self, news):
    if not news.get('influence_score'):
        news['influence_score'] = 50.0  # ❌ 范围 0-100
    if not news.get('source_score'):
        news['source_score'] = 50.0     # ❌ 范围 0-100
    if not news.get('value_score'):
        news['value_score'] = 50.0      # ❌ 范围 0-100
```

**位置 2**：[combined_processor.py#L140-144](file:///c:\Users\matrix\Desktop\news_workflow\news_analyzer\core\processor\combined_processor.py#L140-144)
```python
"scoring": {
    "influence_score": 0.5,  # ✅ 范围 0-1
    "value_score": 0.5       # ✅ 范围 0-1
}
```

**问题**：CombinedProcessor 返回的评分范围是 0-1，而 `_fill_default_values` 填充的是 0-100。造成 final_score 计算时量纲不一致。

---

#### P7: 历史修复脚本使用废弃字段名

**位置**：[repair_history_data.py#L38-41](file:///c:\Users\matrix\Desktop\news_workflow\news_analyzer\scripts\tools\repair_history_data.py#L38-41)
```python
score_fields = ['score', 'score_timeliness', 'score_importance', 'score_credibility', 'score_impact']
```

**问题**：这些是旧版字段名，已被 `final_score`、`heat_score`、`influence_score`、`value_score`、`source_score` 替代。

---

## 4. 问题根因分析

### 4.1 核心根因：Schema 与代码不同步

**Schema（数据库结构）**：
- `news` 表缺少 `repair_count`、`combined_processing_status`、`validation_status` 字段
- `NewsData` 类缺少这些字段的定义

**代码（业务逻辑）**：
- task1_collector.py 依赖这些字段进行状态流转
- INSERT_NEWS_SQL 包含这些字段
- 但由于 NewsData 没有定义，_news_to_dict 不会包含这些字段

**结果**：
1. 代码可以运行（SQLite 静默忽略未知字段）
2. 但业务逻辑完全失效（repair_count 永远为 NULL/0，状态永远不变）

### 4.2 次级根因：缺乏端到端测试

当前测试套件可能没有覆盖：
- force_stored 状态的完整生命周期
- 数据库 schema 与代码的集成测试
- repair_count 字段的读写验证

---

## 5. 改进方案设计

### 5.1 方案目标

1. **修复现有 Bug**：让 force_stored 机制能正常工作
2. **增强鲁棒性**：提高数据修复的成功率
3. **提升可观测性**：让问题更容易追踪和诊断
4. **保持向后兼容**：不破坏已有数据

### 5.2 方案一：最小修复（保守方案）

**目标**：只修复 Bug，不改变设计逻辑

#### 修复 P1: 初始化 abandoned_count
```python
# task1_collector.py L928-930
success_count = 0
fail_count = 0
still_pending = 0
abandoned_count = 0  # 添加此行
```

#### 修复 P2/P3: 添加数据库字段

在 `database.py` 的 `_init_database` 方法中，ALTER TABLE 添加缺失字段：

```python
# 检查并添加缺失字段
def _ensure_columns(self):
    with self.get_connection() as conn:
        cursor = conn.cursor()
        # 获取当前表结构
        cursor.execute("PRAGMA table_info(news)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # 需要添加的字段
        required_columns = {
            'repair_count': 'INTEGER DEFAULT 0',
            'combined_processing_status': 'TEXT',
            'validation_status': 'TEXT',
        }

        for col_name, col_type in required_columns.items():
            if col_name not in existing_columns:
                cursor.execute(f"ALTER TABLE news ADD COLUMN {col_name} {col_type}")
                logger.info(f"添加缺失字段: {col_name}")

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_repair_count ON news(repair_count)')
```

#### 修复 P3: 更新 NewsData 类

```python
@dataclass
class NewsData:
    # ... 现有字段 ...
    raw_news_id: Optional[int] = None
    # 添加新字段
    repair_count: int = 0
    combined_processing_status: Optional[str] = None
    validation_status: Optional[str] = None
```

#### 修复 P6: 统一评分默认值

```python
# _fill_default_values 中的默认值改为 0.5
if not news.get('influence_score'):
    news['influence_score'] = 0.5
if not news.get('value_score'):
    news['value_score'] = 0.5
```

### 5.3 方案二：增强修复（推荐方案）

在最小修复基础上，增加以下改进：

#### 增强 1: 多层次修复机制

**当前设计**：
```
force_stored → 修复 1 次 → abandoned/passed
```

**改进设计**：
```
force_stored → 首次修复（同步）→ 失败 → force_stored + repair_count=1
    ↓
下次采集 → 阶段11 → 修复尝试（最多 MAX_REPAIR_ATTEMPTS 次）
    ↓
repair_count >= MAX_REPAIR_ATTEMPTS → abandoned
```

配置参数：
```python
MAX_REPAIR_ATTEMPTS = 3       # 最多修复 3 次
REPAIR_DELAY_SECONDS = 60     # 修复间隔（秒）
```

#### 增强 2: 启用 AI 补救机制

在 DataValidator 实例化时传入 AI provider：

```python
# task1_collector.py
self.data_validator = DataValidator(
    ai_provider=lambda prompt: self.combined_processor._provider.chat(
        [{"role": "user", "content": prompt}],
        max_tokens=500
    )
)
```

#### 增强 3: 修复结果详细日志

```python
# 添加结构化日志
logger.info(json.dumps({
    "event": "repair_completed",
    "news_id": news_id,
    "success": success,
    "repair_count": current_repair_count + 1,
    "final_status": final_status,
    "time_elapsed": time_elapsed
}))
```

### 5.4 方案三：完全重构（激进方案）

**重构目标**：将 force_stored 机制改为更灵活的错误处理框架

#### 新设计：修复状态机

```
                        ┌─────────────┐
                        │   NEW       │
                        └──────┬──────┘
                               │ AI处理
                        ┌──────▼──────┐
                        │  VALIDATED  │
                        └──────┬──────┘
                               │ 校验
              ┌────────────────┼────────────────┐
              │                │                │
       ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
       │   PASSED    │  │   FAILED    │  │  REMEDIATED │
       └─────────────┘  └──────┬──────┘  └─────────────┘
                               │ AI补救
                        ┌──────▼──────┐
                        │ REMEDIATED?  │
                        └──────┬──────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
             ┌──────▼──────┐       ┌──────▼──────┐
             │   PASSED    │       │ FORCE_STORED│
             └─────────────┘       └──────┬──────┘
                                          │ 重试达上限
                                   ┌──────▼──────┐
                                   │  ABANDONED  │
                                   └─────────────┘
```

#### 新增配置项

```yaml
# core_config.yaml
repair:
  max_attempts: 3                    # 最大修复尝试次数
  retry_delay_seconds: 3600          # 重试延迟（1小时，等下次采集周期）
  enable_ai_remediation: true        # 是否启用AI补救
  fallback_to_defaults: true         # 是否在补救失败时填充默认值
```

---

## 6. 实施计划

### 6.1 阶段划分

| 阶段 | 内容 | 风险 | 建议 |
|-----|------|-----|------|
| Phase 1 | 紧急 Bug 修复（P1、P2、P3、P6） | 低 | 立即实施 |
| Phase 2 | 增强功能（P4、P5） | 中 | 单元测试后实施 |
| Phase 3 | 清理旧脚本（P7） | 低 | 与 Phase 2 合并 |
| Phase 4 | 文档更新 | 低 | 最后实施 |

### 6.2 详细实施步骤

#### Phase 1: 紧急修复

1. **备份数据库**
   ```bash
   cp data/news.db data/news.db.backup
   ```

2. **修改 database.py**：
   - 在 `NewsData` 类添加 `repair_count`、`combined_processing_status`、`validation_status` 字段
   - 修改 `_news_to_dict` 方法，确保这些字段被包含
   - 修改 `INSERT_NEWS_SQL`，确保字段顺序匹配

3. **修改 task1_collector.py**：
   - 初始化 `abandoned_count = 0`
   - 统一 `_fill_default_values` 的评分默认值为 0.5

4. **添加数据库迁移方法**：
   ```python
   def migrate_add_repair_columns(self):
       """迁移：添加 repair_count 等缺失字段"""
       # 见 5.2 方案
   ```

5. **执行迁移**：
   ```python
   from core.storage.database import get_db
   db = get_db()
   db.migrate_add_repair_columns()
   ```

6. **验证**：
   ```sql
   PRAGMA table_info(news);
   -- 确认 repair_count, combined_processing_status, validation_status 存在
   ```

#### Phase 2: 增强功能

1. **配置化重试次数**
2. **启用 AI 补救**
3. **添加详细日志**
4. **编写集成测试**

#### Phase 3: 清理

1. **更新 repair_history_data.py** 使用新字段名
2. **更新 README.md** 文档
3. **更新 WORKFLOW_V3.md** 文档

---

## 7. 验证方案

### 7.1 功能验证

```python
# 验证 repair_count 字段可正常读写
from core.storage.database import get_db
db = get_db()

# 模拟一条 force_stored 数据
test_news = {
    'id': 'test_repair_' + datetime.now().strftime('%Y%m%d%H%M%S'),
    'title': 'Test Repair',
    'combined_processing_status': 'force_stored',
    'repair_count': 0
}

# 验证数据可写入
db.insert_news_batch([NewsData(**test_news)])

# 验证可读取
news = db.get_news_by_status('force_stored')
assert any(n['id'] == test_news['id'] for n in news)

# 验证可更新
db.update_news(test_news['id'], {'repair_count': 1, 'combined_processing_status': 'passed'})
updated = db.get_news_by_id(test_news['id'])
assert updated['repair_count'] == 1
assert updated['combined_processing_status'] == 'passed'
```

### 7.2 端到端验证

```bash
# 1. 清理测试数据
python -c "
from core.storage.database import get_db
db = get_db()
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute(\"DELETE FROM news WHERE title='Test Repair'\")
conn.commit()
"

# 2. 运行采集
python task1_collector.py

# 3. 检查 force_stored 数据是否被正确处理
python -c "
from core.storage.database import get_db
db = get_db()
force_stored = db.get_news_by_status('force_stored')
abandoned = db.get_news_by_status('abandoned')
print(f'force_stored: {len(force_stored)}')
print(f'abandoned: {len(abandoned)}')
"
```

---

## 8. 回滚方案

### 8.1 回滚步骤

1. **恢复数据库**：
   ```bash
   cp data/news.db.backup data/news.db
   ```

2. **代码回滚**：
   ```bash
   git checkout <phase1_commit>
   ```

### 8.2 数据修复（如果需要在线修复）

```python
# 如果 Phase 1 失败，创建修复脚本
def emergency_repair():
    """紧急修复：添加缺失字段"""
    import sqlite3
    conn = sqlite3.connect('data/news.db')
    cursor = conn.cursor()

    # 添加字段
    try:
        cursor.execute("ALTER TABLE news ADD COLUMN repair_count INTEGER DEFAULT 0")
        print("添加 repair_count 成功")
    except Exception as e:
        print(f"repair_count: {e}")

    try:
        cursor.execute("ALTER TABLE news ADD COLUMN combined_processing_status TEXT")
        print("添加 combined_processing_status 成功")
    except Exception as e:
        print(f"combined_processing_status: {e}")

    try:
        cursor.execute("ALTER TABLE news ADD COLUMN validation_status TEXT")
        print("添加 validation_status 成功")
    except Exception as e:
        print(f"validation_status: {e}")

    conn.commit()
    conn.close()
```

---

## 9. 附录

### 9.1 字段映射表（当前状态 vs 目标状态）

| 字段名 | 当前状态 | 目标状态 | 备注 |
|-------|---------|---------|------|
| `repair_count` | ❌ 不存在 | ✅ 存在 | INTEGER DEFAULT 0 |
| `combined_processing_status` | ❌ 不存在 | ✅ 存在 | TEXT |
| `validation_status` | ❌ 不存在 | ✅ 存在 | TEXT |

### 9.2 评分字段范围

| 字段 | 正确范围 | 当前错误填充值 |
|-----|---------|--------------|
| `source_score` | 0-10 | 50.0 ❌ |
| `influence_score` | 0-1 | 50.0 ❌ |
| `value_score` | 0-1 | 50.0 ❌ |
| `heat_score` | 0-10 | 50.0 ❌ |
| `final_score` | 25-84 (计算得出) | N/A |

### 9.3 相关配置文件

**core_config.yaml**（建议新增）：
```yaml
repair:
  max_attempts: 3
  retry_delay_seconds: 3600
  enable_ai_remediation: true
  fallback_to_defaults: true
```

---

## 10. 总结

### 10.1 问题总结

本次分析发现 force_stored 数据修复模块存在 **7 个问题**，其中：
- **3 个严重 Bug**（P1、P2、P3）：会导致程序崩溃或逻辑完全失效
- **3 个设计缺陷**（P4、P5、P6）：导致修复机制效率低下
- **1 个维护问题**（P7）：旧脚本使用废弃字段

### 10.2 核心问题

**第一性原理审视**发现，问题的本质是：
> **Schema（数据库结构）与 Code（业务逻辑）的不同步**

这导致：
1. 代码依赖的字段在数据库中不存在
2. SQLite 静默忽略未知字段，不报错
3. 业务逻辑完全失效，但运行时无任何错误提示

### 10.3 推荐方案

| 方案 | 修复范围 | 改动量 | 风险 | 推荐度 |
|-----|---------|-------|-----|-------|
| 方案一（最小修复） | Bug 修复 | 小 | 低 | ⭐⭐⭐⭐ |
| 方案二（增强修复） | Bug + 增强 | 中 | 中 | ⭐⭐⭐⭐⭐ |
| 方案三（完全重构） | 重构设计 | 大 | 高 | ⭐⭐ |

**推荐采用方案二**，在修复 Bug 的同时增强修复机制，提高系统鲁棒性。

---

> **下一步行动**：
> 1. 确认是否按方案二实施
> 2. 执行 Phase 1 紧急修复
> 3. 编写单元测试验证
> 4. 执行 Phase 2 增强功能
