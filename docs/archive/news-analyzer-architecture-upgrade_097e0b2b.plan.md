---
name: news-analyzer-architecture-upgrade
overview: 基于现有 News Analyzer 第一版，从第一性原理重新梳理核心需求，对采集→解析→存储→分析→报告的全链路做架构升级规划，重点围绕“规则优先的 5W1H/内容/标签抽取 + RSS 字段差异处理 + SQLite 健壮化”，并为后续实体/历史关联与投资分析预留扩展点。
todos:
  - id: review-rss-and-parser
    content: 只读评估 rss 采集与解析模块（collector/parser/sources）以对齐规则优先中间层需求。
    status: completed
  - id: design-parsing-rules-yaml
    content: 设计 parsing_rules.yaml 的结构与代表性源示例，统一 5W1H/内容/标签抽取配置。
    status: completed
  - id: design-rulebased-parser
    content: 设计 RuleBasedParser + AIFallbackExtractor 的接口与核心流程。
    status: completed
  - id: design-db-wal-retry-backup
    content: 设计 NewsDatabase 层面的 WAL/重试/备份封装与使用规范。
    status: completed
  - id: design-entities-schema
    content: 设计 entities 与 news_entities 表结构、索引与迁移策略。
    status: completed
  - id: design-entity-extractor-and-history
    content: 规划 EntityExtractor 与 HistoryRelationEngine 的接口与基本查询模式。
    status: completed
  - id: design-chart-data-service
    content: 规划 ChartDataService 聚合层，为报告与图表提供标准数据结构。
    status: completed
isProject: false
---

## 目标与第一性原理梳理

- **核心使用目的**：每天用最少时间获得“可用于决策的新闻情报”，服务三大长期方向：**投资分析、制度掌握、科技发展**，而不是简单“看新闻”。
- **本质需求拆解**：
  - **输入侧**：多源 RSS 新闻 → 需要解决“能抓到、抓得准、字段结构统一”。
  - **理解侧**：对每条新闻形成结构化表征（5W1H + 内容要点 + 标签/领域 + 多维评分），且**可复现、可解释**，不能只靠大模型自由发挥。
  - **记忆/关联侧**：在时间维度和实体维度上，把新闻“串起来”，支撑历史关联和趋势洞察（为知识图谱做铺垫）。
  - **输出侧**：简要 + 深度双报告，能快速筛选重点事件，并给出有据可依的分析和对比。
- **本轮迭代 focus（按你选择的“平衡但偏向规则 + SQLite 健壮化”）**：
  1. **规则优先的解析中间层**：先把“RSS 字段差异 + 5W1H/内容/标签抽取”做成可配置、可回放的规则层，AI 只做兜底和增强。
  2. **SQLite 健壮化，但不过度工程**：先落地 WAL、重试、备份和简单访问约束，不立刻引入独立写入服务。
  3. **历史关联与图表做最小可用集（MVP）**：基于现有表结构 + 轻量级 `entities/news_entities` 预留，做出一条“从实体到历史新闻 + 简单趋势图”的端到端路径即可。

---

## 高层架构与模块职责规划

可以用“分层 + 中间层”的视角重构当前结构（保留现有目录大框架）：

```mermaid
flowchart TD
  subgraph ingestionLayer [采集层]
    rssCollector[RSSCollector]
    sourcesManager[SourcesManager]
  end

  subgraph parsingLayer [解析中间层]
    ruleEngine[RuleBasedParser]
    aiFallback[AIFallbackExtractor]
    rulesRepo[ParsingRulesYAML]
  end

  subgraph storageLayer [存储层]
    dbManager[NewsDatabase(SQLite+WAL)]
    entitiesTable[Entities]
    newsEntitiesTable[NewsEntities]
  end

  subgraph analysisLayer [分析层]
    fiveW1HAnalyzer[FiveW1H+Scoring]
    historyEngine[HistoryRelationEngine]
    entityExtractor[EntityExtractor]
  end

  subgraph reportLayer [报告层]
    briefReport[BriefReportGenerator]
    depthReport[DepthReportGenerator]
    chartModule[ChartDataService]
  end

  rssCollector --> parsingLayer
  sourcesManager --> rssCollector
  parsingLayer --> dbManager
  dbManager --> analysisLayer
  analysisLayer --> reportLayer
```

- **采集层（rss/**）**：负责从多源 RSS 拉取“原始 item 数据 + 元信息”，不关心 5W1H/标签；对不同源的字段差异只做“最小标准化”（如 `title/link/published/summary/raw_content`）。
- **解析中间层（新）**：
  - `ParsingRulesYAML`：以 YAML 为核心的规则仓库，对不同源/域/语言定义字段映射、正文提取、5W1H 抽取策略、标签规则等。
  - `RuleBasedParser`：统一入口：先按规则解析 → 标记解析方式（规则 / AI / 混合） → 输出结构化对象。
  - `AIFallbackExtractor`：当规则缺失或置信度低时，再调用 AI 做补充/校正；把 AI 输出连同原文和规则结果都存库。
- **存储层（storage/**）**：
  - 在现有 `news` 表基础上，扩展用于“可解释性”和“来源质量”的字段（如 `source_reliability_score/extraction_method/access_time/raw_item_json`）。
  - 预留 `entities` 与 `news_entities` 两张表，只先建表与索引，不强行填充数据。
  - `NewsDatabase` 负责 WAL、连接复用、重试和备份调度的封装。
- **分析层（filters/**, processors/**）**：
  - 把 5W1H、五维评分、标签、历史关联、实体抽取视为**“在结构化数据上的算法模块”**，而不是“在 RSS item 上临时处理”。
  - `EntityExtractor` 第一阶段可以返回空列表，但接口、数据流和调用路径要打通。
  - `HistoryRelationEngine` 增加基于实体/标签/领域的多维关联查询接口，配合图表模块。
- **报告层（generators/** + utils/**）**：
  - `report_generator.py` 中显式依赖“结构化查询接口”，而不是自己写散落的 SQL。
  - 新增 `ChartDataService`（可在 `generators/` 或 `processors/`），专门聚合统计数据给图表/表格使用。

---

## 规则优先 5W1H / 内容 / 标签抽取设计

### 1. YAML 规则模板设计要点

- **规则粒度**：以“源 + 频道/域”为最小粒度，例如 `source_id`（路透-国际）、`domain`（经济）组合；允许继承与 override，避免重复。
- **覆盖字段**：
  - **源级元数据**：可信度、默认领域、语言、是否启用、备选 RSS 地址等。
  - **内容抽取**：如何从 RSS 字段/HTML 中抽取正文（XPath/CSS/正则）、如何处理多语言、如何清洗噪声。
  - **5W1H 抽取**：可配置简单规则（如基于日期/地点正则、标题模板），并指定哪些字段强制交给 AI。
  - **标签与领域**：基于关键词/正则的规则标签，支持多标签；若不满足规则，则降级交由 AI。
- **示例片段（规划层面）**：
  - `parsing_rules.yaml` 中为每个源定义：`match` 匹配条件（host/路径/语言）、`mapping` 字段映射、`content` 正文选择器、`heuristics` 简单规则、`ai_overrides` 何时触发 AI。

### 2. RSS 源字段差异处理思路

- **统一“内部标准字段集合”**：至少包括 `source_id/source_name/title/link/published/raw_summary/raw_content/language/domain/tags_raw` 等。
- **采集时只做“轻标准化”**：
  - 比如对 Google News, RSSHub, 官方 RSS、Atom、JSON feed 统一映射到上述内部字段，不做 5W1H/标签判断。
  - 对每条 item 附带 `raw_item_json`（或压缩后的 JSON），便于后续回放和规则调试。
- **解析中间层负责“深标准化”**：
  - 通过 `RuleBasedParser` + `ParsingRulesYAML`，把内部标准字段转换为 `news` 表所需的 5W1H/标签/评分输入。
  - 对于缺字段的源，规则可以声明“必需字段缺失时直接走 AI 补全”。

### 3. 规则 vs AI 的协同策略

- **优先规则**：
  - 标题结构固定（如“【领域】事件名：后缀说明”）的源，优先用规则拆 5W1H/标签。
  - 对于时间/地点/机构等，可用正则 + 词典优先识别，并给出置信度。
- **AI 兜底与校正**：
  - 若规则得分 < 阈值（如 0.7），则把原始文本 + 规则结果作为 prompt 上下文，让 AI 只做“校验/补全/纠错”。
  - AI 输出需要结构化（JSON），并记录在 `news` 表对应字段或辅助字段中。
- **存储可解释性**：
  - 新增 `extraction_method` 字段（枚举：`rule_only/ai_fallback/ai_only`）。
  - 可选：增加 `extraction_trace` JSON 字段，按需持久化规则命中和 AI 决策摘要。

---

## SQLite 健壮化与数据架构预留

### 1. SQLite 使用策略（第一阶段）

- **连接与 WAL 策略**：
  - 在 `NewsDatabase` 初始化时统一设置 `PRAGMA journal_mode=WAL;`，并根据需要启用 `synchronous=NORMAL` 以平衡性能和安全。
  - 尽量通过**连接池/单例**复用连接，减少频繁打开关闭。
- **访问模式约束**：
  - 保持“采集任务为写重、报告任务为读重”的分离，避免同时在多个进程大量写入。
  - 通过简单约定（如脚本执行时间错峰 + GitHub Actions/Windows 任务时间表）控制并发层面风险。
- **重试机制**：
  - 在所有写路径（插入/更新）统一封装重试逻辑，捕获 `sqlite3.OperationalError`（`database is locked` 等），随机 sleep 后重试最多 N 次。
- **备份策略**：
  - 在采集/报表关键任务结束后，触发一次数据库备份（复制 `data/news.db` 至带时间戳的文件），并限定保留天数。

### 2. 轻量级知识图谱预留

- **新表 `entities`（实体表）**：
  - 字段规划：`id/name/type/subtype/normalized_name/created_at/updated_at` 等。
  - 索引：`(name, type)` 组合索引便于查找，“type+normalized_name” 用于去重。
- **新表 `news_entities`（新闻-实体关联表）**：
  - 字段规划：`id/news_id/entity_id/role/weight/extra/created_at` 等。
  - 索引：`news_id` 单列索引（从新闻查实体）、`entity_id` 单列索引（从实体查新闻），后续可拓展联合索引。
- **第一阶段实现边界**：
  - 只创建表和索引，以及基础 DAO 接口，不强制在采集/分析流程中写入实体。
  - `EntityExtractor` 可以暂时实现为“空实现 + 简单日志”，但对外暴露的接口与调用点要完整。

---

## 历史关联与图表的最小可用路径（MVP）

- **关联维度 MVP**：
  - 第一阶段可主要基于：**实体（若有）、标签、领域（政治/经济/科技）、时间窗口** 来做历史查询。
  - 若实体尚未填充，可先使用“领域 + 标签 + 关键词”组合做伪实体关联。
- **图表/对比 MVP**：
  - 选 1~2 个关键指标（如“某领域近 30 天新闻数量/提及频次”），通过一个 `ChartDataService` 提供聚合数据（时间序列、柱状统计）。
  - 在 PDF 报告中先以简单表格 + 一张趋势图的形式嵌入即可，不追求炫酷可视化。

---

## 分阶段实施计划（只做到架构与复杂逻辑层面的设计）

### 阶段一：规则优先解析 + SQLite 健壮化 + 轻量图谱预留

- **子目标**：
  - 有一个稳定可靠的“解析中间层”，能在至少 3~5 个重点 RSS 源上表现明显优于纯 AI。
  - SQLite 不再因调试或多次运行脚本而轻易损坏，具备基本的重试与备份能力。
  - 数据库结构中已经包含实体/关联表，未来实体抽取可以无痛接入。
- **关键设计任务（偏复杂逻辑/架构，计划后续由我具体实现）**：
  - 抽象 `RuleBasedParser`、`ParsingRulesYAML` 以及 `AIFallbackExtractor` 的接口与数据模型。
  - 在 `NewsDatabase` 中设计统一的连接管理、WAL 初始化、重试与备份接口。
  - 设计 `entities/news_entities` 表结构与索引方案、DAO 接口以及如何与现有 `News` 模型集成。
  - 规划 `sources.yaml` 与 `parsing_rules.yaml` 之间的关系与扩展点（例如，用 `source_id` 打通两者）。
- **相对简单、准备通过“开发文档/指导”给你，而非直接改代码的内容**：
  - 如何为新源编写 YAML 规则（模式模板 + 示例）。
  - 如何调试和迭代规则（比如通过“重放某天的原始 RSS 数据”）。
  - 具体的 Windows/GitHub Actions 调度参数调整说明。

### 阶段二：实体抽取 + 更完整的历史关联与可视化

- **子目标**：
  - `EntityExtractor` 至少在一个领域（如经济）开始落地产出实体数据，能支撑从“公司/技术”到相关新闻的查询。
  - `HistoryRelationEngine` 能基于实体/标签/领域组合输出一个“简明历史时间线 + 基本统计图表”。
- **关键设计任务**：
  - 设计 `EntityExtractor` 接口（输入：新闻结构化数据；输出：实体列表 + 置信度/角色），以及与 AI 调用策略（何时触发、prompt 结构）。
  - 在 `history_relation_engine.py` 中规划面向报告的查询接口（如 `get_entity_timeline`、`get_domain_trend` 等）。
  - 设计 `ChartDataService` 聚合层，抽象出给报告模板使用的标准数据结构。
- **通过“指导文档”完成的部分**：
  - 如何构造评测集来评估实体抽取质量。
  - 如何调整阈值和规则来平衡召回率和准确率。

### 阶段三：可扩展基础设施与投资分析模块

- **子目标**：
  - 依据未来实际负载与需求，决定是否引入 PostgreSQL 或图数据库，并提供迁移/同步方案。
  - 在已有实体与历史关系基础上，引入简单的投资分析模板（如产业链梳理、政策传导路径等）。
- **关键设计任务**：
  - 抽象存储访问层（Repository/DAO），使得从 SQLite 切换到 PostgreSQL 不改变上层逻辑。
  - 规划若引入 Neo4j 时的实体/关系建模方案及同步策略。
  - 设计 `ENABLE_INVESTMENT_ANALYSIS` 等功能开关的配置策略（环境变量 + 配置文件 + 代码路径）。

---

## 后续由我直接落地的“核心代码与架构调整”范围

> 遵守你的约束：**实际操作阶段只改核心复杂逻辑和架构**，其它通过文档与指导先行。

- **会直接改动/新增的核心模块**（在你确认计划后）：
  - `RuleBasedParser` / 解析中间层的核心类与接口（含与 `rss/parser.py`、`filters/ai_filter_agent.py` 的集成方式）。
  - `NewsDatabase` 的连接管理、WAL/重试/备份封装与 `models/data_models.py` 的对接。
  - `entities` 与 `news_entities` 的数据模型和最小 DAO 接口，以及在 `history_relation_engine.py` 中预留的查询路径。
  - `ChartDataService` 的核心查询聚合逻辑（不含具体图表渲染库集成细节）。
- **暂时仅通过文档/指导输出的部分**：
  - YAML 规则编写手册、常见 RSS 源字段差异说明与应对策略。
  - Windows/GitHub Actions 自动化细节、报警与监控建议。
  - 投资分析模板的写作框架与 prompt 设计思路。

---

## TODO 概览（后续具体实现前的任务清单）

- **理解与梳理现状**：
  - 对现有 `rss/collector.py`、`rss/parser.py`、`filters/ai_filter_agent.py`、`storage/database.py`、`generators/report_generator.py` 做一次针对“规则优先 & SQLite 健壮化”的结构评估（只读分析）。
- **设计输出物**：
  - 给出 `parsing_rules.yaml` 的详细字段设计与 2~3 个典型源的完整示例。
  - 设计 `RuleBasedParser` / `AIFallbackExtractor` / `EntityExtractor` / `ChartDataService` 的接口草图与关键伪代码。
  - 设计 `entities/news_entities` 表结构、索引与迁移策略（含如何兼容现有 `news.db`）。
  - 规划 SQLite WAL + 重试 + 备份的封装接口与调用规范。

在你确认这个架构级计划后，我可以按你的工具调用次数与“只改核心复杂逻辑”的约束，进一步细化到具体文件级的改造方案和开发顺序。