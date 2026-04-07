# News Analyzer

基于 AI 的新闻采集与分析系统，服务**投资分析、制度掌握、科技发展**三大决策方向。

每日自动完成：多信源采集 → AI 解析评分 → 简报 + 深度报告 → 邮件推送。

**最后更新**：2026-04-07 | **架构**：单一数据路径（SQLite） | **运行环境**：GitHub Actions + 本地 Windows/Linux

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
| `task1_collector.py` | 采集主入口，12 步流水线，写入 SQLite | 每天 3 次 |
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
│ Step 1   全信源采集（增量模式）           │
│          └─ 采集后立即存入 raw_news 表   │
│ Step 2   字段规范化（FieldNormalizer）    │
│ Step 3   存储原始数据（raw_news 表）      │
│ Step 4   轻量级分类（8 类，置信度≥0.7 时填充 domain） │
│          └─ 关键词 + RSS category 映射，无外部依赖
│ Step 5   基础三层过滤                    │
│          ├─ 信源白名单校验               │
│          ├─ 可信度过滤                   │
│          └─ 历史去重（DB 批量查询）      │
│ Step 6   合并 LLM（单次 API 调用）       │
│          翻译 + 摘要 + 5W1H + 5 维评分  │
│          └─ 熔断器：连续 3 次致命错误后跳过剩余批次
│ Step 7   数据完整性校验（前置）          │
│          ├─ 校验通过 → passed            │
│          └─ 校验失败 → force_stored + 默认值填充
│ Step 8   向量化生成（BGE-M3，passed + force_stored）│
│ Step 9   热度评分（仅 passed 数据）      │
│ Step 10  批量事务写入 SQLite             │
│          └─ 更新 raw_news.processed=1   │
│ Step 11  force_stored 修复（已简化）     │
│          └─ 不再自动修复，保留数据降权处理
│ Step 12  清理过期原始数据（>7天）         │
│          └─ 删除 raw_news 中 processed=1 的历史记录
└──────────────────┬──────────────────────┘
                   │
                   ▼  data/news.db（单一权威数据源）
┌─────────────────────────────────────────┐
│ task2_reporter.py（每天 1 次）           │
│                                         │
│ 阶段 1  DB 读取近 24h 新闻              │
│ 阶段 2  记录新闻数量                    │
│ 阶段 3  生成简要报告（TOP10，按评分排序）│
│         └─ 直接使用 task1 产出的翻译摘要 │
│ 阶段 4  生成深度报告（按领域）           │
│         ├─ 事件聚类 → TOP5              │
│         ├─ 原文获取（article_fetcher）   │
│         ├─ 全文向量关联（BGE-M3 索引B）  │
│         └─ 深度分析                     │
│ 阶段 5  发送邮件                        │
└──────────────────┬──────────────────────┘
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
│     └─ 其他 → force_stored + 默认值填充 → 向量化 → 存储     │
│                                                              │
│  AI处理失败（熔断器/单条失败）                                │
│     └─ 记录 WARNING 日志，数据不存入 news 表                 │
│                                                              │
│  最终状态:                                                   │
│     passed        → 正常参与 Task2 报告生成                  │
│     force_stored  → 保留数据，查询时降权处理                 │
└─────────────────────────────────────────────────────────────┘
```

### AI 熔断器机制

当 LLM 服务出现致命错误（401/403 认证失败、账户欠费等）时，系统自动进入熔断状态：

| 阶段 | 行为 |
|------|------|
| 连续 1-2 次致命错误 | 记录错误，继续尝试下一批次 |
| 连续 3 次致命错误 | 熔断器断开，跳过剩余所有批次 |
| 恢复后下次运行 | 熔断器自动重置 |

**设计目的**：避免在 LLM 服务不可用时浪费整个 240 分钟超时窗口（如 166 个批次全部重试失败）。

### 评分体系

| 字段 | 含义 | 来源 |
|------|------|------|
| `source_score` | 信源权威性（Tier 1/2/3 映射） | 规则 |
| `influence_score` | 事件影响力 | LLM |
| `value_score` | 决策价值 | LLM |
| `heat_score` | 热榜向量匹配热度 | BGE-M3 |
| `final_score` | 综合得分 | `source×0.25 + influence×0.25 + value×0.25 + heat×0.25` |

---

## 项目结构

```
news_analyzer/
├── task1_collector.py          采集主入口（12 步流水线）
├── task2_reporter.py           报告主入口（双轨输出）
├── send_email.py               邮件重发工具
├── sources.yaml                RSS 信源配置（Tier 1/2/3，45 KB）
├── requirements.txt            Python 依赖
├── .env                        环境变量（本地，不入库）
├── .env.example                环境变量示例
│
├── core/
│   ├── collector/
│   │   ├── collector.py            UnifiedRSSCollector + RSSSourceManager
│   │   ├── sources.py              信源定义与 Tier 管理
│   │   └── crawlers/               定向爬虫
│   │
│   ├── filters/
│   │   ├── source_validator.py     信源白名单校验
│   │   ├── content_filter.py       内容质量过滤
│   │   └── deduplication.py        哈希去重
│   │
│   ├── processor/
│   │   ├── combined_processor.py       单次 LLM 合并处理 + 熔断器
│   │   ├── content_parser.py           RuleBasedParser + EntityExtractor
│   │   ├── field_normalizer.py         字段标准化
│   │   ├── lightweight_classifier.py   轻量级领域分类
│   │   ├── heat_processor.py           BGE-M3 热度向量匹配
│   │   ├── data_validator.py           校验 + AI 补救 + 默认值填充
│   │   ├── history_relation_engine_bge3.py  BGE-M3 历史关联引擎（索引A）
│   │   ├── history_relation_engine_fulltext.py  BGE-M3 全文关联引擎（索引B）
│   │   └── generators/
│   │       └── report_generator.py    简报 + 深度报告双轨生成
│   │
│   ├── storage/
│   │   └── database.py             NewsDatabase + NewsData（SQLite 主库）
│   │
│   ├── config/
│   │   ├── manager.py              统一配置管理器
│   │   ├── loader.py               环境变量加载（兼容新旧格式）
│   │   ├── core_config.yaml        核心运行配置
│   │   └── report_templates.yaml   报告模板
│   │
│   └── utils/
│       ├── email_sender.py         SMTP 邮件（支持 465/SMTP_SSL + 587/STARTTLS）
│       ├── md2pdf.py               Markdown → PDF（中文字体自动检测）
│       ├── workflow_timer.py       各阶段耗时追踪
│       ├── task_lock.py            跨平台文件锁
│       ├── heartbeat.py            心跳监控
│       ├── incremental_tracker.py  增量采集状态持久化
│       └── source_scorer.py        信源评分映射
│
├── .github/workflows/
│   ├── collect.yml              采集 + 报告（07:00）+ 补充采集（15:00/23:00）
│   └── send_email.yml           邮件推送（08:30）
│
├── data/                        SQLite 数据库 + 增量状态
├── reports/                     输出报告
├── logs/                        运行日志
└── tests/                       测试套件
```

---

## 快速开始

### 环境要求

- Python 3.9+
- 至少一个 AI API Key

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
python -c "from core.config import get_project_root; print(get_project_root())"
python -c "from core.storage.database import get_db; db=get_db(); print(db.get_stats())"
```

---

## 配置说明

### `.env` 关键变量

```bash
# ── AI 模型（新格式，推荐）──────────────────────────────
AI_ANALYSIS_PROVIDER=deepseek
AI_ANALYSIS_MODEL=deepseek-reasoner
AI_ANALYSIS_KEY=             # DeepSeek API Key
AI_ANALYSIS_BASE_URL=https://api.deepseek.com/v1

AI_FILTER_PROVIDER=doubao
AI_FILTER_MODEL=doubao-seed-2-0-mini-260215
AI_FILTER_KEY=               # 豆包 API Key（必填）
AI_FILTER_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# ── 旧格式（向后兼容）─────────────────────────────────
DEEPSEEK_API_KEY=            # 等同于 AI_ANALYSIS_KEY

# ── 热榜 API（可选）─────────────────────────────────────
HOTBOARD_API_KEY=

# ── 邮件推送（可选）─────────────────────────────────────
SMTP_HOST=smtp.example.com
SMTP_PORT=465                # 支持 465（SMTP_SSL）和 587（STARTTLS）
SMTP_USER=
SMTP_PASSWORD=
EMAIL_TO=recipient@example.com

# ── 报告配置（可选）─────────────────────────────────────
ENABLE_INVESTMENT_ANALYSIS=false
AI_BATCH_SIZE=4
```

### `sources.yaml` 信源分层

```
Tier 1  核心骨架（必采）  路透社、BBC、新华社、央视等
Tier 2  区域支柱          各国主要媒体
Tier 3  专业补充          行业垂直媒体
```

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
pytest tests/unit/ -v        # 单元测试
pytest tests/integration/ -v # 集成测试
```

### Docker

```bash
docker-compose up -d
```

---

## 自动化部署

通过 GitHub Actions 实现全自动化，无需本地常驻进程。

### 工作流一览

| 工作流 | 文件 | 触发时间（北京时间） | 执行内容 |
|--------|------|---------------------|----------|
| 新闻采集 | `collect.yml` | 07:00（采集+报告）、15:00、23:00（纯采集） | `task1_collector.py` + `task2_reporter.py` |
| 邮件推送 | `send_email.yml` | 08:30 | `send_email.py` |

### GitHub Secrets 配置

仓库 → Settings → Secrets → Actions，添加以下 Secret：

```
AI_ANALYSIS_KEY     DeepSeek API Key（深度分析模型）
AI_FILTER_KEY       豆包 API Key（快速筛选模型，必填）
SMTP_HOST           邮件服务器地址
SMTP_PORT           邮件端口（465 或 587）
SMTP_USER           发件人邮箱
SMTP_PASSWORD       邮件密码 / 授权码
EMAIL_TO            收件人邮箱（多个用逗号分隔）
```

### CI 环境优化

| 优化项 | 说明 |
|--------|------|
| pip 缓存 | `~/.cache/pip` 按 requirements.txt 哈希缓存 |
| HuggingFace 缓存 | `~/.cache/huggingface` 缓存 BGE-M3 模型（~2GB） |
| 中文字体 | 自动安装 `fonts-wqy-microhei` 确保 PDF 正常渲染 |
| HF 镜像 | CI 环境使用官方 `huggingface.co`（非中国镜像） |
| 熔断器 | LLM 致命错误时快速跳过，避免浪费超时窗口 |

### 数据持久化

- **数据库**：通过 `actions/cache` 缓存 `data/` 目录，历史数据在每次运行间保持
- **报告**：通过 `actions/upload-artifact` 在工作流间传递
- **BGE-M3 模型**：首次运行下载后缓存，后续运行直接使用

---

## 输出说明

### 简要报告（`reports/{date}/brief/*.md`）

- 当日市场数据仪表盘（汇率、主要指数、大宗商品、利率）
- TOP 10 新闻（按 `final_score` 排序）
- 每条含：中文标题、来源、5W1H 摘要、各维度评分

### 深度报告（`reports/{date}/depth/*.pdf`）

每个活跃领域一份，包含：
1. 领域综述与核心信号
2. 历史关联事件（全文向量索引B）
3. TOP5 事件深度分析
4. 投资 / 决策建议

### 数据库（`data/news.db`）

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
| `final_score` | 综合评分 |
| `embedding` | BGE-M3 向量（1024 维 float32） |
| `combined_processing_status` | 处理状态：passed / force_stored |
| `validation_status` | 校验状态 |

#### `raw_news` 表（原始数据追溯）

| 字段 | 说明 |
|------|------|
| `news_id` | 新闻唯一标识（MD5） |
| `raw_json` | 原始 JSON 数据 |
| `source_name` | 来源名称 |
| `fetched_at` | 采集时间 |
| `processed` | 0=被过滤，1=已入库 |

原始数据保留 7 天后自动清理（Step 12）。

---

## 常见问题

**Q：运行 task2 后没有报告输出？**
确认 task1 已成功写入数据库：`python -c "from core.storage.database import get_db; db=get_db(); print(db.get_stats())"`。task2 直接从 SQLite 读取。

**Q：BGE-M3 相关模块报错？**
系统自动降级：`faiss` / `sentence-transformers` 不可用时，热度评分和历史关联降级为 TF-IDF，主流程不受影响。

**Q：原文获取失败会影响深度报告吗？**
不会。原文获取失败时，系统自动降级到使用 RSS 摘要进行深度分析。

**Q：邮件发送失败？**
1. 检查 `.env` 中 `EMAIL_TO`（非 `EMAIL_RECIPIENTS`）是否正确
2. `SMTP_PORT=465` 使用 SMTP_SSL，`SMTP_PORT=587` 使用 STARTTLS，系统自动适配
3. Gmail 需使用应用专用密码，国内邮箱需获取授权码

**Q：LLM 服务不可用时会发生什么？**
熔断器会在连续 3 次致命错误（认证失败、账户欠费等）后自动跳过剩余批次，避免浪费超时时间。非致命错误（限流、超时）不触发熔断。下次运行时熔断器自动重置。

**Q：想在本地添加新信源？**
编辑 `sources.yaml`，按已有格式添加条目，设置 `enabled: true`。无需重启，下次 task1 运行时自动生效。
