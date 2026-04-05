# News Analyzer

基于 AI 的新闻采集与分析系统，服务**投资分析、制度掌握、科技发展**三大决策方向。

每日自动完成：多信源采集 → AI 解析评分 → 简报 + 深度报告 → 邮件推送。

**最后更新**：2026-03-20 | **架构**：单一数据路径（SQLite） | **新增**：校验前置 + force_stored 修复机制 + abandoned 状态

---

## 目录

- [系统架构](#系统架构)
- [数据流](#数据流)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [运行方式](#运行方式)
- [自动化部署](#自动化部署)
- [输出说明](#输出说明)
- [常见问题](#常见问题)

---

## 系统架构

### 五层模块结构

```
core/
├── collector/    采集层   RSS 抓取、解析、增量追踪、爬虫
├── filters/      过滤层   信源校验、去重、AI 5W1H 守门
├── processor/    处理层   字段规范化、LLM 合并处理、热度评分、报告生成
├── storage/      存储层   SQLite 数据库、文件管理
└── utils/        工具层   心跳监控、任务锁、邮件、热榜、市场数据
```

### 三个入口脚本

| 脚本 | 职责 | 触发频率 |
|------|------|----------|
| `task1_collector.py` | 采集主入口，11 步流水线，写入 SQLite | 每天 3 次 |
| `task2_reporter.py` | 报告主入口，从 DB 读取，双轨输出 | 每天 1 次 |
| `send_email.py` | 独立邮件重发，查找最新报告文件发送 | 按需 |

### AI 模型分工

| 角色 | 用途 | 推荐模型 |
|------|------|----------|
| FILTER | 翻译 + 摘要 + 5W1H + 评分（单次合并调用） | 豆包 doubao-seed-2-0 |
| ANALYSIS | 领域深度分析报告 | DeepSeek-reasoner |
| BACKUP | 兜底备用 | 通义千问 |

---

## 数据流

```
外部 RSS 源
     │
     ▼  task1_collector.py（每天 3 次）
┌─────────────────────────────────────────┐
│ Step 1  全信源采集（增量模式）           │
│         └─ 采集后立即存入 raw_news 表   │
│ Step 2  字段规范化（FieldNormalizer）    │
│ Step 3  存储原始数据（raw_news 表）      │
│ Step 4  轻量级分类（8 类，置信度≥0.7 时填充 domain） │
│         └─ 关键词 + RSS category 映射，无外部依赖
│ Step 5  基础三层过滤                    │
│         ├─ 信源白名单校验               │
│         ├─ 可信度过滤                   │
│         └─ 历史去重（DB 批量查询）      │
│ Step 6  合并 LLM（单次 API 调用）       │
│         翻译 + 摘要 + 5W1H + 5 维评分  │
│ Step 7  数据完整性校验（前置）          │
│         ├─ 校验通过 → passed            │
│         └─ 校验失败 → force_stored + repair_count=0 │
│ Step 8  向量化生成（passed + force_stored 都生成）│
│ Step 9  热度评分（仅 passed 数据）      │
│ Step 10 批量事务写入 SQLite             │
│         └─ 更新 raw_news.processed=1   │
│ Step 11 修复 force_stored 数据          │
│         ├─ repair_count < 1 → 重新处理  │
│         ├─ 修复成功 → passed            │
│         ├─ 修复失败 → force_stored      │
│         └─ repair_count >= 1 → abandoned│
└──────────────────┬──────────────────────┘
                   │
                   ▼  data/news.db（单一权威数据源）
┌─────────────────────────────────────────┐
│ task2_reporter.py（每天 1 次）           │
│                                         │
│ 阶段 1  DB 读取近 24h 新闻                 │
│ 阶段 2  记录新闻数量                       │
│ 阶段 3  生成简要报告（TOP10，按评分排序）     │
│         └─ 直接使用 task1 产出的翻译摘要     │
│ 阶段 4  生成深度报告（按领域）               │
│         ├─ 事件聚类 → TOP5                │
│         ├─ 原文获取（article_fetcher）     │
│         ├─ 全文向量关联（BGE-M3索引B）      │
│         └─ 深度分析                       │
│ 阶段 5  发送邮件                           │                
│└──────────────────┬──────────────────────┘
                   │
                   ▼
     reports/{date}/brief/*.md
     reports/{date}/depth/*.pdf
```

### 数据状态流转

```
┌─────────────────────────────────────────────────────────────┐
│  Task1 数据处理状态流转                                      │
│                                                              │
│  AI处理 → 校验                                               │
│     ├─ valid/remediated → passed → 向量化 → 热度评分 → 存储  │
│     └─ 其他 → force_stored (repair_count=0) → 向量化 → 存储 │
│                                                              │
│  修复循环（Task1 阶段11）                                    │
│     force_stored 数据:                                       │
│     ├─ repair_count >= 1 → abandoned（放弃修复）             │
│     ├─ 修复成功 → passed                                     │
│     └─ 修复失败 → force_stored (repair_count += 1)           │
│                                                              │
│  最终状态:                                                   │
│     passed     → 正常参与 Task2 报告生成                     │
│     force_stored → 等待下次修复                              │
│     abandoned  → 放弃修复，保留数据但不参与处理               │
└─────────────────────────────────────────────────────────────┘
```

### 评分体系

| 字段 | 含义 | 来源 |
|------|------|------|
| `source_score` | 信源权威性（Tier 1/2/3 映射） | 规则 |
| `influence_score` | 事件影响力 | LLM |
| `value_score` | 决策价值 | LLM |
| `heat_score` | 热榜向量匹配热度 | BGE-M3 |
| `final_score` | 综合得分（25–84） | 公式加权 |
| `combined_processing_status` | AI处理状态：passed/force_stored/abandoned | 自动 |
| `repair_count` | 修复尝试次数（0-1） | 自动 |

TOP N 排序公式：`final_score`（由 `score_timeliness×0.25 + score_importance×0.25 + score_credibility×0.25 + score_impact×0.25` 计算）

### force_stored 数据修复机制

| 场景 | 处理方式 |
|------|---------|
| AI处理成功 + 校验通过 | `combined_processing_status = 'passed'` |
| AI处理成功 + 校验失败 | `combined_processing_status = 'force_stored'` + repair_count=0 |
| AI处理失败 | 进入 `rejected_news` 表 |
| 修复失败 1 次 | `combined_processing_status = 'abandoned'` |

修复时机：
- **采集完成后**（task1_collector.py 阶段11）：自动调用AI重新处理 `force_stored` 数据
- **修复限制**：每条数据最多修复 1 次，超过则标记为 `abandoned`
- **报告生成前**（task2_reporter.py）：task1 在 07:00 先完成修复，task2 在 08:30 无需重复修复

---

## 项目结构

```
news_analyzer/
├── task1_collector.py          采集主入口（11 步流水线）
├── task2_reporter.py           报告主入口（双轨输出）
├── send_email.py               邮件重发工具
├── sources.yaml                RSS 信源配置（Tier 1/2/3，45 KB）
├── requirements.txt            Python 依赖
├── .env                        环境变量（本地，不入库）
├── .env.example                环境变量示例
├── Dockerfile / docker-compose.yml
│
├── core/
│   ├── collector/
│   │   ├── collector.py            RSSCollector + RSSSourceManager
│   │   ├── sources.py              信源定义与 Tier 管理
│   │   ├── parser.py               原始 Feed 解析
│   │   ├── api_sources.py          API 类信源接入
│   │   ├── incremental_collector.py 智能补救采集（遗漏检测）
│   │   └── crawlers/               新华社、人民网定向爬虫
│   │
│   ├── filters/
│   │   ├── ai_filter_agent.py      5W1H 校验 + 语义去重（守门人）
│   │   ├── source_validator.py     信源白名单校验
│   │   ├── content_filter.py       内容质量过滤
│   │   └── deduplication.py        哈希去重
│   │
│   ├── processor/
│   │   ├── combined_processor.py       单次 LLM 合并处理
│   │   ├── content_parser.py           RuleBasedParser + EntityExtractor
│   │   ├── field_normalizer.py         字段标准化
│   │   ├── lightweight_classifier.py   轻量级领域分类（政治/经济/科技/军事/社会/文化/体育/娱乐） |
│   │   ├── heat_processor.py           BGE-M3 热度向量匹配
│   │   ├── depth_analyzer.py           领域深度分析（JSON 结构化输出，支撑全文分析）
│   │   ├── article_fetcher.py          新闻原文获取器（Google RSS 解析 + 代理访问）
│   │   ├── data_validator.py           5W1H/domain 校验 + AI 补救 + 默认值填充
│   │   ├── history_relation_engine_bge3.py  BGE-M3 历史关联引擎（索引A：标题向量）
│   │   ├── history_relation_engine_fulltext.py  BGE-M3 全文关联引擎（索引B：全文向量）
│   │   ├── investment_advisor.py       投资建议生成
│   │   └── generators/
│   │       └── report_generator.py    简报 + 深度报告双轨生成
│   │
│   ├── storage/
│   │   ├── database.py             NewsDatabase + NewsData（SQLite 主库）
│   │   ├── storage_manager.py      文件存储（baseline / rejected_news）
│   │   ├── baseline.py             历史基线管理
│   │   └── file_manager.py         报告文件管理
│   │
│   ├── config/
│   │   ├── loader.py               PROJECT_ROOT 定义、环境变量加载
│   │   ├── manager.py              统一配置管理器
│   │   ├── core_config.yaml        核心运行配置
│   │   └── report_templates.yaml   报告模板（default / minimal / detailed）
│   │
│   └── utils/
│       ├── heartbeat.py            HeartbeatMonitor 单例，8 步进度追踪
│       ├── workflow_timer.py      WorkflowTimer 各阶段耗时追踪，生成 JSON 日志
│       ├── task_lock.py            跨平台文件锁，防并发重复执行
│       ├── incremental_tracker.py  信源增量状态持久化
│       ├── hotboard_fetcher.py     四平台热榜（微博/知乎/百度/头条，缓存 3h）
│       ├── market_data_fetcher.py  市场数据（汇率/指数/大宗/利率，日级缓存）
│       ├── email_sender.py         SMTP 邮件发送
│       ├── source_scorer.py        信源 Tier → source_score 映射
│       └── md2pdf.py               Markdown → PDF 转换
│
├── data/
│   ├── news.db                 主数据库（SQLite，1500+ 条历史记录）
│   ├── incremental/            增量采集状态（各信源最后采集时间）
│   ├── baseline/               历史基线快照
│   ├── rejected_news/          过滤记录（审计用）
│   └── filter_logs/            过滤日志
│
├── reports/
│   └── {YYYY-MM-DD}/
│       ├── brief/              简要摘要报告（Markdown）
│       └── depth/              深度分析报告（PDF，按领域）
│
├── logs/                       运行日志（task1 / task2 / send_email）
├── scripts/                    维护脚本（数据库修复、迁移、健康检查）
│   └── tools/
│       └── fix_history_data.py  历史数据修复脚本（标记 force_stored）
├── tests/                      测试套件（206 tests）
├── docs/                       开发文档
└── commercial/                 商业版模块（独立，不影响主流程）
```

---

## 快速开始

### 环境要求

- Python 3.9+
- 至少一个 AI API Key（豆包 ARK_API_KEY 为必填，用于 FILTER 层）

### 安装

```bash
git clone <repo-url>
cd news_analyzer
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 API Key
```

### 验证配置

```bash
python -c "from core.config.loader import PROJECT_ROOT; print(PROJECT_ROOT)"
python -c "from core.storage.database import get_db; db=get_db(); print(db.get_stats())"
```

---

## 配置说明

### `.env` 关键变量

```bash
# ── AI 模型（ARK_API_KEY 必填）──────────────────────────
ARK_API_KEY=          # 豆包 API Key（FILTER 层）
DEEPSEEK_API_KEY=     # DeepSeek（ANALYSIS 层）
QWEN_API_KEY=         # 通义千问（BACKUP 层）
DASHSCOPE_API_KEY=    # DashScope（阿里云）

# ── 模型接入地址 ─────────────────────────────────────────
DOUBAO_API_BASE=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_MODEL=doubao-seed-2-0-lite-260215
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
QWEN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# ── 热榜 API（可选）─────────────────────────────────────
HOTBOARD_API_KEY=     # 四平台热榜数据

# ── 邮件推送（可选）─────────────────────────────────────
SMTP_HOST=
SMTP_PORT=465
SMTP_USER=
SMTP_PASSWORD=
EMAIL_TO=
```

### `sources.yaml` 信源分层

```
Tier 1  核心骨架（必采）  路透社、BBC、新华社、央视等
Tier 2  区域支柱          各国主要媒体
Tier 3  专业补充          行业垂直媒体
```

每个信源字段：`name`、`url`、`tier`、`domain`、`language`、`enabled`。

---

## 运行方式

### 本地手动执行

```bash
# 采集新闻（写入 DB）
python task1_collector.py

# 生成报告（从 DB 读取）
python task2_reporter.py

# 不发送邮件
python task2_reporter.py --no-email

# 采集 + 报告顺序执行
python task1_collector.py && python task2_reporter.py --no-email

# 重发最新报告邮件
python send_email.py
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试（快速）
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 查看测试覆盖
pytest --cov=. --cov-report=html
```

### Docker

```bash
docker-compose up -d
```

### Windows 任务计划

```
采集：每天 07:00、15:00、23:00  →  python task1_collector.py
报告：每天 00:10                 →  python task2_reporter.py
```

---

## 自动化部署

通过 GitHub Actions 实现全自动化，无需本地常驻进程。

### 工作流一览

| 工作流 | 文件 | 触发时间（北京时间） | 执行内容 |
|--------|------|---------------------|----------|
| 新闻采集 | `collect.yml` | 07:00（采集+报告）、15:00、23:00（纯采集） | `task1_collector.py` |
| 报告生成 | `report.yml` | 00:00 | `task2_reporter.py --no-email` |
| 邮件推送 | `send_email.yml` | 08:30 | `send_email.py` |

### GitHub Secrets 配置

仓库 → Settings → Secrets → Actions，添加以下 Secret：

```
ARK_API_KEY         豆包 API Key（必填）
DEEPSEEK_API_KEY    DeepSeek API Key
QWEN_API_KEY        通义千问 API Key
DASHSCOPE_API_KEY   DashScope API Key
SMTP_HOST           邮件服务器地址
SMTP_PORT           邮件端口（通常 465）
SMTP_USER           发件人邮箱
SMTP_PASSWORD       邮件密码 / 授权码
EMAIL_TO            收件人邮箱
```

### 数据持久化

GitHub Actions 通过 `actions/cache` 缓存 `data/` 目录（含 SQLite 数据库），确保历史数据在每次运行间保持。报告文件通过 `actions/upload-artifact` 在工作流间传递。

---

## 输出说明

### 简要报告（`reports/{date}/brief/*.md`）

- 当日市场数据仪表盘（汇率、主要指数、大宗商品、利率）
- TOP 10 新闻（按 `final_score` 排序）
- 每条含：中文标题、来源、5W1H 摘要、各维度评分

### 深度报告（`reports/{date}/depth/*.pdf`）

每个活跃领域一份，包含：
1. 领域综述与核心信号
2. 历史关联事件（**全文向量索引B**：基于 original_article 而非标题）
3. TOP5 事件深度分析（**原文获取 + 动态阈值 + unified_score**）
4. 投资 / 决策建议

### 数据库（`data/news.db`）

SQLite，主要表结构：

#### `news` 表（处理后新闻）

| 字段 | 说明 |
|------|------|
| `title` / `translated_title` | 原标题 / 中文翻译 |
| `summary` | 100 字摘要 |
| `who/what/when_time/where_place/why/how` | 5W1H 分析 |
| `domain` | 领域分类（政治/经济/科技/军事/社会/文化/体育/娱乐） |
| `source_score` | 信源权威性（0–10） |
| `influence_score` | 事件影响力（LLM 评分） |
| `value_score` | 决策价值（LLM 评分） |
| `heat_score` | 热榜匹配热度 |
| `final_score` | 综合评分（25–84） |
| `pub_date` | 发布时间 |
| `source_name` | 信源名称 |
| `raw_news_id` | 关联原始数据 ID |

#### `raw_news` 表（原始数据追溯）

| 字段 | 说明 |
|------|------|
| `id` | 自增主键 |
| `news_id` | 新闻唯一标识（MD5） |
| `raw_json` | 原始 JSON 数据 |
| `source_name` | 来源名称 |
| `fetched_at` | 采集时间 |
| `processed` | 处理状态（0=未处理/被过滤，1=已入库） |

**原始数据追溯**：每条新闻采集后立即存入 `raw_news` 表，入库成功后更新 `processed=1`。被过滤的新闻保留 `processed=0`，便于问题排查和数据恢复。

---

## 常见问题

**Q：运行 task2 后没有报告输出？**
确认 task1 已成功写入数据库：`python -c "from core.storage.database import get_db; db=get_db(); print(db.get_stats())"`。task2 直接从 SQLite 读取，无中间文件依赖。

**Q：BGE-M3 相关模块报错？**
系统自动降级：`faiss` / `sentence-transformers` 不可用时，热度评分降级 TF-IDF，历史关联降级 TF-IDF，主流程不受影响。

**Q：原文获取失败会影响深度报告吗？**
不会。原文获取失败时，系统自动降级到使用 RSS 摘要（content 字段）进行深度分析，不影响报告生成。

**Q：全文向量索引B与标题向量索引A的区别？**
- 索引A（history_relation_engine_bge3）：用于事件聚类、HOT10查询，输入为 title embedding
- 索引B（history_relation_engine_fulltext）：用于深度分析历史关联，输入为 original_article embedding
两者完全独立，互不影响。

**Q：动态阈值是如何工作的？**
动态阈值 = max(绝对底线0.3, 百分位阈值)。系统先计算所有候选的 unified_score，再根据数据分布自动调整阈值，过滤低质量匹配。宁可少而精，不可用低质量凑数。

**Q：某个领域的深度报告没有生成？**
当日该领域新闻数量低于阈值时跳过。可在 `sources.yaml` 开启更多相关信源，或调整 `core/config/core_config.yaml` 中的最小条数配置。

**Q：邮件发送失败？**
运行 `python send_email.py` 单独测试。检查 SMTP 配置，Gmail 需使用应用专用密码，国内邮箱需开启 SMTP 服务并获取授权码。

**Q：Windows 路径报错？**
所有路径统一通过 `core/config/loader.py` 的 `PROJECT_ROOT` 计算，兼容 Windows / Linux / macOS。不要使用硬编码绝对路径。

**Q：想在本地添加新信源？**
编辑 `sources.yaml`，按已有格式添加条目，设置 `enabled: true`。无需重启，下次 task1 运行时自动生效。
