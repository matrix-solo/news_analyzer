# 新闻分析工作流架构说明文档 V2.0

> **文档用途**: 项目工作流运转逻辑说明，用于后端测试、开发使用  
> **文档版本**: V2.0  
> **最后更新**: 2026-03-15  
> **覆盖范围**: 全项目所有模块（约160个文件）

---

## 目录

1. [系统架构概览](#1-系统架构概览)
2. [核心工作流](#2-核心工作流)
3. [RSS采集工作流](#3-rss采集工作流)
4. [过滤与校验工作流](#4-过滤与校验工作流)
5. [处理与解析工作流](#5-处理与解析工作流)
6. [存储工作流](#6-存储工作流)
7. [报告生成工作流](#7-报告生成工作流)
8. [知识库工作流](#8-知识库工作流)
9. [工具与配置](#9-工具与配置)
10. [兜底与容错机制](#10-兜底与容错机制)
11. [数据流转](#11-数据流转)
12. [配置体系](#12-配置体系)
13. [定时任务调度](#13-定时任务调度)
14. [数据库设计](#14-数据库设计)
15. [API与接口](#15-api与接口)
16. [测试与调试](#16-测试与调试)

---

## 1. 系统架构概览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           新闻分析工作流系统                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        入口层 (Entry Points)                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │run_collect.py│  │run_report.py │  │send_email.py │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      核心工作流层 (Core Workflow)                     │   │
│  │                                                                     │   │
│  │   Task1NewsCollector          Task2DailyReporter                   │   │
│  │   ├─ 6阶段采集工作流          ├─ 7阶段报告工作流                    │   │
│  │   ├─ RSS多源采集              ├─ 待分析池加载                       │   │
│  │   ├─ AI内容校验               ├─ 深度分析生成                       │   │
│  │   └─ 数据库存储               └─ 邮件发送                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      功能模块层 (Functional Modules)                  │   │
│  │                                                                     │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │   │
│  │  │  RSS采集     │ │  过滤校验    │ │  处理解析    │ │  知识库    │ │   │
│  │  │  (rss/)      │ │  (filters/)  │ │  (processors)│ │  (knowledge)│   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │   │
│  │                                                                     │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │   │
│  │  │  爬虫        │ │  存储        │ │  报告生成    │ │  商业化    │ │   │
│  │  │  (crawlers/) │ │  (storage/)  │ │  (generators)│ │  (commercial)│  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      基础设施层 (Infrastructure)                      │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │   │
│  │  │  数据模型    │ │  配置管理    │ │  工具函数    │ │  测试      │ │   │
│  │  │  (models/)   │ │  (config/)   │ │  (utils/)    │ │  (tests/)  │ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 模块职责矩阵

| 模块 | 核心职责 | 关键文件 |
|------|---------|---------|
| **入口层** | 任务调度入口 | `run_collect.py`, `run_report.py`, `send_email.py` |
| **核心工作流** | Task1采集、Task2报告 | `task1_collector.py`, `task2_reporter.py` |
| **RSS采集** | 多源RSS采集、增量采集 | `rss/collector.py`, `rss/sources.py` |
| **过滤校验** | 白名单、AI校验、去重 | `filters/ai_filter_agent.py` |
| **处理解析** | AI处理、规则解析 | `processors/ai_processor.py` |
| **知识库** | RAG检索、向量存储 | `knowledge/retriever.py`, `knowledge/chroma_store.py` |
| **爬虫** | 国内媒体抓取 | `crawlers/xinhua.py`, `crawlers/people.py` |
| **存储** | SQLite数据库、文件管理 | `storage/database.py` |
| **报告生成** | Markdown/PDF报告 | `generators/report_generator.py` |
| **商业化** | Web界面、订阅管理 | `commercial/web/app.py` |

### 1.3 关键技术栈

| 类别 | 技术 | 版本/说明 |
|------|------|----------|
| **编程语言** | Python | 3.9+ |
| **AI模型** | DeepSeek / Doubao / Qwen | OpenAI兼容接口 |
| **向量数据库** | ChromaDB | 0.4.0+ |
| **向量模型** | BGE-M3 / MiniLM | 1024d / 384d |
| **数据库** | SQLite | WAL模式 |
| **Web框架** | Flask | 商业版 |
| **CI/CD** | GitHub Actions | 定时触发 |
| **容器化** | Docker / Docker Compose | 可选部署 |

---

## 2. 核心工作流

### 2.1 Task1采集工作流

#### 2.1.1 触发时机

| 时间 | 类型 | 说明 |
|------|------|------|
| 07:00 (北京时间) | 主任务 | 采集+生成报告 |
| 15:00 (北京时间) | 补充采集 | 仅采集 |
| 23:00 (北京时间) | 补充采集 | 仅采集 |

#### 2.1.2 6阶段工作流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Task1 采集工作流（6阶段）                          │
└─────────────────────────────────────────────────────────────────────────┘

阶段1: 全信源新闻采集
    │
    ├─ 从所有启用的RSS源采集
    ├─ 支持增量采集（ENABLE_INCREMENTAL_COLLECTION）
    ├─ 智能回溯计算（基于中断时长）
    ├─ 遗漏检测与补救采集
    └─ 输出: 原始新闻列表

阶段2: 基础三层过滤
    │
    ├─ 过滤1: 白名单校验（source_validator.validate_source）
    ├─ 过滤2: 可信度校验（credibility in ['高', '中高']）
    ├─ 过滤3: 历史去重（批量查询优化N+1问题）
    ├─ 过滤4: 垃圾内容清理（内容长度>=50，非spam）
    └─ 输出: 过滤后新闻列表

阶段3: AI内容属性校验
    │
    ├─ 5W1H检测（何人、何事、何时、何地、何因、如何）
    ├─ 事实性判断（is_factual）
    ├─ 五维评分（source/influence/heat/value/compliance）
    ├─ 领域分类（规则优先 > RSS分类 > AI推断）
    ├─ 标签提取（规则命中优先，AI兜底）
    ├─ 翻译处理（原文+译文）
    └─ 输出: AI校验通过/拒绝/待分类

阶段4: 批量存入数据库（事务安全）
    │
    ├─ 批量插入（executemany优化性能）
    ├─ 事务保证原子性
    ├─ FTS5全文索引自动同步
    ├─ 实体抽取（ENABLE_ENTITY_EXTRACTION）
    ├─ 数据库备份（ENABLE_DB_BACKUP）
    └─ 输出: 存储成功计数

阶段5: 重新判断"待分类"新闻
    │
    ├─ 使用高级模型（ANALYSIS provider）重新判断
    ├─ 更新领域、标签、评分
    ├─ 或标记为拒绝
    └─ 输出: 重判结果

阶段6: 统计与日志
    │
    ├─ 打印采集统计
    ├─ 保存AI处理日志
    └─ 输出: 完整统计信息
```

#### 2.1.3 核心类：Task1NewsCollector

**文件**: `task1_collector.py`

| 属性/方法 | 说明 | 默认值 |
|-----------|------|--------|
| `MIN_CONTENT_LENGTH` | 最小内容长度 | 50字符 |
| `MAX_PER_SOURCE` | 每源最大条目数 | 10 |
| `ai_batch_size` | AI批处理大小 | 4（环境变量AI_BATCH_SIZE） |
| `enable_incremental` | 增量采集开关 | True |
| `run(max_per_source)` | 主执行方法 | - |
| `_collect_from_sources()` | 阶段1：采集 | - |
| `_apply_basic_filters()` | 阶段2：基础过滤 | - |
| `_apply_ai_filter()` | 阶段3：AI校验 | - |
| `_store_batch_to_database()` | 阶段4：存储 | - |
| `_recheck_fallback_news()` | 阶段5：兜底重判 | - |

#### 2.1.4 统计指标

| 指标 | 说明 |
|------|------|
| `total_collected` | 总采集数 |
| `whitelist_passed` | 白名单通过数 |
| `credibility_passed` | 可信度通过数 |
| `history_passed` | 历史去重通过数 |
| `content_passed` | 内容清理通过数 |
| `ai_passed` | AI校验通过数 |
| `stored` | 成功存储数 |
| `incremental_filtered` | 增量过滤数 |
| `remedial_count` | 补救采集数 |
| `remedial_success` | 补救成功数 |

---

### 2.2 Task2报告工作流

#### 2.2.1 触发时机

| 时间 | 说明 |
|------|------|
| 00:10 (北京时间) | 每日报告生成 |
| 08:30 (北京时间) | 邮件发送 |

#### 2.2.2 7阶段工作流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Task2 报告工作流（7阶段）                          │
└─────────────────────────────────────────────────────────────────────────┘

阶段1: 读取待分析池
    │
    ├─ 读取data/analysis_pool/目录
    ├─ 读取data/archive_pool/近24小时归档
    ├─ 按发布时间筛选（过去24小时）
    ├─ 去重（基于news_id）
    └─ 输出: 待分析新闻列表 + 采集日期集合

阶段2: 最终冗余去重
    │
    ├─ AI去重检测（check_duplicates）
    ├─ 保留代表性新闻
    └─ 输出: 去重后新闻列表

阶段3: 生成简要摘要报告
    │
    ├─ 中国TOP N + 国外TOP N
    ├─ 简洁排版（适合移动端）
    ├─ Markdown格式
    └─ 输出: 简要报告文件路径

阶段4: 生成深度分析报告
    │
    ├─ 加载历史新闻（近90天）
    ├─ 按领域聚类（政治/经济/科技）
    ├─ 历史关联分析
    ├─ RAG增强洞察
    ├─ 领域整体分析
    ├─ 生成PDF附件
    └─ 输出: 深度报告文件列表

阶段5: 选择TOP N
    │
    ├─ 按final_score排序
    ├─ 取前N条（默认10）
    └─ 输出: TOP N新闻列表

阶段6: 发送邮件
    │
    ├─ 检查邮件配置（is_email_configured）
    ├─ 简要版作为邮件正文
    ├─ 深度版PDF作为附件
    ├─ 发送邮件（send_email_with_attachments）
    └─ 输出: 发送成功/失败

阶段7: 清理待分析池
    │
    ├─ 归档到data/archive_pool/
    ├─ 清理已处理新闻
    └─ 输出: 归档完成
```

#### 2.2.3 核心类：Task2DailyReporter

**文件**: `task2_reporter.py`

| 属性/方法 | 说明 |
|-----------|------|
| `ai_filter` | AIFilterAgent实例 |
| `ai_processor` | AIProcessor实例 |
| `storage` | StorageManager实例 |
| `report_generator` | ReportGenerator实例 |
| `run(top_n=10)` | 主执行方法 |
| `_load_pool()` | 阶段1：加载待分析池 |
| `_final_dedup()` | 阶段2：最终去重 |
| `_load_history_news(days=90)` | 加载历史新闻 |
| `_select_top_n()` | 阶段5：选择TOP N |
| `_archive_pool()` | 阶段7：归档 |

---

## 3. RSS采集工作流

### 3.1 RSSCollector（rss/collector.py）

#### 3.1.1 核心职责
- RSS Feed采集
- 多级fallback机制
- 超时重试

#### 3.1.2 多级Fallback机制

```python
def fetch_feed(self, source: RSSSource, max_retries: int = 3) -> Optional[RSSFeed]:
    """
    获取RSS Feed，支持多级fallback
    
    Fallback优先级:
    1. official - 官方RSS源（优先级最高）
    2. rsshub - RSSHub镜像
    3. google_news - Google News聚合
    4. third_party - 第三方聚合源
    """
    url_priority = ['official', 'rsshub', 'google_news', 'third_party']
    
    for url_type in url_priority:
        url = source.urls.get(url_type)
        if not url:
            continue
        
        for attempt in range(max_retries):
            try:
                response = self.http_client.get(url, timeout=30)
                feed = self.parser.parse(response.text)
                feed.used_source_type = url_type
                return feed
            except Exception as e:
                logger.warning(f"获取失败 [{url_type}]: {e}")
                continue
    
    return None  # 所有源都失败
```

### 3.2 RSSSource数据结构（rss/sources.py）

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

### 3.3 增量采集与智能回溯

#### 3.3.1 智能回溯计算

```python
def get_intelligent_cutoff_date(self, source_name: str) -> datetime:
    """
    根据中断时长计算智能回溯日期
    
    策略:
    - 正常采集间隔内 (0-8h): 回溯 = 间隔 × 1.5
    - 轻微延迟 (8-12h): 回溯 = 间隔 × 2
    - 中等延迟 (12-24h): 回溯 = 间隔 × 3
    - 长时间中断 (>24h): 回溯 = min(中断时长, RSS滚动限制)
    """
    downtime = self.get_downtime_hours(source_name)
    
    if downtime <= 8:
        lookback_hours = downtime * 1.5
    elif downtime <= 12:
        lookback_hours = downtime * 2
    elif downtime <= 24:
        lookback_hours = downtime * 3
    else:
        lookback_hours = min(downtime, self._get_rss_rollover_limit(source_name))
    
    return datetime.now() - timedelta(hours=lookback_hours)
```

#### 3.3.2 RSS滚动限制（按源类型）

| 源类型 | 滚动限制 | 说明 |
|--------|---------|------|
| 通讯社 | 48小时 | 路透社、美联社、法新社 |
| 中央媒体 | 72小时 | 新华社、人民日报 |
| 国际媒体 | 48小时 | BBC、纽约时报 |
| 财经媒体 | 72小时 | 金融时报、华尔街日报 |
| 科技媒体 | 96小时 | TechCrunch、Wired |

---

## 4. 过滤与校验工作流

### 4.1 AIFilterAgent（filters/ai_filter_agent.py）

#### 4.1.1 核心职责
- 5W1H检测
- 事实性判断
- 五维评分
- 批处理重试

#### 4.1.2 五维评分体系

| 维度 | 字段名 | 权重 | 说明 |
|------|--------|------|------|
| 信源权威性 | `source_score` | 20% | 中央媒体10分、权威通讯社8-9分、普通媒体4-5分 |
| 事件影响力 | `influence_score` | 25% | 全球性10分、国家级8-9分、行业级6-7分 |
| 传播热度 | `heat_score` | 20% | 全网热搜10分、多平台热搜8-9分 |
| 新闻价值 | `value_score` | 25% | 独家重磅10分、有价值信息6-7分 |
| 合规扣分 | `compliance_deduction` | 10% | 0-1分直接扣减 |

#### 4.1.3 评分公式

```python
final_score = (
    source_score * 0.20 +
    influence_score * 0.25 +
    heat_score * 0.20 +
    value_score * 0.25 -
    compliance_deduction
) * 10
```

#### 4.1.4 5W1H检测输出

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

### 4.2 批处理重试机制

```python
def check_fact_batch(self, news_list, max_retries=3):
    for attempt in range(max_retries):
        try:
            results = self._call_ai_api(news_list)
            return results
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise
```

---

## 5. 处理与解析工作流

### 5.1 AIProcessor（processors/ai_processor.py）

#### 5.1.1 Provider配置

| 用途 | 环境变量前缀 | 说明 |
|------|-------------|------|
| ANALYSIS | `AI_ANALYSIS_*` | 深度分析模型（高级） |
| FILTER | `AI_FILTER_*` | 快速筛选模型（经济） |
| BACKUP | `AI_BACKUP_*` | 备用模型 |

#### 5.1.2 环境变量配置示例

```bash
# 深度分析模型
AI_ANALYSIS_PROVIDER=deepseek
AI_ANALYSIS_MODEL=deepseek-chat
AI_ANALYSIS_KEY=your-api-key
AI_ANALYSIS_BASE_URL=https://api.deepseek.com/v1

# 快速筛选模型
AI_FILTER_PROVIDER=doubao
AI_FILTER_MODEL=doubao-seed-2-0-lite-260215
AI_FILTER_KEY=your-api-key
AI_FILTER_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

### 5.2 领域/标签提取优先级

```
规则命中 > RSS分类 > AI判断
```

---

## 6. 存储工作流

### 6.1 NewsDatabase（storage/database.py）

#### 6.1.1 核心特性
- **单例模式**: 全局唯一数据库连接实例
- **连接池**: 最多5个并发连接
- **WAL模式**: 提升并发性能
- **事务安全**: 自动重试机制
- **FTS5全文索引**: 支持全文搜索

#### 6.1.2 连接池配置

```python
self.__pool = Queue(maxsize=5)  # 连接池大小
self.__wal_mode = True          # WAL模式
```

#### 6.1.3 事务重试机制

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def _execute_with_retry(self, cursor, sql: str, parameters: tuple = ()):
    """带重试机制的数据库执行"""
    cursor.execute(sql, parameters)
```

---

## 7. 报告生成工作流

### 7.1 ReportGenerator（generators/report_generator.py）

#### 7.1.1 报告类型

| 类型 | 格式 | 用途 |
|------|------|------|
| 简要报告 | Markdown | 邮件正文、快速浏览 |
| 深度报告 | Markdown + PDF | 详细分析、附件下载 |

#### 7.1.2 深度分析维度

- 领域聚类分析（政治/经济/科技）
- 历史关联分析（近90天）
- RAG增强洞察
- 事件演变追踪

---

## 8. 知识库工作流

### 8.1 RAGRetriever（knowledge/retriever.py）

#### 8.1.1 检索流程

```python
def retrieve(self, query: str, domain_filter: Optional[str] = None, 
             use_time_decay: bool = True) -> RAGContext:
    # 1. 生成查询向量
    query_embedding = self.embedding_service.get_single_embedding(query)
    
    # 2. 向量检索
    results = self.knowledge_base.search_by_embedding(
        embedding=query_embedding,
        top_k=self.top_k * 2
    )
    
    # 3. 应用时间衰减
    if use_time_decay:
        results = self._apply_time_decay(results)
    
    # 4. 过滤低分结果
    results = [r for r in results if r.score >= self.min_score]
    results = results[:self.top_k]
    
    # 5. 构建上下文
    return self._build_context(query, results)
```

#### 8.1.2 时间衰减公式

```python
def _calculate_time_decay(self, pub_date: str) -> float:
    days_diff = (datetime.now() - news_date).days
    
    if days_diff <= 0:
        return 1.0
    elif days_diff >= self.time_decay_days * 3:  # 90天
        return 0.3
    else:
        return math.exp(-days_diff / self.time_decay_days)  # 30天半衰期
```

### 8.2 EmbeddingService（knowledge/embedding.py）

#### 8.2.1 双模型配置

| 模型 | 名称 | 维度 | 用途 |
|------|------|------|------|
| 主模型 | BAAI/bge-m3 | 1024 | 高精度检索 |
| 快速模型 | all-MiniLM-L6-v2 | 384 | 快速检索 |

---

## 9. 工具与配置

### 9.1 增量跟踪器（utils/incremental_tracker.py）

#### 9.1.1 核心职责
- 记录各源最后采集时间
- 计算中断时长
- 智能回溯日期计算

#### 9.1.2 状态文件

```json
{
  "source_name": "路透社",
  "last_collection": "2026-03-15T07:00:00",
  "total_collected": 1500,
  "status": "active"
}
```

### 9.2 任务锁（utils/task_lock.py）

#### 9.2.1 跨平台实现

```python
def _acquire_unix(self, blocking: bool = True, timeout: Optional[int] = None) -> bool:
    """Unix/Linux使用fcntl文件锁"""
    import fcntl
    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

def _acquire_windows(self, blocking: bool = True, timeout: Optional[int] = None) -> bool:
    """Windows使用文件存在性检查"""
    lock_path = self.lock_dir / f"{self.task_name}.lock"
    if lock_path.exists():
        return False
    lock_path.touch()
    return True
```

---

## 10. 兜底与容错机制

### 10.1 兜底机制汇总表

| 模块 | 场景 | 兜底策略 |
|------|------|---------|
| **AI批处理** | API调用失败 | 指数退避重试3次，失败后整批标记为"待分类" |
| **RSS采集** | 所有源失败 | 记录失败日志，跳过该源继续其他源 |
| **RSS采集** | 源URL失效 | 4级fallback（official→RSSHub→Google News→third_party）|
| **内容提取** | 规则解析失败 | AI兜底解析 |
| **领域分类** | 规则未命中 | RSS分类 → AI推断 |
| **数据库** | 连接失败 | 连接池重试3次，指数退避 |
| **数据库** | 事务失败 | 自动回滚，重试3次 |
| **历史加载** | 数据库加载失败 | 回退到文件加载 |
| **爬虫** | 代理不可用 | 自动切换到直连模式 |
| **爬虫** | 内容提取失败 | 尝试通用p标签提取 |
| **爬虫** | SSL证书错误 | 忽略SSL验证 |

### 10.2 AI批处理失败兜底

```python
max_retries = int(os.getenv("AI_BATCH_MAX_RETRIES", "3"))
for attempt in range(max_retries):
    try:
        results = self.ai_filter.check_fact_batch(batch_news)
        break
    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # 指数退避

# 所有重试失败，整批兜底处理
if results is None:
    for news in batch:
        news['final_score'] = 50.0
        news['domain'] = '待分类'
        news['needs_recheck'] = True
        passed_news.append(news)
        fallback_news.append(news)
```

### 10.3 遗漏补救机制

```python
# 检测遗漏
gap_result = self._detect_gap_for_source(source.name, feed, source_news_count)

# 如果检测到RSS滚动遗漏，触发补救
if gap_result['has_gap'] and gap_result['gap_type'] == 'rss_rollover':
    # 执行补救采集（扩大回溯）
    remedial_news = self._补救采集(source, gap_result)
    
    # 补救效果验证
    gap_result_after = self._detect_gap_for_source(...)
    
    # 判断补救效果
    if not gap_result_after['has_gap']:
        logger.info(f"✅ 补救成功 [{source.name}]: 遗漏已完全补救")
    elif improvement > 0:
        logger.warning(f"⚠️ 部分补救 [{source.name}]: 遗漏分数改善")
    else:
        logger.error(f"❌ 补救失败 [{source.name}]: 遗漏分数未改善")
```

---

## 11. 数据流转

### 11.1 完整数据流图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据流转全景图                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐                                                            │
│  │  RSS源      │                                                            │
│  │  爬虫       │                                                            │
│  └──────┬──────┘                                                            │
│         │ 原始新闻                                                           │
│         ▼                                                                   │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │  采集层     │────▶│  过滤层     │────▶│  AI校验层   │                   │
│  │             │     │             │     │             │                   │
│  │ • RSS采集   │     │ • 白名单    │     │ • 5W1H检测  │                   │
│  │ • 爬虫      │     │ • 可信度    │     │ • 五维评分  │                   │
│  │ • 增量跟踪  │     │ • 去重      │     │ • 领域分类  │                   │
│  └─────────────┘     └─────────────┘     └─────────────┘                   │
│                                                   │                         │
│         ┌─────────────────────────────────────────┘                         │
│         │ 校验通过新闻                                                          │
│         ▼                                                                   │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │  存储层     │────▶│  知识库     │────▶│  报告层     │                   │
│  │             │     │             │     │             │                   │
│  │ • SQLite    │     │ • ChromaDB  │     │ • 简要报告  │                   │
│  │ • FTS5索引  │     │ • 向量索引  │     │ • 深度分析  │                   │
│  │ • 文件备份  │     │ • RAG检索   │     │ • PDF生成   │                   │
│  └─────────────┘     └─────────────┘     └─────────────┘                   │
│                                                   │                         │
│         ┌─────────────────────────────────────────┘                         │
│         │ 报告文件                                                              │
│         ▼                                                                   │
│  ┌─────────────┐     ┌─────────────┐                                        │
│  │  邮件发送   │     │  归档存储   │                                        │
│  │             │     │             │                                        │
│  │ • SMTP发送  │     │ • 待分析池  │                                        │
│  │ • 附件处理  │     │ • 归档池    │                                        │
│  └─────────────┘     └─────────────┘                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 关键数据格式

#### 11.2.1 新闻数据模型（NewsItem）

```python
@dataclass
class NewsItem:
    id: str                      # 唯一ID
    title: str                   # 标题
    translated_title: str        # 译名
    content: str                 # 内容
    summary: str                 # 摘要
    source_name: str             # 来源
    source_type: str             # domestic/international
    domain: str                  # 领域
    tags: List[str]              # 标签
    score: float                 # 综合评分
    pub_date: str                # 发布时间
    link: str                    # 原文链接
    # 5W1H分析
    who: str
    what: str
    when_time: str
    where_place: str
    why: str
    how: str
```

---

## 12. 配置体系

### 12.1 环境变量配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `AI_ANALYSIS_PROVIDER` | 深度分析模型厂商 | deepseek |
| `AI_ANALYSIS_MODEL` | 深度分析模型名 | deepseek-chat |
| `AI_ANALYSIS_KEY` | API密钥 | sk-xxx |
| `AI_FILTER_PROVIDER` | 快速筛选模型厂商 | doubao |
| `AI_FILTER_MODEL` | 快速筛选模型名 | doubao-seed-2-0-lite |
| `AI_FILTER_KEY` | API密钥 | ark-xxx |
| `NEWS_API_KEY` | NewsAPI密钥 | xxx |
| `HTTP_PROXY` | HTTP代理 | http://127.0.0.1:7890 |
| `SMTP_HOST` | SMTP服务器 | smtp.gmail.com |
| `SMTP_PORT` | SMTP端口 | 465 |
| `SMTP_USER` | 邮箱账号 | user@gmail.com |
| `SMTP_PASSWORD` | 邮箱密码/授权码 | xxx |
| `EMAIL_TO` | 收件人 | recipient@example.com |
| `AI_BATCH_SIZE` | AI批处理大小 | 4 |
| `LOG_LEVEL` | 日志级别 | INFO |

### 12.2 YAML配置文件

| 文件 | 用途 |
|------|------|
| `sources.yaml` | RSS源配置 |
| `config/ai_providers.yaml` | AI厂商配置 |
| `config/knowledge.yaml` | 知识库配置 |
| `config/parsing_rules.yaml` | 解析规则配置 |
| `config/report_templates.yaml` | 报告模板配置 |

---

## 13. 定时任务调度

### 13.1 GitHub Actions调度

| 工作流 | 触发时间(北京时间) | 功能 |
|--------|-------------------|------|
| collect.yml | 07:00, 15:00, 23:00 | 新闻采集（早7点含报告生成） |
| report.yml | 00:00 | 报告生成（独立任务） |
| send_email.yml | 08:30 | 邮件发送 |

### 13.2 本地Windows任务调度

| 时间 | 任务 | 命令 |
|------|------|------|
| 07:00 | 新闻采集 | run_collect_auto.bat |
| 07:05 | 报告生成 | run_report_auto.bat |
| 08:30 | 邮件发送 | run_send_email_auto.bat |
| 15:00 | 补充采集 | run_collect_auto.bat |
| 23:00 | 补充采集 | run_collect_auto.bat |

---

## 14. 数据库设计

### 14.1 核心表结构

#### 14.1.1 news表（新闻主表）

```sql
CREATE TABLE news (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    translated_title TEXT,
    content TEXT,
    summary TEXT,
    source_name TEXT,
    source_type TEXT,
    domain TEXT,
    tags TEXT,  -- JSON数组
    score REAL,
    score_credibility REAL,
    score_importance REAL,
    score_timeliness REAL,
    score_impact REAL,
    pub_date TEXT,
    link TEXT UNIQUE,
    -- 5W1H字段
    who TEXT,
    what TEXT,
    when_time TEXT,
    where_place TEXT,
    why TEXT,
    how TEXT,
    -- 向量字段
    embedding BLOB,
    embedding_updated_at DATETIME,
    -- 元数据
    extraction_method TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 14.1.2 subscribers表（订阅者表）

```sql
CREATE TABLE subscribers (
    email TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    subscription_type TEXT DEFAULT 'free',  -- free/premium
    expires_at TEXT,
    metadata TEXT  -- JSON
);
```

### 14.2 FTS5全文索引

```sql
CREATE VIRTUAL TABLE news_fts USING fts5(
    title,
    content,
    content='news',
    content_rowid='rowid'
);
```

---

## 15. API与接口

### 15.1 内部API

| 模块 | 类/函数 | 功能 |
|------|---------|------|
| storage.database | `get_db()` | 获取数据库实例 |
| storage.database | `NewsDatabase()` | 数据库操作 |
| utils.email_sender | `send_email_with_attachments()` | 发送邮件 |
| utils.email_sender | `is_email_configured()` | 检查邮件配置 |
| knowledge.retriever | `RAGRetriever.retrieve()` | RAG检索 |
| knowledge.embedding | `EmbeddingService.get_embeddings()` | 文本向量化 |

### 15.2 Web API（商业化模块）

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/subscribe` | POST | 订阅服务 |
| `/api/unsubscribe` | POST | 取消订阅 |
| `/api/stats` | GET | 获取统计 |
| `/api/check-content` | POST | 内容合规检测 |
| `/api/check-source` | POST | 信源检测 |

---

## 16. 测试与调试

### 16.1 测试标记

| 标记 | 说明 |
|------|------|
| `@pytest.mark.unit` | 单元测试（快速、隔离）|
| `@pytest.mark.integration` | 集成测试（需外部资源）|
| `@pytest.mark.e2e` | 端到端测试 |
| `@pytest.mark.slow` | 慢速测试（>5秒）|
| `@pytest.mark.requires_api` | 需要API密钥 |

### 16.2 调试工具

| 脚本 | 用途 |
|------|------|
| `scripts/tools/check_env.py` | 检查环境配置 |
| `scripts/tools/check_data.py` | 检查数据完整性 |
| `scripts/database/db_manager.py` | 数据库管理CLI |
| `check_entity_fields.py` | 检查5W1H字段填充 |

---

## 附录A：文件清单

### A.1 核心文件（第一批）

- `task1_collector.py` - Task1采集工作流
- `task2_reporter.py` - Task2报告工作流
- `rss/collector.py` - RSS采集器
- `rss/sources.py` - RSS源管理
- `filters/ai_filter_agent.py` - AI过滤代理
- `processors/ai_processor.py` - AI处理器
- `storage/database.py` - 数据库存储
- `generators/report_generator.py` - 报告生成器

### A.2 扩展文件（第二批）

- `knowledge/retriever.py` - RAG检索器
- `knowledge/chroma_store.py` - ChromaDB存储
- `knowledge/embedding.py` - 向量化服务
- `utils/incremental_tracker.py` - 增量跟踪器
- `utils/task_lock.py` - 任务锁
- `models/data_models.py` - 数据模型

### A.3 其他文件（第三批）

- `crawlers/base.py` - 爬虫基类
- `crawlers/xinhua.py` - 新华社爬虫
- `crawlers/people.py` - 人民日报爬虫
- `scheduler/task_scheduler.py` - 任务调度器
- `.github/workflows/*.yml` - CI/CD工作流
- `commercial/web/app.py` - Web应用
- `scripts/` - 各类工具脚本

---

## 附录B：术语表

| 术语 | 说明 |
|------|------|
| **5W1H** | 新闻六要素：Who, What, When, Where, Why, How |
| **RAG** | Retrieval-Augmented Generation，检索增强生成 |
| **RSS** | Really Simple Syndication，简易信息聚合 |
| **FTS5** | Full-Text Search 5，SQLite全文搜索引擎 |
| **WAL** | Write-Ahead Logging，预写日志模式 |
| **BGE-M3** | BAAI General Embedding M3，向量模型 |
| **Fallback** | 兜底、回退机制 |
| **增量采集** | 只采集上次采集后新增的新闻 |
| **智能回溯** | 根据中断时长动态计算回溯时间 |

---

**文档结束**

本文档完整覆盖了新闻分析工作流系统的所有模块，包括核心工作流、RSS采集、过滤校验、处理解析、存储、报告生成、知识库、工具配置、兜底机制、数据流转、配置体系、定时任务、数据库设计、API接口和测试调试等方面。
