# 新闻分析系统工作流详细说明 V3.0

> **文档用途**：面向后端开发与迭代维护人员的权威工作流说明
> **文档版本**：V3.0（基于第一性原理重构后的最终架构）
> **最后更新**：2026-04-08
> **注意**：本文档替代旧版 WORKFLOW_ARCHITECTURE.md / WORKFLOW_ARCHITECTURE_V2.md，记录的是重构后的真实状态

---

## 目录

1. [架构原则](#1-架构原则)
2. [目录结构与单一路径规则](#2-目录结构与单一路径规则)
3. [数据库设计](#3-数据库设计)
4. [task1：采集流水线（8步）](#4-task1采集流水线8步)
5. [task2：报告生成流水线（5阶段）](#5-task2报告生成流水线5阶段)
6. [核心模块详解](#6-核心模块详解)
7. [AI 调用体系](#7-ai-调用体系)
8. [兜底与降级机制](#8-兜底与降级机制)
9. [数据事务与崩溃安全性](#9-数据事务与崩溃安全性)
10. [定时调度](#10-定时调度)
11. [配置体系](#11-配置体系)
12. [评分体系](#12-评分体系)
13. [常见开发场景](#13-常见开发场景)

---

## 1. 架构原则

本项目在 2026-03-19 完成第一性原理重构，核心原则：

**每个概念只有一个规范路径（Single Canonical Path）**

| 概念 | 规范路径 | 废弃路径（已删除） |
|------|----------|---------------------|
| 所有业务代码 | `core/` | 根目录 `processors/`、`config/`、`analysts/` 等 |
| 运行时数据（DB/增量状态） | `data/` | `core/data/`（PROJECT_ROOT bug 遗留） |
| 运行时日志 | `logs/` | `core/logs/` |
| 报告输出 | `reports/` | `core/reports/` |
| 入口脚本 | `task1_collector.py`、`task2_reporter.py` | `run_collect.py`、`run_report.py`、`run_now.py` |
| task1→task2 数据交接 | SQLite `news` 表 | `data/analysis_pool/*.json`（已删除） |

---

## 2. 目录结构与单一路径规则

```
news_analyzer/
├── task1_collector.py          # 采集主入口（唯一）
├── task2_reporter.py           # 报告主入口（唯一）
├── send_email.py               # 邮件重发工具
├── sources.yaml                # RSS信源配置
├── requirements.txt
├── .env                        # 私密配置（不入库）
│
├── core/                       # 所有业务逻辑（单一代码路径）
│   ├── config/                 # 配置管理
│   │   ├── loader.py           # PROJECT_ROOT 定义（唯一来源）
│   │   ├── manager.py          # 统一配置管理器
│   │   ├── core_config.yaml    # 运行参数配置
│   │   └── report_templates.yaml
│   ├── collector/              # 采集层
│   ├── filters/                # 过滤层
│   ├── processor/              # 处理层
│   ├── storage/                # 存储层
│   └── utils/                  # 工具层
│
├── data/                       # 运行时数据（单一数据路径）
│   ├── news.db                 # 主数据库（SQLite）
│   ├── incremental/            # 增量采集状态
│   ├── baseline/               # 历史基线快照
│   ├── rejected_news/          # 过滤记录（审计）
│   └── filter_logs/
│
├── reports/{YYYY-MM-DD}/       # 报告输出（单一输出路径）
│   ├── brief/                  # 简要报告（Markdown）
│   └── depth/                  # 深度报告（PDF）
│
├── logs/                       # 运行日志（单一日志路径）
├── scripts/                    # 维护脚本
├── tests/                      # 测试套件
└── docs/                       # 开发文档
```

### PROJECT_ROOT 的唯一来源

**所有模块必须从 `core.config.loader` 导入 `PROJECT_ROOT`**，不得自行计算：

```python
# ✅ 正确
from core.config.loader import PROJECT_ROOT
data_dir = Path(PROJECT_ROOT) / "data"

# ❌ 错误（残留的旧写法）
project_root = Path(__file__).parent.parent  # 层数错误会导致路径偏移
```

`core/config/loader.py` 中的定义：
```python
def get_project_root() -> Path:
    # core/config/loader.py → parent(core/config) → parent(core) → parent(project root)
    return Path(__file__).parent.parent.parent.resolve()
```

---

## 3. 数据库设计

数据库位于 `data/news.db`（SQLite），通过 `core/storage/database.py` 访问。

### 3.1 核心表结构

#### `news` 表（主存储）

| 字段 | 类型 | 说明 |
|------|------|------|
| `news_id` | TEXT PRIMARY KEY | 内容哈希（SHA256 前16位，去重用） |
| `title` | TEXT | 原始标题 |
| `translated_title` | TEXT | 中文翻译标题 |
| `link` | TEXT | 原文 URL |
| `source` | TEXT | 信源URL/标识 |
| `source_name` | TEXT | 信源名称（如 "Reuters"） |
| `pub_date` | TEXT | 发布时间（ISO格式） |
| `content` | TEXT | 正文内容 |
| `summary` | TEXT | 100字摘要 |
| `who` | TEXT | 5W1H：主体 |
| `what` | TEXT | 5W1H：事件 |
| `when_time` | TEXT | 5W1H：时间 |
| `where_place` | TEXT | 5W1H：地点 |
| `why` | TEXT | 5W1H：原因 |
| `how` | TEXT | 5W1H：经过 |
| `domain` | TEXT | 领域分类（政治/经济/科技/军事/社会等） |
| `tags` | TEXT | JSON 数组，标签列表 |
| `keywords` | TEXT | JSON 数组，关键词 |
| `source_score` | REAL | 信源权威性（Tier映射，0–10） |
| `influence_score` | REAL | 事件影响力（LLM，0–1） |
| `value_score` | REAL | 决策价值（LLM，0–1） |
| `heat_score` | REAL | 热榜匹配热度（BGE-M3） |
| `final_score` | REAL | 综合评分（公式，25–84） |
| `score` | REAL | 别名 = final_score（历史兼容） |
| `score_timeliness` | REAL | 别名 = heat_score |
| `score_importance` | REAL | 别名 = influence_score |
| `score_credibility` | REAL | 别名 = source_score |
| `score_impact` | REAL | 别名 = value_score |
| `classification_confidence` | REAL | 轻量分类置信度 |
| `embedding` | BLOB | BGE-M3 向量（历史关联用） |
| `created_at` | TEXT | 入库时间 |

#### `processed_news` 表（去重指纹）

与 `news` 表同步写入，仅存 `news_id + processed_at`，用于下次采集时快速批量去重（避免 N+1 查询）。

#### `news_fts` 表（全文搜索）

FTS5 虚拟表，自动与 `news` 主表同步，支持中文全文检索。

#### `entities` + `news_entities` 表

实体存储（人物、机构、地点），由 `EntityExtractor` 填入，用于跨新闻关联分析。

#### `market_context` 表

市场快照（汇率、指数、大宗商品、利率），由 `MarketDataFetcher` 每日写入一次，简报报告引用。

#### `hotboard_cache` 表

四平台热榜缓存（微博/知乎/百度/头条），TTL 3小时，`HotboardFetcher` 管理。

### 3.2 数据库访问方式

```python
from core.storage.database import get_db

db = get_db()                          # 获取全局单例（优先，用于主流程）
db.get_recent_news(hours=24)           # 获取近24小时新闻
db.get_history_news(days=90)           # 获取近90天历史
db.filter_processed_ids(id_set)        # 返回已处理的 ID 集合
db.insert_news_batch(news_list)        # 批量原子写入（news + processed_news）
db.get_stats()                         # 获取统计信息
```

**注意**：`get_db()` 使用单例 + 连接池，连接池大小为 5（WAL 模式，PRAGMA busy_timeout=5000ms）。

---

## 4. task1：采集流水线（12步）

入口：`task1_collector.py` → `Task1Collector.run()`

```
外部RSS源
    │
    ▼ Step 1: 全信源采集（增量模式）
    │  RSSCollector + IncrementalTracker
    │  增量截断：只取上次采集时间之后的条目
    │  采集后立即存入 raw_news 表
    │
    ▼ Step 2: 字段规范化
    │  FieldNormalizer.normalize_fields(item)
    │  统一字段名、清洗空值、生成 news_id (SHA256哈希前16位)
    │
    ▼ Step 3: 存储原始数据（raw_news 表）
    │
    ▼ Step 4: 轻量级分类
    │  LightweightClassifier.classify_batch(news_list)
    │  规则层：关键词 + RSS category 映射 → domain
    │  置信度阈值配置驱动（默认≥0.7 时填充 domain）
    │
    ▼ Step 5: 基础三层过滤
    │  ├─ SourceValidator：信源白名单校验
    │  ├─ 可信度过滤
    │  └─ 历史去重：db.filter_processed_ids() 批量查询去掉已入库 ID
    │
    ▼ Step 6: 合并 LLM 处理（单次 API 调用）
    │  CombinedProcessor.process_news(news)
    │  输出：translation / summary / 5W1H / scoring(4维)
    │  熔断器：连续 3 次致命错误后跳过剩余批次
    │  Token限额：FILTER 接近日限时自动切换 BACKUP 模型
    │
    ▼ Step 7: 数据完整性校验
    │  DataValidator.validate_combined_result(news, result)
    │  校验通过 → passed；校验失败 → force_stored + 默认值填充
    │
    ▼ Step 8: 向量化生成（BGE-M3，passed + force_stored）
    │  仅对缺失向量的新闻调用 BGE-M3 批量编码
    │
    ▼ Step 9: 热度评分（仅 passed 数据）
    │  HeatProcessor.calculate_batch(news_list)
    │  BGE-M3 向量 → FAISS 匹配热榜（优先），配置驱动
    │  降级：TF-IDF 关键词命中计数
    │
    ▼ Step 10: 批量事务写入 SQLite
    │  db.insert_news_batch(news_list)
    │  原子事务：news 表 + processed_news 表同时写入
    │  更新 raw_news.processed=1
    │
    ▼ Step 11: force_stored 修复（已简化）
    │  不再自动修复，保留数据降权处理
    │
    ▼ Step 12: 清理过期原始数据（>7天）
       删除 raw_news 中 processed=1 的历史记录
```

### 4.1 进度与状态监控

采集过程使用 `HeartbeatMonitor` 单例追踪进度：

```python
from core.utils.heartbeat import get_heartbeat_monitor
hb = get_heartbeat_monitor()

hb.start("collect", "开始采集")               # 任务开始
hb.update("collect", progress=0.5, msg="过滤中")  # 进度更新
hb.success("collect", "采集完成")             # 成功结束
hb.failure("collect", "采集失败: {err}")      # 失败结束
```

### 4.2 并发保护

`TaskLock`（跨平台文件锁）防止同一 task 多实例并发：

```python
from core.utils.task_lock import task_lock

with task_lock("task1"):
    # task1_collector 主体逻辑
    ...
```

锁文件位于 `data/task1.lock`；超过 30 分钟自动释放（超时保护）。

### 4.3 增量采集逻辑

`IncrementalTracker` 将每个信源的最后 `pub_date` 持久化到 `data/incremental/tracker_state.json`：

```python
tracker.get_intelligent_cutoff_date(source_name)  # 返回截断时间点
tracker.get_suggested_max_items(source_name, default_max)  # 宕机>12h时翻倍
tracker.update_state(source_name, latest_pub_date, count)  # 采集后更新
```

| 宕机时长 | 诊断类型 | 处理策略 |
|----------|----------|----------|
| < 2h | normal | 正常增量 |
| 2–24h | short_interruption | 正常增量 |
| 24–72h | day_interruption | max_items × 2 |
| > 72h | long_interruption | max_items × 2（上限50） |

### 4.4 Step 4 去重的批量优化

旧架构：对每条新闻单独 SELECT → N 次查询
新架构：`db.filter_processed_ids(id_set)` 一次 `WHERE news_id IN (?,?,...)` 返回已处理集合，然后本地集合差集计算未处理条目。时间复杂度从 O(N) 次 DB 往返变为 O(1) 次。

---

## 5. task2：报告生成流水线（5阶段）

入口：`task2_reporter.py` → `Task2DailyReporter.run(top_n=10)`

```
data/news.db（SQLite，task1 写入的单一权威数据源）
    │
    ▼ 阶段1: DB 读取近24小时新闻
    │  db.get_recent_news(hours=24)
    │  无数据时自动兜底：取最近可用一天（_fallback_latest）
    │
    ▼ 阶段2: 记录新闻数量
    │
    ▼ 阶段3: 生成简要摘要报告
    │  ReportGenerator.generate_brief_report(dedup_news, report_date)
    │  内容：市场数据仪表盘 + TOP 10 新闻（按 final_score×0.7 + heat_score×0.3）
    │  输出：reports/{date}/brief/*.md
    │
    ▼ 阶段4: 生成深度分析报告
    │  基础数据：db.get_history_news(days=90)（近90天历史，BGE-M3关联用）
    │  ReportGenerator.generate_depth_reports(dedup_news, report_date, history_news)
    │  每个活跃领域生成一份，包含：
    │    ① 领域综述与核心信号
    │    ② 历史关联事件（BGE-M3语义检索）
    │    ③ 跨领域共振分析
    │    ④ 投资/决策建议
    │  输出：reports/{date}/depth/*.pdf
    │
    ▼ 阶段5: 邮件推送（可选）
       is_email_configured() → 检查 SMTP 全部配置是否存在
       send_email_with_attachments(subject, brief_content, pdf_attachments)
       正文：简要报告 Markdown 内容
       附件：各领域深度报告 PDF
```

### 5.1 兜底策略

当 `get_recent_news(hours=24)` 返回空（任务间隔超时、首次运行等场景）：

```python
def _fallback_latest(self, days: int = 7) -> List[Dict]:
    history = self.db.get_history_news(days=days)
    if not history:
        return []
    # 找最近有数据的一天
    latest_date = max(n['pub_date'][:10] for n in history if n.get('pub_date'))
    return [n for n in history if n.get('pub_date', '').startswith(latest_date)]
```

### 5.2 TOP N 选择公式

```python
def _select_top_n(self, news_list, n):
    def sort_key(x):
        impact = x.get('final_score', x.get('influence_score', 0))
        heat   = x.get('heat_score', 0)
        return impact * 0.7 + heat * 0.3
    return sorted(news_list, key=sort_key, reverse=True)[:n]
```

---

## 6. 核心模块详解

### 6.1 CombinedProcessor（Step 5 核心）

**文件**：`core/processor/combined_processor.py`

单次 LLM 调用完成四步输出：

```
输入：{title, content, source_name, pub_date}
LLM 调用（FILTER provider）
输出 JSON：
  translation         → 中文标题
  translated_content  → 中文正文
  summary             → 100字摘要
  analysis.{who/what/when/where/why/how}  → 5W1H
  domain              → 领域分类
  tags                → 标签列表
  scoring.{source_score, influence_score, value_score, compliance_score}
```

**熔断器机制**：LLM 连续 3 次致命错误（401/403 认证失败等）后自动跳过剩余批次，避免浪费超时窗口。

**BACKUP 兜底**：FILTER 模型 Token 限额触发（`TokenLimitExceeded`）或 API 失败时，自动切换到 BACKUP 模型重试。

**失败降级**：LLM 调用仍失败时返回原始字段（title不翻译，5W1H为空，评分为0），不阻断流水线。

### 6.2 HeatProcessor（Step 7 核心）

**文件**：`core/processor/heat_processor.py`

```
热榜数据来源：HotboardFetcher → 四平台（微博/知乎/百度/头条）
                              → DB缓存 3小时（hotboard_cache表）

评分流程：
  1. 优先：BGE-M3 向量编码热榜标题 → FAISS 索引 → 余弦相似度
  2. 降级：TF-IDF 关键词命中计数（faiss/sentence-transformers 不可用时）

输出：news['heat_score']（0–10）
```

### 6.3 AIFilterAgent（task2 语义去重）

**文件**：`core/filters/ai_filter_agent.py`

```python
# 去重接口
result = ai_filter.check_duplicates(news_items)
# result.kept_ids: List[str]  保留的 news_id

# 5W1H 守门接口（task1 Step 4 基础过滤之后可选调用）
result = ai_filter.check_news(news_item)
# result.passed: bool
# result.reason: str
```

**设计说明**：AIFilterAgent 保留其"守门人"角色（语义去重 + 5W1H合规过滤），与 CombinedProcessor（翻译+评分合并调用）职责分离，互不替代。

### 6.4 BGE3HistoryRelationEngine（深度报告历史关联）

**文件**：`core/processor/history_relation_engine_bge3.py`

```
输入：当日新闻列表 + 近90天历史新闻（含 embedding BLOB）

流程：
  1. 读取 DB 中已存储的 embedding（BLOB） → 无需重新编码
  2. 无 embedding 时现场 BGE-M3 编码
  3. FAISS cosine 检索最近邻
  4. 意义分类：is_meaningful(score) 过滤噪音
  5. 格式化：format_related_table / format_related_section

降级：sentence-transformers 不可用时 → TF-IDF 关键词匹配（Jaccard相似度）
```

### 6.5 ReportGenerator（报告双轨生成）

**文件**：`core/processor/generators/report_generator.py`

```
generate_brief_report(news_list, report_date)
  → 获取市场快照（MarketDataFetcher）
  → 格式化市场仪表盘（汇率/指数/大宗/利率）
  → 按 TOP N 排序
  → 输出 Markdown：reports/{date}/brief/report_{date}.md

generate_depth_reports(all_news, report_date, history_news)
  → 按 domain 分组（min_news_per_domain 阈值过滤）
  → 每个领域：
      ① 调用 DepthAnalyzer.analyze(domain_news, domain, history_news)
         → LLM JSON结构化输出（4个章节的 Markdown 内容）
      ② md2pdf 转换 → reports/{date}/depth/{domain}_report.pdf
  → 返回 PDF 路径列表
```

### 6.6 FieldNormalizer（Step 2）

**文件**：`core/processor/field_normalizer.py`

处理单条 dict：
- 清洗空字符串、None → 统一字段名
- `news_id` = `sha256(title + source + pub_date)[:16]`（内容哈希，可重现）
- 时间格式标准化 → ISO 8601
- `source_score` = Tier 映射（Tier1=9.5, Tier2=7.5, Tier3=5.5）

### 6.7 DataValidator（Step 8）

**文件**：`core/processor/data_validator.py`

检查 5W1H 各字段是否存在、是否为有意义内容：
- `who`/`what` 必填，缺失时尝试从 title 提取
- `when_time` 缺失时使用 `pub_date`
- `where_place` 缺失时从 content 提取地名
- 写入 `extraction_method`：`rule_only` / `ai_fallback` / `ai_only` / `unknown`

---

## 7. AI 调用体系

### 7.1 Provider 三档

```python
from core.processor.ai_processor import AIProcessor
ai = AIProcessor()

provider = ai.get_provider("FILTER")    # 快速筛选：豆包 doubao-seed-2-0
provider = ai.get_provider("ANALYSIS")  # 深度分析：DeepSeek-reasoner
provider = ai.get_provider("BACKUP")    # 备用兜底：通义千问 qwen-plus
```

**注意**：必须传枚举字符串 `"FILTER"` / `"ANALYSIS"` / `"BACKUP"`，不能传 provider 名称。

### 7.2 各 provider 用途

| Provider | 模型 | 主要调用场景 |
|----------|------|-------------|
| FILTER | 豆包 doubao-seed-2-0 系列 | CombinedProcessor（task1 Step6），模型名通过环境变量/AI_FILTER_MODEL Secret配置 |
| ANALYSIS | DeepSeek-reasoner | DepthAnalyzer 领域深度报告（4章节结构化输出） |
| BACKUP | 豆包 doubao-seed-2-0-pro（推荐） | FILTER Token限额触发时自动切换；配置于 AI_BACKUP_* 环境变量 |

### 7.3 环境变量

```bash
# 深度分析模型
AI_ANALYSIS_PROVIDER=deepseek
AI_ANALYSIS_MODEL=deepseek-reasoner
AI_ANALYSIS_KEY=
AI_ANALYSIS_BASE_URL=https://api.deepseek.com/v1

# 快速筛选模型
AI_FILTER_PROVIDER=doubao
AI_FILTER_MODEL=doubao-seed-2-0-lite-260215
AI_FILTER_KEY=
AI_FILTER_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# 备用模型（Token限额触发时自动切换）
AI_BACKUP_PROVIDER=
AI_BACKUP_MODEL=
AI_BACKUP_KEY=
AI_BACKUP_BASE_URL=

# Token限额（按天，可选）
AI_TOKEN_LIMIT_DEFAULT=2000000
AI_TOKEN_THRESHOLD_DEFAULT=0.9
```

---

## 8. 兜底与降级机制

### 8.1 BGE-M3 / FAISS 不可用

| 模块 | 主路径 | 降级路径 |
|------|--------|----------|
| HeatProcessor | BGE-M3 向量 + FAISS | TF-IDF 关键词命中计数 |
| BGE3HistoryRelationEngine | BGE-M3 + FAISS 检索 | TF-IDF Jaccard 相似度 |

降级触发条件：`import faiss` 或 `import sentence_transformers` 失败。降级时主流程继续，`heat_score` 精度下降但不为零。

### 8.2 LLM API 失败

- **CombinedProcessor**：返回原始字段（空 5W1H，评分0），不抛异常，流水线继续
- **DepthAnalyzer**：该领域深度报告跳过，其他领域继续生成
- **AIFilterAgent**：去重失败时保留全部 news（宁可重复也不丢数据）

### 8.3 task2 数据兜底

```
db.get_recent_news(hours=24) 返回空
   → _fallback_latest(days=7)：取近7天最新一天的数据
      → 仍为空 → 返回 {'success': False, 'reason': 'no_news_in_db'}
```

### 8.4 邮件发送失败

不影响报告生成。报告文件已落地 `reports/` 目录，可用 `send_email.py` 单独重发。

---

## 9. 数据事务与崩溃安全性

### 9.1 原子写入保证

`db.insert_news_batch()` 在**单个事务**中同时写入 `news` 表和 `processed_news` 表：

```python
with self.transaction():
    for news in news_list:
        INSERT INTO news (...)
        INSERT INTO processed_news (news_id, processed_at)
```

事务失败 → 整批回滚 → `processed_news` 中无此批记录 → 下次运行重新采集并处理。

### 9.2 崩溃场景分析

| 崩溃时机 | 状态 | 下次运行结果 |
|----------|------|-------------|
| Step 1–8 之间崩溃 | 无任何 DB 写入 | 正常重新采集 |
| Step 9 事务中崩溃 | 整批回滚 | 正常重新采集 |
| Step 9 事务提交后崩溃 | news + processed_news 已一致 | 去重正常工作 |
| task2 阶段3–4 崩溃 | 报告文件可能不完整 | 下次重新生成（覆盖） |

### 9.3 已知边缘情况

**被拒绝的新闻（rejected_news）不写入 `processed_news`**：
- 原因：被 SourceValidator / ContentFilter 过滤掉的新闻在 Step 4 之后丢弃，不进 Step 9
- 影响：下次采集时这些 ID 不在 `processed_news` 中，会被重新拉取并再次过滤
- 后果：CPU/网络开销略增，无数据错误

如需记录拒绝历史，可扩展 Step 4 后写入 `data/rejected_news/` 文件（StorageManager 支持）。

---

## 10. 定时调度

### 10.1 本地运行（手动或按需）

| 命令 | 用途 |
|------|------|
| `python task1_collector.py` | 采集新闻（写入DB） |
| `python task2_reporter.py` | 生成报告 + 发邮件 |
| `python task2_reporter.py --no-email` | 生成报告（不发邮件） |
| `python send_email.py` | 重发最新报告邮件 |

> **注意**：项目已全面迁移到 GitHub Actions 自动化运行，本地无需配置定时任务。如需本地手动测试，直接执行上述命令即可。

### 10.2 GitHub Actions

| 工作流 | 文件 | 北京时间 | 内容 |
|--------|------|----------|------|
| 采集+报告 | `.github/workflows/collect.yml` | 07:00（采集+报告）、15:00/23:00（纯采集） | task1 + task2 |

| 邮件推送 | `.github/workflows/send_email.yml` | 08:30 | send_email.py |

**数据持久化**：SQLite `data/` 目录通过 `actions/cache` 在 Actions 运行间保持；报告文件通过 `actions/upload-artifact` 传递给邮件工作流。

---

## 11. 配置体系

### 11.1 配置层级

```
.env                           # 私密（API Key、SMTP）
core/config/core_config.yaml   # 运行参数（阈值、批量大小等）
sources.yaml                   # 信源分层配置（Tier 1/2/3）
core/config/report_templates.yaml  # 报告模板（minimal/default/detailed）
```

### 11.2 信源配置（sources.yaml）

每条信源字段：

```yaml
- name: "Reuters"
  url: "https://feeds.reuters.com/reuters/topNews"
  tier: 1          # 1=核心骨架（必采）/ 2=区域支柱 / 3=专业补充
  domain: "政治"   # 默认领域（LLM 可覆盖）
  language: "en"
  enabled: true
```

**Tier → source_score 映射**：Tier1=9.5, Tier2=7.5, Tier3=5.5（由 `core/utils/source_scorer.py` 执行，配置驱动）

### 11.3 报告生成阈值

`core/config/core_config.yaml` 中关键参数（可调整，无需改代码）：

```yaml
report:
  min_news_per_domain: 3     # 深度报告最少需要的领域新闻数
  top_n_brief: 10            # 简报 TOP N 条数
  history_days: 90           # 历史关联检索天数
```

---

## 12. 评分体系

### 12.1 五维度评分

| 字段 | 范围 | 来源 | 说明 |
|------|------|------|------|
| `source_score` | 0–10 | 规则（Tier映射） | Tier1=9.5, Tier2=7.5, Tier3=5.5 |
| `influence_score` | 0–10 | LLM（CombinedProcessor） | 事件影响范围 |
| `value_score` | 0–10 | LLM（CombinedProcessor） | 投资/政策决策价值 |
| `heat_score` | 0–10 | BGE-M3（HeatProcessor） | 热榜匹配热度 |
| `final_score` | 0–100 | 配置驱动公式加权 | 综合评分 |

### 12.2 final_score 计算公式（配置驱动）

权重从 `core_config.yaml → scoring.weights` 读取，修改配置即时生效：

```python
# 公式: (source×w1 + influence×w2 + value×w3 + heat×w4) / 10 × 100
# 各项输入范围 0-10，输出范围 0-100
# 默认权重: source=0.25, influence=0.25, value=0.25, heat=0.25（等权）
```

**Tier 分值映射**（配置驱动）：Tier1=9.5, Tier2=7.5, Tier3=5.5, 默认=5.0

### 12.3 TOP N 排序公式

```python
rank_score = final_score * 0.7 + heat_score * 0.3
```

热度权重在 TOP N 选择时进一步加强（热门新闻优先呈现）。

---

## 13. 常见开发场景

### 13.1 验证系统基础配置

```bash
python -c "from core.config.loader import PROJECT_ROOT; print(PROJECT_ROOT)"
python -c "from core.storage.database import get_db; db=get_db(); print(db.get_stats())"
```

### 13.2 手动执行完整流程

```bash
# 采集（写入 DB）
python task1_collector.py

# 生成报告（从 DB 读取，不发邮件）
python task2_reporter.py --no-email

# 顺序执行
python task1_collector.py && python task2_reporter.py --no-email

# 重发最新报告
python send_email.py
```

### 13.3 添加新信源

编辑 `sources.yaml`，按已有格式添加条目，设置 `enabled: true`。无需改代码，下次 task1 运行自动生效。

### 13.4 调整深度报告领域阈值

修改 `core/config/core_config.yaml` 中 `report.min_news_per_domain`。若某领域一直无深度报告，降低此阈值或在 `sources.yaml` 开启更多该领域信源。

### 13.5 强制重新处理历史数据

清空 `processed_news` 表中对应记录，下次 task1 运行时这些新闻将重新被处理：

```sql
DELETE FROM processed_news WHERE news_id IN (...);
```

### 13.6 修复评分字段

使用 `scripts/database/repair_scores.py`：

```bash
python scripts/database/repair_scores.py --only source    # Tier映射 source_score
python scripts/database/repair_scores.py --only heat      # 启发式 heat_score
python scripts/database/repair_scores.py --only final     # 公式计算 final_score
```

**注意**：脚本中写入操作需显式 `conn.commit()`，`get_connection()` 不自动提交。

### 13.7 定位 PROJECT_ROOT 相关路径问题

所有运行时输出若出现在意外位置（如写入了 `core/` 子目录），检查相关模块是否直接计算了 `Path(__file__).parent.parent` 而没有从 `core.config.loader` 导入 `PROJECT_ROOT`。

### 13.8 模块导入测试

```bash
# 验证所有核心模块可导入
python -c "
from core.collector.collector import RSSCollector
from core.processor.combined_processor import CombinedProcessor
from core.processor.heat_processor import HeatProcessor
from core.filters.ai_filter_agent import AIFilterAgent
from core.storage.database import get_db
from core.utils.heartbeat import get_heartbeat_monitor
from core.utils.task_lock import task_lock
print('All imports OK')
"
```

---

## 附录：模块依赖关系

```
task1_collector.py
├── core.config (PROJECT_ROOT, get_current_date)
├── core.storage.database (get_db)
├── core.utils.task_lock (task_lock)
├── core.utils.heartbeat (get_heartbeat_monitor)
├── core.collector.collector (RSSCollector, RSSSourceManager)
├── core.collector.sources (SourceManager)
├── core.processor.field_normalizer (FieldNormalizer)
├── core.processor.lightweight_classifier (LightweightClassifier)
├── core.filters.source_validator (SourceValidator)
├── core.filters.content_filter (ContentFilter)
├── core.utils.incremental_tracker (IncrementalTracker)
├── core.processor.combined_processor (CombinedProcessor)
│   └── core.processor.ai_processor (AIProcessor → FILTER provider)
├── core.processor.heat_processor (HeatProcessor)
│   └── core.utils.hotboard_fetcher (HotboardFetcher → hotboard_cache)
├── core.processor.data_validator (DataValidator)
└── core.storage.database (insert_news_batch → 原子事务)

task2_reporter.py
├── core.config
├── core.storage.database (get_db → get_recent_news, get_history_news)
├── core.filters.ai_filter_agent (AIFilterAgent → check_duplicates)
├── core.processor.generators.report_generator (ReportGenerator)
│   ├── core.utils.market_data_fetcher (MarketDataFetcher)
│   ├── core.processor.depth_analyzer (DepthAnalyzer → ANALYSIS provider)
│   ├── core.processor.history_relation_engine_bge3 (BGE3HistoryRelationEngine)
│   └── core.utils.md2pdf (md2pdf)
└── core.utils.email_sender (send_email_with_attachments)
```
