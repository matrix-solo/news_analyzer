# 新闻分析系统工作流架构说明

> 本文档面向后端开发与测试人员，详细说明系统各模块的运转逻辑、兜底措施和异常处理机制。

---

## 目录

1. [系统架构概览](#1-系统架构概览)
2. [核心工作流](#2-核心工作流)
3. [模块详解](#3-模块详解)
4. [数据流转](#4-数据流转)
5. [兜底与容错机制](#5-兜底与容错机制)
6. [配置体系](#6-配置体系)
7. [定时任务调度](#7-定时任务调度)
8. [数据库设计](#8-数据库设计)
9. [API与接口](#9-api与接口)
10. [测试与调试](#10-测试与调试)

---

## 1. 系统架构概览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           定时调度层                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  Task1 Collector │    │  Task2 Reporter  │    │  Task3 Cleanup   │  │
│  │  (每日3次采集)    │    │  (每日1次报告)    │    │  (定期清理)       │  │
│  └────────┬─────────┘    └────────┬─────────┘    └──────────────────┘  │
└───────────┼───────────────────────┼─────────────────────────────────────┘
            │                       │
            ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           业务逻辑层                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ RSS采集器   │  │ 过滤器链    │  │ AI处理器    │  │ 报告生成器  │   │
│  │ (多源fallback)│ │ (三层过滤)  │  │ (多provider)│  │ (模板引擎)  │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
            │                       │
            ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           数据存储层                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ SQLite DB   │  │ ChromaDB    │  │ 文件存储    │  │ 状态跟踪    │   │
│  │ (WAL模式)   │  │ (向量存储)  │  │ (报告/日志) │  │ (JSON状态)  │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

| 原则 | 说明 | 实现方式 |
|------|------|----------|
| **容错优先** | 任何模块失败都有兜底方案 | 多级fallback、默认值、降级处理 |
| **增量采集** | 避免重复采集，节省资源 | 基于pub_date的智能回溯 |
| **事务安全** | 数据一致性保证 | SQLite事务、批量操作、重试机制 |
| **可观测性** | 全链路日志追踪 | 结构化日志、心跳检测、统计报告 |

---

## 2. 核心工作流

### 2.1 Task1: 高频新闻采集工作流

**触发时机**: 每日3次（07:00、15:00、23:00）

**执行流程**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Task1 采集工作流                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    ▼                               ▼                               ▼
┌─────────┐                   ┌─────────┐                   ┌─────────┐
│ 阶段1   │                   │ 阶段2   │                   │ 阶段3   │
│ 全信源  │                   │ 基础    │                   │ AI内容  │
│ 新闻采集│ ─────────────────▶│ 三层过滤│ ─────────────────▶│ 属性校验│
└─────────┘                   └─────────┘                   └─────────┘
    │                               │                               │
    │ • RSS多源fallback            │ • 白名单校验                  │ • 5W1H检测
    │ • 增量采集过滤               │ • 可信度校验                  │ • 事实性判断
    │ • 遗漏检测                   │ • 历史去重                    │ • 五维评分
    │ • 补救采集                   │ • 垃圾内容清理                │ • 领域分类
    │                               │                               │
    ▼                               ▼                               ▼
┌─────────┐                   ┌─────────┐                   ┌─────────┐
│ 阶段4   │                   │ 阶段5   │                   │ 阶段6   │
│ 批量    │                   │ 兜底    │                   │ 数据库  │
│ 存入DB  │ ─────────────────▶│ 重新判断│ ─────────────────▶│ 备份    │
└─────────┘                   └─────────┘                   └─────────┘
    │                               │                               │
    │ • 事务安全写入                │ • 高级模型重判                │ • 在线备份
    │ • FTS5自动同步                │ • 更新/拒绝处理               │ • 可选关闭
    │ • 实体抽取(可选)              │                               │
    │                               │                               │
    └───────────────────────────────┴───────────────────────────────┘
                                    │
                                    ▼
                            ┌─────────────┐
                            │ 统计报告    │
                            │ 日志保存    │
                            └─────────────┘
```

**详细阶段说明**:

#### 阶段1: 全信源新闻采集

```python
# 执行逻辑伪代码
for source in enabled_sources:
    # 1. 智能回溯计算
    cutoff_date = incremental_tracker.get_intelligent_cutoff_date(source.name)
    
    # 2. RSS多级fallback采集
    feed = rss_collector.fetch_feed(source)  # 官方 → RSSHub → Google News → 第三方
    
    # 3. 增量过滤
    for item in feed.items:
        if item.pub_date < cutoff_date:
            continue  # 跳过旧新闻
        all_news.append(item)
    
    # 4. 遗漏检测
    gap_result = detect_gap_for_source(source.name, feed, collected_count)
    
    # 5. 补救采集（如果检测到遗漏）
    if gap_result.has_gap and gap_result.gap_type == 'rss_rollover':
        remedial_news = 补救采集(source, gap_result)
        all_news.extend(remedial_news)
```

#### 阶段2: 基础三层过滤

| 过滤层 | 检查内容 | 通过条件 | 日志输出 |
|--------|----------|----------|----------|
| 白名单校验 | source_name 是否在白名单 | `source_validator.validate_source()` 返回 passed | `过滤1-白名单: N → M` |
| 可信度校验 | credibility 字段 | `credibility in ['高', '中高']` | `过滤2-可信度: N → M` |
| 历史去重 | news_id 是否已处理 | `news_id not in processed_ids` | `过滤3-历史去重: N → M` |
| 垃圾清理 | 内容长度和模式 | `len(content) >= 50 and not is_spam(content)` | `过滤4-垃圾清理: N → M` |

#### 阶段3: AI内容属性校验

```python
# AI批处理逻辑
for batch in chunks(news_list, batch_size=4):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            results = ai_filter.check_fact_batch(batch)
            break
        except Exception as e:
            if attempt == max_retries - 1:
                # 兜底处理：整批标记为"待分类"
                for news in batch:
                    news['domain'] = '待分类'
                    news['needs_recheck'] = True
                    passed_news.append(news)
            else:
                time.sleep(2 ** attempt)  # 指数退避
```

**AI校验输出字段**:

| 字段 | 说明 | 来源 |
|------|------|------|
| `is_factual` | 是否为事实性新闻 | AI判断 |
| `w5h1_score` | 5W1H完整度得分(0-6) | AI分析 |
| `domain` | 领域分类 | 规则优先 → RSS分类 → AI判断 |
| `tags` | 标签列表 | 规则优先 → AI兜底 |
| `final_score` | 最终评分(0-100) | 五维评分加权 |
| `translated_title` | 翻译后标题 | AI翻译 |
| `short_summary` | 简短摘要 | AI生成 |

#### 阶段4: 批量存入数据库

```python
# 事务安全的批量插入
with db.transaction() as conn:
    cursor = conn.cursor()
    cursor.executemany(INSERT_NEWS_SQL, news_dicts)
    cursor.executemany(INSERT_PROCESSED_SQL, processed_dicts)
```

**关键特性**:
- 使用 `executemany` 提高性能
- 事务失败自动回滚
- FTS5全文索引通过触发器自动同步
- 支持连接池和WAL模式

#### 阶段5: 兜底重新判断

当AI批处理失败时，新闻会被标记为"待分类"并存入数据库。阶段5会使用更高级的模型重新判断：

```python
# 使用ANALYSIS模型重新判断
analysis_provider = ai_processor.get_provider("ANALYSIS")
for news in fallback_news:
    result = analysis_provider.chat(build_recheck_prompt(news))
    if result.is_factual and result.w5h1_score >= 3:
        update_news_after_recheck(news, result)
    else:
        mark_news_as_rejected(news)
```

### 2.2 Task2: 每日深度分析报告工作流

**触发时机**: 每日00:10运行一次

**执行流程**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Task2 报告工作流                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    ▼                               ▼                               ▼
┌─────────┐                   ┌─────────┐                   ┌─────────┐
│ 阶段1   │                   │ 阶段2   │                   │ 阶段3   │
│ 读取    │                   │ 最终    │                   │ 生成    │
│ 待分析池│ ─────────────────▶│ 冗余去重│ ─────────────────▶│ 简要报告│
└─────────┘                   └─────────┘                   └─────────┘
    │                               │                               │
    │ • 加载pool目录                │ • AI去重检测                  │ • 中国TOP N
    │ • 加载24h内归档               │ • 保留代表性新闻              │ • 国外TOP N
    │ • 按发布时间筛选              │                               │
    │                               │                               │
    ▼                               ▼                               ▼
┌─────────┐                   ┌─────────┐                   ┌─────────┐
│ 阶段4   │                   │ 阶段5   │                   │ 阶段6   │
│ 生成    │                   │ 选择    │                   │ 发送    │
│ 深度报告│ ─────────────────▶│ TOP N   │ ─────────────────▶│ 邮件    │
└─────────┘                   └─────────┘                   └─────────┘
    │                               │                               │
    │ • 按领域聚类                   │ • 按final_score排序          │ • 简要版正文
    │ • 历史关联分析                │ • 取TOP N                    │ • 深度版附件
    │ • RAG增强洞察                │                               │
    │ • 领域整体分析                │                               │
    │                               │                               │
    ▼                               ▼                               ▼
┌─────────┐                   ┌─────────┐                   ┌─────────┐
│ 阶段7   │                   │          │                   │         │
│ 归档    │                   │          │                   │         │
│ 待分析池│                   │          │                   │         │
└─────────┘                   └──────────┘                   └─────────┘
```

**深度报告生成逻辑**:

```python
for domain in ['政治', '经济', '科技', '其他']:
    domain_news = [n for n in all_news if n.domain == domain]
    
    # 1. 事件聚类
    clusters = ai_processor.cluster_events(domain_news)
    
    # 2. 历史关联分析
    history_engine = HistoryRelationEngine(history_news)
    related = history_engine.find_related_news(current_news)
    
    # 3. RAG增强洞察
    rag_context = rag_retriever.retrieve_for_event(event_summary)
    
    # 4. 深度分析
    insight = depth_analyzer.analyze(news, related_history, rag_context)
    
    # 5. 领域整体分析
    overview = ai_processor.generate_domain_overview(domain, clusters)
```

---

## 3. 模块详解

### 3.1 RSS采集模块 (rss/)

#### 3.1.1 RSSSourceManager

**职责**: 管理RSS源配置，从 `sources.yaml` 加载源信息

**核心数据结构**:

```python
@dataclass
class RSSSource:
    name: str                    # 源名称
    type: str                    # domestic/international
    category: str                # central/news_agency/comprehensive等
    region: str                  # 地区
    credibility: str             # 可信度: 高/中高/中/低
    urls: Dict[str, str]         # 多源URL映射
    enabled: bool = True         # 是否启用
```

**源URL优先级**:

```
官方RSS → RSSHub → Google News → 第三方聚合
```

#### 3.1.2 RSSCollector

**核心方法**: `fetch_feed(source, max_retries=3)`

**多级Fallback机制**:

```python
def fetch_feed(self, source: RSSSource) -> Optional[RSSFeed]:
    url_priority = ['official', 'rsshub', 'google_news', 'third_party']
    
    for url_type in url_priority:
        url = source.urls.get(url_type)
        if not url:
            continue
            
        for attempt in range(max_retries):
            try:
                response = http_client.get(url, timeout=30)
                feed = self.parser.parse(response.text)
                feed.used_source_type = url_type
                return feed
            except Exception as e:
                logger.warning(f"获取失败 [{url_type}]: {e}")
                continue
    
    return None  # 所有源都失败
```

**关键属性**:

| 属性 | 说明 |
|------|------|
| `feed.used_backup` | 是否使用了备用源 |
| `feed.used_source_type` | 实际使用的源类型 |
| `feed.items` | 解析后的新闻条目列表 |

### 3.2 过滤模块 (filters/)

#### 3.2.1 SourceValidator

**职责**: 白名单校验，验证源是否可信

**配置来源**: `sources.yaml` 中所有启用的源

```python
def validate_source(self, source_name: str) -> ValidationResult:
    if source_name in self.whitelist:
        return ValidationResult(passed=True, source=source_name)
    return ValidationResult(passed=False, reason="不在白名单")
```

#### 3.2.2 AIFilterAgent

**职责**: AI内容属性校验，包括5W1H检测、事实性判断、五维评分

**核心方法**: `check_fact_batch(news_list)`

**五维评分体系**:

| 维度 | 字段名 | 说明 | 权重 |
|------|--------|------|------|
| 信源权威性 | `source_score` | 来源可信度 | 20% |
| 影响力 | `influence_score` | 影响范围 | 25% |
| 热度 | `heat_score` | 时效性/关注度 | 20% |
| 价值 | `value_score` | 信息价值 | 25% |
| 合规扣分 | `compliance_deduction` | 合规性扣分 | 10% |

**最终评分计算**:

```python
final_score = (
    source_score * 0.20 +
    influence_score * 0.25 +
    heat_score * 0.20 +
    value_score * 0.25 -
    compliance_deduction
) * 10
```

**5W1H检测输出**:

```python
w5h1_analysis = {
    'who': '事件主体',
    'what': '事件内容',
    'when': '事件时间',
    'where': '事件地点',
    'why': '事件原因',
    'how': '事件方式'
}
w5h1_score = sum(1 for v in w5h1_analysis.values() if v)  # 0-6分
```

### 3.3 处理模块 (processors/)

#### 3.3.1 AIProcessor

**职责**: 统一AI调用接口，支持多provider

**Provider配置**:

| 用途 | 环境变量前缀 | 说明 |
|------|-------------|------|
| ANALYSIS | `AI_ANALYSIS_*` | 深度分析模型（高级） |
| FILTER | `AI_FILTER_*` | 快速筛选模型（经济） |
| BACKUP | `AI_BACKUP_*` | 备用模型 |

**核心方法**:

```python
def get_provider(self, purpose: str = "ANALYSIS") -> Optional[BaseProvider]:
    """获取指定用途的AI Provider"""
    config = self._get_provider_config(purpose)
    if config.get('key'):
        return self._create_provider(config)
    return None

def generate_event_insight(self, news, related_history, rag_context):
    """生成事件洞察"""
    provider = self.get_provider("ANALYSIS")
    return provider.chat(build_insight_prompt(news, related_history, rag_context))
```

#### 3.3.2 RuleBasedParser

**职责**: 基于YAML规则的领域/标签提取

**配置文件**: `config/parsing_rules.yaml`

**提取逻辑**:

```yaml
domains:
  政治:
    keywords: ["政府", "政策", "选举", "外交"]
    patterns: ["*政府*", "*政策*"]
  经济:
    keywords: ["股市", "金融", "经济", "投资"]
    patterns: ["*股市*", "*金融*"]
```

**优先级**: 规则命中 > RSS分类 > AI判断

#### 3.3.3 HistoryRelationEngine

**职责**: 历史关联分析，查找相关历史新闻

**算法**: TF-IDF + 实体加权 + 时间衰减

**权重分配**:
- 融合相似度（TF-IDF + 实体）: 70%
- 时间关联度: 30%

**时间分类**:

| 时间范围 | 类型 | 基础分 |
|----------|------|--------|
| 0-7天 | 本周关联 | 1.0 |
| 7-30天 | 近期关联 | 0.7 |
| 30-90天 | 历史背景 | 0.3 |

### 3.4 存储模块 (storage/)

#### 3.4.1 NewsDatabase

**职责**: SQLite数据库管理，事务安全操作

**关键特性**:
- WAL模式提高并发性能
- 连接池支持（默认5个连接）
- 事务上下文管理器
- FTS5全文搜索自动同步

**核心方法**:

```python
# 单条插入（事务安全）
def insert_news_with_processed(self, news: NewsData) -> bool:
    with self.transaction() as conn:
        # 检查存在
        # 插入新闻
        # 标记已处理
        # 自动提交或回滚

# 批量插入（性能优化）
def insert_news_batch(self, news_list: List[NewsData]) -> int:
    with self.transaction() as conn:
        cursor.executemany(INSERT_NEWS_SQL, news_dicts)
        cursor.executemany(INSERT_PROCESSED_SQL, processed_dicts)

# 写操作重试封装
def _execute_with_retry(self, conn, sql, params, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return cursor.execute(sql, params)
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                raise
```

**数据库表结构**:

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `news` | 新闻主表 | id, title, domain, score, 5W1H字段 |
| `processed_news` | 去重基线表 | news_id, processed_at |
| `rejected_news` | 拒绝新闻表 | news_id, reject_reason, reject_type |
| `event_clusters` | 事件聚类表 | cluster_date, domain, event_name, news_ids |
| `news_fts` | FTS5全文索引 | title, content, keywords, tags |

### 3.5 报告生成模块 (generators/)

#### 3.5.1 ReportGenerator

**职责**: 生成简要摘要报告和深度分析报告

**模板系统**: `config/report_templates.yaml`

**报告目录结构**:

```
reports/
└── 2026-03-15/
    ├── brief/
    │   ├── daily_report_2026-03-15_120000.md
    │   └── daily_report_2026-03-15_120000.pdf
    └── depth/
        ├── daily_report_depth_政治_2026-03-15_120000.md
        ├── daily_report_depth_经济_2026-03-15_120000.md
        └── daily_report_depth_科技_2026-03-15_120000.md
```

**中国/国外新闻判断逻辑**:

```python
def _is_china_news(self, news: Dict) -> bool:
    source = self.source_manager.get_source(news['source_name'])
    if source:
        if '中国' in source.region:
            return True
        if source.type == 'domestic':
            return True
    return False
```

### 3.6 知识库模块 (knowledge/)

#### 3.6.1 RAGRetriever

**职责**: RAG检索，为深度分析提供历史上下文

**检索流程**:

```python
def retrieve_for_event(self, event_summary, event_entities, domain_filter):
    # 1. 生成查询向量
    query_embedding = embedding_service.get_single_embedding(event_summary)
    
    # 2. 向量检索
    results = knowledge_base.search_by_embedding(query_embedding, top_k=20)
    
    # 3. 时间衰减
    results = apply_time_decay(results)
    
    # 4. 过滤低分
    results = [r for r in results if r.score >= min_score]
    
    # 5. 构建上下文
    return build_context(results[:top_k])
```

**时间衰减公式**:

```python
def calculate_time_decay(pub_date):
    days_diff = (now - pub_date).days
    if days_diff <= 0:
        return 1.0
    elif days_diff >= time_decay_days * 3:
        return 0.3
    else:
        return exp(-days_diff / time_decay_days)
```

### 3.7 工具模块 (utils/)

#### 3.7.1 IncrementalTracker

**职责**: 增量采集状态跟踪

**状态文件**: `data/collection_state.json`

**智能回溯策略**:

| 中断时长 | 策略 | 回溯计算 |
|----------|------|----------|
| ≤1小时 | 保守回溯 | 1小时 |
| 1-6小时 | 线性回溯 | 中断时长 + 1小时 |
| 6-24小时 | 激进回溯 | min(中断时长 × 1.5, 36小时) |
| 24-72小时 | 深度回溯 | min(中断时长 + 12, 96小时) |
| >72小时 | 保守深度 | 72小时（受RSS滚动限制） |

**RSS滚动限制**:

| 源类型 | 滚动限制 | 说明 |
|--------|----------|------|
| 通讯社 | 24小时 | 新闻滚动最快 |
| 中央媒体 | 96小时 | 滚动最慢 |
| 财经媒体 | 48小时 | 中等滚动 |
| 综合媒体 | 48小时 | 默认值 |

#### 3.7.2 CollectionConfigManager

**职责**: 采集配置管理，遗漏检测

**遗漏检测逻辑（基于RSS滚动边界）**:

```python
def detect_gap(self, source_name, db_latest, rss_earliest, rss_latest):
    """
    核心原理：
    RSS源会滚动，旧新闻会被"挤出"。
    RSS feed中最后一条（最早发布的）新闻，就是RSS源当前能提供的最早新闻。
    
    如果 db_latest >= rss_earliest：无遗漏
    如果 db_latest < rss_earliest：存在遗漏
    """
    if db_latest >= rss_earliest:
        return {'has_gap': False, 'gap_type': 'none'}
    else:
        time_gap = (rss_earliest - db_latest).hours
        return {
            'has_gap': True,
            'gap_type': 'rss_rollover',
            'time_gap_hours': time_gap
        }
```

#### 3.7.3 TaskLock

**职责**: 任务锁机制，防止定时任务冲突

**跨平台支持**:
- Unix/Linux: 使用 `fcntl` 文件锁
- Windows: 使用文件存在性检查 + 进程检测

**使用方式**:

```python
# 方式1: 上下文管理器
with task_lock('collect', timeout=3600):
    run_collection()

# 方式2: 手动控制
lock = TaskLock('collect', timeout=3600)
if lock.acquire(blocking=False):
    try:
        run_collection()
    finally:
        lock.release()
```

**锁超时检测**: 超过 `timeout` 秒的锁视为失效，会被自动清理

---

## 4. 数据流转

### 4.1 新闻数据流转图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  RSS Feed   │ ──▶ │  RSS Item   │ ──▶ │  News Dict  │ ──▶ │  NewsData   │
│  (原始XML)  │     │  (解析后)   │     │  (处理中)   │     │  (最终存储) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                   │                   │
                           ▼                   ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                    │ • title     │     │ + news_id   │     │ + 5W1H字段  │
                    │ • link      │     │ + domain    │     │ + score字段 │
                    │ • pub_date  │     │ + tags      │     │ + extraction│
                    │ • content   │     │ + rule_parse│     │   _method  │
                    └─────────────┘     └─────────────┘     └─────────────┘
```

### 4.2 字段映射关系

| 阶段 | 字段名 | 来源 | 说明 |
|------|--------|------|------|
| RSS解析 | `title` | RSS item | 原始标题 |
| RSS解析 | `content` | RSS item | 原始内容 |
| 规则解析 | `domain` | RuleBasedParser | 规则提取的领域 |
| 规则解析 | `tags` | RuleBasedParser | 规则提取的标签 |
| AI校验 | `translated_title` | AI翻译 | 翻译后标题 |
| AI校验 | `final_score` | AI评分 | 最终评分 |
| AI校验 | `who/what/when/where/why/how` | AI分析 | 5W1H要素 |
| 数据库 | `score_timeliness` | `heat_score` | 时效性评分 |
| 数据库 | `score_importance` | `influence_score` | 重要性评分 |
| 数据库 | `score_credibility` | `source_score` | 可信度评分 |
| 数据库 | `score_impact` | `value_score` | 影响力评分 |

### 4.3 待分析池流转

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Task1 采集     │     │  analysis_pool  │     │  Task2 报告     │
│  (存入pool)     │ ──▶ │  (待分析池)     │ ──▶ │  (读取+归档)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  archive_pool   │
                        │  (归档池)       │
                        │  保留90天       │
                        └─────────────────┘
```

**文件命名规则**:
- 待分析池: `pool_YYYY-MM-DD.json`
- 归档池: `pool_YYYY-MM-DD_YYYY-MM-DD_HHMMSS.json`

---

## 5. 兜底与容错机制

### 5.1 RSS采集兜底

| 场景 | 兜底措施 | 日志标识 |
|------|----------|----------|
| 官方RSS不可达 | 尝试RSSHub | `used_source_type: rsshub` |
| RSSHub不可达 | 尝试Google News | `used_source_type: google_news` |
| 所有源都失败 | 跳过该源，记录警告 | `采集信源失败: {source_name}` |

### 5.2 AI处理兜底

| 场景 | 兜底措施 | 日志标识 |
|------|----------|----------|
| AI批处理失败 | 标记为"待分类"，存入数据库 | `[FALLBACK] 批处理失败` |
| AI判断失败 | 标记为"待分类"，后续重判 | `[FALLBACK] 判断失败` |
| AI重判失败 | 保持"待分类"状态 | `[RECHECK ERROR]` |
| 领域提取失败 | 默认"其他" | `domain: 其他` |
| 标签提取失败 | 空列表 | `tags: []` |

### 5.3 数据库兜底

| 场景 | 兜底措施 | 实现 |
|------|----------|------|
| 写入被锁 | 指数退避重试(最多3次) | `_execute_with_retry` |
| 事务失败 | 自动回滚 | `transaction()` 上下文管理器 |
| 连接池耗尽 | 创建新连接 | `ConnectionPool.get_connection` |

### 5.4 遗漏补救机制

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  遗漏检测       │ ──▶ │  补救采集       │ ──▶ │  效果验证       │
│  (RSS滚动边界)  │     │  (扩大回溯)     │     │  (重新检测)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
  gap_score计算          扩大至RSS滚动限制       gap_score对比
  (0-1分数)              增加采集条目数          判断补救效果
```

**补救结果分类**:
- ✅ 补救成功: 遗漏分数降为0
- ⚠️ 部分补救: 遗漏分数降低但未归零
- ❌ 补救失败: 遗漏分数未改善

---

## 6. 配置体系

### 6.1 配置文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| 环境变量 | `.env` | API密钥、代理等敏感配置 |
| 源配置 | `sources.yaml` | RSS源列表和属性 |
| AI配置 | `config/ai_providers.yaml` | AI模型配置 |
| 解析规则 | `config/parsing_rules.yaml` | 领域/标签提取规则 |
| 报告模板 | `config/report_templates.yaml` | 报告生成模板 |
| 知识库配置 | `config/knowledge.yaml` | RAG配置 |

### 6.2 环境变量配置

**AI模型配置**:

```bash
# 深度分析模型（高级）
AI_ANALYSIS_PROVIDER=deepseek
AI_ANALYSIS_MODEL=deepseek-chat
AI_ANALYSIS_KEY=sk-xxx
AI_ANALYSIS_BASE_URL=https://api.deepseek.com/v1

# 快速筛选模型（经济）
AI_FILTER_PROVIDER=qwen
AI_FILTER_MODEL=qwen-turbo
AI_FILTER_KEY=sk-xxx
AI_FILTER_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# 备用模型
AI_BACKUP_PROVIDER=openai
AI_BACKUP_MODEL=gpt-3.5-turbo
AI_BACKUP_KEY=sk-xxx
```

**功能开关**:

```bash
# 增量采集（默认开启）
ENABLE_INCREMENTAL_COLLECTION=true

# 实体抽取（默认关闭）
ENABLE_ENTITY_EXTRACTION=false

# 数据库备份（默认开启）
ENABLE_DB_BACKUP=true

# 投资分析（默认关闭）
ENABLE_INVESTMENT_ANALYSIS=false

# AI标签兜底（默认关闭）
ENABLE_AI_TAG_FALLBACK=false
```

**批处理配置**:

```bash
# AI批处理大小
AI_BATCH_SIZE=4

# AI批处理最大重试次数
AI_BATCH_MAX_RETRIES=3
```

### 6.3 配置加载顺序

```
1. 代码默认值（最低优先级）
      ↓
2. 全局配置文件（.env / config.yaml）
      ↓
3. 源级别配置（sources.yaml）
      ↓
4. 运行时参数（最高优先级）
```

---

## 7. 定时任务调度

### 7.1 任务时间表

| 任务 | 触发时间 | 执行频率 | 超时时间 |
|------|----------|----------|----------|
| Task1 采集 | 07:00, 15:00, 23:00 | 每日3次 | 1小时 |
| Task2 报告 | 00:10 | 每日1次 | 2小时 |
| Task3 清理 | 03:00 | 每日1次 | 30分钟 |

### 7.2 任务锁机制

**锁文件位置**: `data/locks/{task_name}.lock`

**锁文件内容**:

```
PID: 12345
Time: 2026-03-15T07:00:00
Timeout: 3600
```

**冲突处理**:
- 如果锁文件存在且未过期 → 跳过本次执行
- 如果锁文件存在但已过期 → 清理失效锁，继续执行

### 7.3 心跳检测

**心跳文件位置**: `data/heartbeat.json`

**心跳内容**:

```json
{
  "task": "collect",
  "status": "running",
  "progress": 50,
  "message": "阶段3：AI内容属性校验",
  "updated_at": "2026-03-15T07:05:30"
}
```

---

## 8. 数据库设计

### 8.1 核心表结构

**news 表**:

```sql
CREATE TABLE news (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    translated_title TEXT,
    link TEXT,
    source TEXT,
    source_name TEXT,
    pub_date DATETIME,
    content TEXT,
    summary TEXT,
    
    -- 5W1H
    who TEXT,
    what TEXT,
    when_time TEXT,
    where_place TEXT,
    why TEXT,
    how TEXT,
    
    -- 分类
    domain TEXT,
    tags TEXT,          -- JSON数组
    keywords TEXT,      -- JSON数组
    
    -- 评分
    score REAL,
    score_timeliness REAL,
    score_importance REAL,
    score_credibility REAL,
    score_impact REAL,
    
    -- 扩展字段
    source_reliability_score REAL,
    extraction_method TEXT DEFAULT 'unknown',
    raw_item_json TEXT,
    access_time DATETIME,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**索引**:

```sql
CREATE INDEX idx_pub_date ON news(pub_date);
CREATE INDEX idx_created_at ON news(created_at);
CREATE INDEX idx_domain ON news(domain);
CREATE INDEX idx_score ON news(score);
CREATE INDEX idx_source ON news(source);
CREATE INDEX idx_extraction_method ON news(extraction_method);
```

### 8.2 FTS5全文索引

```sql
CREATE VIRTUAL TABLE news_fts USING fts5(
    title,
    translated_title,
    content,
    keywords,
    tags,
    content='news',
    content_rowid='rowid'
);
```

**自动同步触发器**:
- `news_fts_insert`: INSERT后自动插入FTS
- `news_fts_update`: UPDATE后自动更新FTS
- `news_fts_delete`: DELETE后自动删除FTS

### 8.3 数据库迁移

**自动迁移字段**:

```python
migrations = [
    ("source_reliability_score", "ALTER TABLE news ADD COLUMN source_reliability_score REAL"),
    ("extraction_method", "ALTER TABLE news ADD COLUMN extraction_method TEXT DEFAULT 'unknown'"),
    ("raw_item_json", "ALTER TABLE news ADD COLUMN raw_item_json TEXT"),
    ("access_time", "ALTER TABLE news ADD COLUMN access_time DATETIME"),
]
```

**迁移逻辑**: 启动时检查字段是否存在，不存在则添加

---

## 9. API与接口

### 9.1 内部模块接口

**RSS采集接口**:

```python
from rss import RSSCollector, RSSSourceManager

# 获取启用的源
manager = RSSSourceManager()
sources = manager.get_enabled_sources()

# 采集单个源
collector = RSSCollector()
feed = collector.fetch_feed(source)
```

**AI处理接口**:

```python
from processors.ai_processor import AIProcessor

processor = AIProcessor()

# 获取指定用途的provider
analysis_provider = processor.get_provider("ANALYSIS")
filter_provider = processor.get_provider("FILTER")

# 生成事件洞察
insight = processor.generate_event_insight(news, related_history)

# 聚类事件
clusters = processor.cluster_events(domain_news, persist=True)
```

**数据库接口**:

```python
from storage.database import NewsDatabase, get_db

db = get_db()

# 批量插入
stored = db.insert_news_batch(news_data_list)

# 查询最近新闻
recent = db.get_recent_news(hours=24)

# 按领域查询
domain_news = db.search_by_domain("政治", hours=24)

# 关键词搜索
results = db.search_by_keywords(["经济", "政策"], days=30)
```

### 9.2 状态查询接口

**增量采集状态**:

```python
from utils.incremental_tracker import get_incremental_tracker

tracker = get_incremental_tracker()

# 获取源的最后采集时间
last_time = tracker.get_last_collection_time(source_name)

# 获取中断时长
downtime = tracker.get_downtime_hours(source_name)

# 获取智能截止日期
cutoff = tracker.get_intelligent_cutoff_date(source_name)

# 获取状态报告
report = tracker.get_state_report()
```

**任务锁状态**:

```python
from utils.task_lock import check_lock_status

status = check_lock_status('collect')
# {'locked': True, 'status': '运行中', 'pid': '12345', 'time': '...'}
```

---

## 10. 测试与调试

### 10.1 单元测试入口

各模块都支持独立运行测试：

```bash
# RSS模块测试
python -m rss.collector

# 过滤模块测试
python -m filters.ai_filter_agent

# 数据库模块测试
python -m storage.database

# 增量跟踪测试
python -m utils.incremental_tracker

# 配置模块测试
python -m config.loader
```

### 10.2 调试日志

**日志文件位置**: `logs/task1_collect_YYYY-MM-DD.log`, `logs/task2_report_YYYY-MM-DD.log`

**日志级别配置**:

```bash
LOG_LEVEL=DEBUG  # 详细调试日志
LOG_LEVEL=INFO   # 正常运行日志
LOG_LEVEL=WARNING  # 仅警告和错误
```

**关键日志标识**:

| 标识 | 含义 |
|------|------|
| `[PASS]` | AI校验通过 |
| `[REJECT]` | AI校验拒绝 |
| `[FALLBACK]` | 兜底处理 |
| `[RECHECK PASS]` | 重新判断通过 |
| `[RECHECK REJECT]` | 重新判断拒绝 |
| `⚠️` | 警告信息 |
| `🔧` | 补救采集 |
| `✅` | 成功/正常 |
| `❌` | 失败/异常 |

### 10.3 常见问题排查

**问题1: 采集量为0**

排查步骤:
1. 检查网络连接和代理配置
2. 检查RSS源是否可访问
3. 查看日志中的 `采集信源失败` 信息
4. 检查增量采集是否过滤了所有新闻

**问题2: AI批处理失败**

排查步骤:
1. 检查API密钥是否正确
2. 检查API配额是否用尽
3. 检查网络连接
4. 查看日志中的具体错误信息

**问题3: 数据库写入失败**

排查步骤:
1. 检查磁盘空间
2. 检查文件权限
3. 查看是否有 `database is locked` 错误
4. 检查WAL文件是否存在

**问题4: 报告生成失败**

排查步骤:
1. 检查待分析池是否有数据
2. 检查AI模型是否可用
3. 检查reports目录权限
4. 查看日志中的具体错误

### 10.4 性能监控

**关键指标**:

| 指标 | 正常范围 | 异常处理 |
|------|----------|----------|
| 单次采集时间 | <10分钟 | 检查网络/源数量 |
| AI批处理延迟 | <5秒/批 | 检查API响应 |
| 数据库写入 | <1秒/100条 | 检查WAL模式 |
| 报告生成时间 | <5分钟 | 检查AI模型 |

**性能日志示例**:

```
[PERF] RSS采集耗时: 45.2s (50个源)
[PERF] AI批处理耗时: 12.3s (32条新闻)
[PERF] 数据库写入耗时: 0.8s (28条)
[PERF] 报告生成耗时: 180.5s (3个领域)
```

---

## 附录

### A. 错误码对照表

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| E001 | RSS源不可达 | 检查网络/使用备用源 |
| E002 | AI API调用失败 | 检查密钥/配额 |
| E003 | 数据库锁定 | 等待重试/检查并发 |
| E004 | 配置文件缺失 | 创建配置文件 |
| E005 | 任务锁冲突 | 等待当前任务完成 |

### B. 版本兼容性

| 组件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Python | 3.8 | 3.10+ |
| SQLite | 3.25 | 3.35+ (FTS5) |
| ChromaDB | 0.4.0 | 最新 |

### C. 相关文档

- [README.md](../README.md) - 用户使用指南
- [sources.yaml](../sources.yaml) - RSS源配置
- [config/](../config/) - 配置文件目录
