# 项目工作流架构说明 - 第一批：核心工作流

> 本文档为中间交付物，覆盖阶段1-6：入口与核心工作流、RSS采集、过滤校验、处理解析、存储、报告生成

---

## 1. 入口与核心工作流

### 1.1 Task1采集工作流（task1_collector.py）

#### 1.1.1 概述
- **触发时机**: 每天3次（07:00、15:00、23:00）
- **核心职责**: 高频新闻采集、AI校验、数据库存储
- **工作流阶段**: 6个阶段

#### 1.1.2 6阶段工作流详解

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

#### 1.1.3 核心类：Task1NewsCollector

| 属性/方法 | 说明 |
|-----------|------|
| `MIN_CONTENT_LENGTH` | 最小内容长度50字符 |
| `MAX_PER_SOURCE` | 每源最大条目数10 |
| `ai_batch_size` | AI批处理大小（默认4，环境变量AI_BATCH_SIZE） |
| `enable_incremental` | 增量采集开关（ENABLE_INCREMENTAL_COLLECTION） |
| `run(max_per_source)` | 主执行方法 |
| `_collect_from_sources()` | 阶段1：采集 |
| `_apply_basic_filters()` | 阶段2：基础过滤 |
| `_apply_ai_filter()` | 阶段3：AI校验 |
| `_store_batch_to_database()` | 阶段4：存储 |
| `_recheck_fallback_news()` | 阶段5：兜底重判 |

#### 1.1.4 兜底机制

**AI批处理失败兜底**:
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

**遗漏补救机制**:
```python
# 检测遗漏
gap_result = self._detect_gap_for_source(source.name, feed, source_news_count)

# 如果检测到RSS滚动遗漏，触发补救
if gap_result['has_gap'] and gap_result['gap_type'] == 'rss_rollover':
    # 记录补救前遗漏分数
    gap_score_before = gap_result.get('gap_score', 0)
    
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

#### 1.1.5 统计指标

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
| `remedial_partial` | 部分补救数 |
| `remedial_failed` | 补救失败数 |

---

### 1.2 Task2报告工作流（task2_reporter.py）

#### 1.2.1 概述
- **触发时机**: 每日00:10运行一次
- **核心职责**: 读取待分析池、生成报告、邮件推送
- **工作流阶段**: 7个阶段

#### 1.2.2 7阶段工作流详解

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

#### 1.2.3 核心类：Task2DailyReporter

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

#### 1.2.4 待分析池加载逻辑

```python
def _load_pool(self) -> tuple:
    pool_dir = Path(PROJECT_ROOT) / 'data' / 'analysis_pool'
    archive_dir = Path(PROJECT_ROOT) / 'data' / 'archive_pool'
    
    # 1. 读取待分析池
    for pool_file in pool_dir.glob('pool_*.json'):
        news = json.load(f)
        all_news.extend(news)
    
    # 2. 读取归档池中最近24小时内归档的新闻
    cutoff_time = now - timedelta(hours=24)
    for archive_file in archive_dir.glob('pool_*.json'):
        # 解析归档时间（文件名格式：pool_2026-03-09_2026-03-09_HHMMSS.json）
        archive_datetime = datetime.strptime(archive_datetime_str, '%Y-%m-%d %H%M%S')
        if archive_datetime >= cutoff_time:
            news = json.load(f)
            all_news.extend(news)
    
    # 3. 按发布时间筛选（过去24小时）
    filtered_news = [n for n in all_news if pub_date >= cutoff_time]
    
    # 4. 去重（基于news_id）
    unique_news = deduplicate_by_news_id(filtered_news)
    
    return unique_news, {report_date}
```

#### 1.2.5 历史新闻加载兜底

```python
def _load_history_news(self, days: int = 90) -> List[Dict]:
    # 优先从数据库加载带embedding的新闻
    try:
        db = get_db()
        history_news = db.get_news_with_embeddings(days=days)
        if history_news:
            return history_news
    except Exception as e:
        logger.warning(f"从数据库加载历史新闻失败: {e}，尝试从文件加载")
    
    # 回退到文件加载
    archive_dir = Path(PROJECT_ROOT) / 'data' / 'archive_pool'
    # ... 文件加载逻辑
```

#### 1.2.6 统计指标

| 指标 | 说明 |
|------|------|
| `pool_total` | 待分析池总数 |
| `dedup_passed` | 去重后数量 |
| `brief_report` | 简要报告文件路径 |
| `depth_reports` | 深度报告文件列表 |
| `report_generated` | 报告生成标志 |
| `top10_count` | TOP N数量 |

---

### 1.3 其他入口文件

#### 1.3.1 run_collect.py
- 采集任务入口封装
- 支持命令行参数
- 调用Task1NewsCollector

#### 1.3.2 run_report.py
- 报告任务入口封装
- 支持命令行参数
- 调用Task2DailyReporter

#### 1.3.3 run_now.py
- 一键运行脚本
- 顺序执行采集+报告
- 用于手动触发

#### 1.3.4 send_email.py
- 邮件发送入口
- 支持单独发送报告
- 邮件配置检查

---

## 2. RSS采集模块

### 2.1 RSSCollector（rss/collector.py）

#### 2.1.1 核心职责
- RSS Feed采集
- 多级fallback机制
- 超时重试

#### 2.1.2 多级Fallback机制

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

#### 2.1.3 关键属性

| 属性 | 说明 |
|------|------|
| `feed.used_backup` | 是否使用了备用源 |
| `feed.used_source_type` | 实际使用的源类型 |
| `feed.items` | 解析后的新闻条目列表 |

---

### 2.2 RSSSourceManager（rss/sources.py）

#### 2.2.1 核心职责
- 管理RSS源配置
- 从sources.yaml加载
- 源启用/禁用管理

#### 2.2.2 RSSSource数据结构

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

#### 2.2.3 源URL优先级

```
官方RSS → RSSHub → Google News → 第三方聚合
```

---

### 2.3 RSSParser（rss/parser.py）

#### 2.3.1 核心职责
- RSS XML解析
- 提取标题、链接、内容、发布时间
- 处理各种RSS格式

---

### 2.4 IncrementalCollector（rss/incremental_collector.py）

#### 2.4.1 核心职责
- 增量采集逻辑
- 智能回溯计算
- 状态跟踪

---

### 2.5 sources.yaml配置

#### 2.5.1 配置结构

```yaml
international:
  news_agency:
    - name: 路透社
      type: 通讯社
      region: 英国/全球
      credibility: 高
      tier: 1
      rss_url_official: https://www.reutersagency.com/feed/
      rss_url_rsshub: https://rsshub.app/reuters/world
      rss_url_google: https://news.google.com/rss/search?q=site:reuters.com
      rss_url: https://news.google.com/rss/search?q=site:reuters.com
      rss_url_backup: https://rsshub.app/reuters/world
      enabled: true
```

---

## 3. 过滤与校验模块

### 3.1 AIFilterAgent（filters/ai_filter_agent.py）

#### 3.1.1 核心职责
- 5W1H检测
- 事实性判断
- 五维评分
- 批处理重试

#### 3.1.2 五维评分体系

| 维度 | 字段名 | 权重 | 说明 |
|------|--------|------|------|
| 信源权威性 | `source_score` | 20% | 中央媒体10分、权威通讯社8-9分、普通媒体4-5分 |
| 事件影响力 | `influence_score` | 25% | 全球性10分、国家级8-9分、行业级6-7分 |
| 传播热度 | `heat_score` | 20% | 全网热搜10分、多平台热搜8-9分 |
| 新闻价值 | `value_score` | 25% | 独家重磅10分、有价值信息6-7分 |
| 合规扣分 | `compliance_deduction` | 10% | 0-1分直接扣减 |

#### 3.1.3 评分公式

```python
final_score = (
    source_score * 0.20 +
    influence_score * 0.25 +
    heat_score * 0.20 +
    value_score * 0.25 -
    compliance_deduction
) * 10
```

#### 3.1.4 5W1H检测输出

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

#### 3.1.5 批处理重试机制

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

### 3.2 SourceValidator（filters/source_validator.py）

#### 3.2.1 核心职责
- 白名单校验
- 验证源是否可信

#### 3.2.2 校验逻辑

```python
def validate_source(self, source_name: str) -> ValidationResult:
    if source_name in self.whitelist:
        return ValidationResult(passed=True, source=source_name)
    return ValidationResult(passed=False, reason="不在白名单")
```

---

### 3.3 ContentFilter（filters/content_filter.py）

#### 3.3.1 核心职责
- 内容过滤
- 垃圾内容检测

---

### 3.4 Deduplication（filters/deduplication.py）

#### 3.4.1 核心职责
- 去重逻辑
- 基于news_id去重
- AI辅助去重

---

## 4. 处理与解析模块

### 4.1 AIProcessor（processors/ai_processor.py）

#### 4.1.1 核心职责
- 统一AI调用接口
- 多provider支持
- 用途分类（ANALYSIS/FILTER/BACKUP）

#### 4.1.2 Provider配置

| 用途 | 环境变量前缀 | 说明 |
|------|-------------|------|
| ANALYSIS | `AI_ANALYSIS_*` | 深度分析模型（高级） |
| FILTER | `AI_FILTER_*` | 快速筛选模型（经济） |
| BACKUP | `AI_BACKUP_*` | 备用模型 |

#### 4.1.3 核心方法

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

---

### 4.2 RuleBasedParser（processors/content_parser.py）

#### 4.2.1 核心职责
- 基于YAML规则的领域/标签提取
- 规则命中优先
- AI兜底补全

#### 4.2.2 提取优先级

```
规则命中 > RSS分类 > AI判断
```

#### 4.2.3 解析规则配置（config/parsing_rules.example.yaml）

```yaml
domains:
  政治:
    keywords: ["政府", "政策", "选举", "外交"]
    patterns: ["*政府*", "*政策*"]
  经济:
    keywords: ["股市", "金融", "经济", "投资"]
    patterns: ["*股市*", "*金融*"]
```

---

### 4.3 HistoryRelationEngine（processors/history_relation_engine.py）

#### 4.3.1 核心职责
- 历史关联分析
- 查找相关历史新闻

#### 4.3.2 算法

- TF-IDF + 实体加权 + 时间衰减
- 权重分配：融合相似度70% + 时间关联度30%

#### 4.3.3 时间分类

| 时间范围 | 类型 | 基础分 |
|----------|------|--------|
| 0-7天 | 本周关联 | 1.0 |
| 7-30天 | 近期关联 | 0.7 |
| 30-90天 | 历史背景 | 0.3 |

---

## 5. 存储模块

### 5.1 NewsDatabase（storage/database.py）

#### 5.1.1 核心职责
- SQLite数据库管理
- 事务安全操作
- 连接池管理
- WAL模式

#### 5.1.2 关键特性

| 特性 | 说明 |
|------|------|
| WAL模式 | 提高并发性能 |
| 连接池 | 默认5个连接 |
| 事务上下文 | 自动提交或回滚 |
| FTS5全文索引 | 自动同步 |

#### 5.1.3 事务安全写入

```python
def insert_news_with_processed(self, news: NewsData) -> bool:
    with self.transaction() as conn:
        # 检查存在
        # 插入新闻
        # 标记已处理
        # 自动提交或回滚

def insert_news_batch(self, news_list: List[NewsData]) -> int:
    with self.transaction() as conn:
        cursor.executemany(INSERT_NEWS_SQL, news_dicts)
        cursor.executemany(INSERT_PROCESSED_SQL, processed_dicts)
```

#### 5.1.4 写操作重试封装

```python
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

#### 5.1.5 数据库表结构

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `news` | 新闻主表 | id, title, domain, score, 5W1H字段 |
| `processed_news` | 去重基线表 | news_id, processed_at |
| `rejected_news` | 拒绝新闻表 | news_id, reject_reason, reject_type |
| `event_clusters` | 事件聚类表 | cluster_date, domain, event_name, news_ids |
| `news_fts` | FTS5全文索引 | title, content, keywords, tags |

---

### 5.2 Baseline（storage/baseline.py）

#### 5.2.1 核心职责
- 历史数据基线
- 用于关联分析

---

### 5.3 FileManager（storage/file_manager.py）

#### 5.3.1 核心职责
- 文件存储管理
- 报告文件管理

---

### 5.4 StorageManager（storage/storage_manager.py）

#### 5.4.1 核心职责
- 存储管理器
- 统一存储接口

---

## 6. 报告生成模块

### 6.1 ReportGenerator（generators/report_generator.py）

#### 6.1.1 核心职责
- 生成简要摘要报告
- 生成深度分析报告
- 模板渲染
- PDF导出

#### 6.1.2 报告目录结构

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

#### 6.1.3 中国/国外新闻判断逻辑

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

---

### 6.2 DepthAnalyzer（analysts/depth_analyzer.py）

#### 6.2.1 核心职责
- 深度分析
- 洞察生成（900-1200字文章）

#### 6.2.2 分析维度

- 核心要点
- 直接影响
- 趋势预判
- 风险机遇

---

### 6.3 InvestmentAdvisor（analysts/investment_advisor.py）

#### 6.3.1 核心职责
- 投资分析（可选）
- 通过ENABLE_INVESTMENT_ANALYSIS启用

---

### 6.4 报告模板配置（config/report_templates.yaml）

#### 6.4.1 模板类型

- default - 默认模板
- minimal - 简洁模板
- detailed - 详细模板

---

## 附录A：关键兜底机制汇总

### A.1 RSS采集兜底
- **机制**: 官方 → RSSHub → Google News → 第三方
- **实现**: RSSCollector.fetch_feed()
- **日志**: `used_source_type` 字段记录实际使用的源

### A.2 AI批处理兜底
- **机制**: 失败时标记为"待分类"，后续重判
- **实现**: Task1NewsCollector._apply_ai_filter()
- **标记**: `needs_recheck=True`, `domain='待分类'`

### A.3 数据库写入兜底
- **机制**: 指数退避重试（最多3次）
- **实现**: NewsDatabase._execute_with_retry()
- **退避**: 2^attempt 秒

### A.4 遗漏补救机制
- **机制**: 检测 → 扩大回溯 → 验证效果
- **实现**: Task1NewsCollector._collect_from_sources()
- **效果分类**: 完全补救/部分补救/补救失败

### A.5 任务锁兜底
- **机制**: 超时自动清理失效锁
- **实现**: TaskLock
- **超时**: 3600秒

### A.6 AI Provider兜底
- **机制**: ANALYSIS → FILTER → BACKUP
- **实现**: AIProcessor.get_provider()
- **配置**: 环境变量AI_*_PROVIDER等

---

## 附录B：数据流转路径

### B.1 新闻数据流转

```
RSS Feed (XML)
    ↓
RSS Item (解析后)
    ↓
News Dict (处理中)
    ├─ + news_id
    ├─ + domain (规则/RSS/AI)
    ├─ + tags (规则/AI)
    └─ + rule_parse
    ↓
NewsData (AI校验后)
    ├─ + 5W1H字段
    ├─ + score字段
    ├─ + extraction_method
    └─ + fact_check
    ↓
Database (SQLite)
    ├─ news表
    ├─ processed_news表
    └─ news_fts表 (FTS5)
```

### B.2 待分析池流转

```
Task1采集
    ↓ (存入pool)
analysis_pool/ (待分析池)
    ↓ (Task2读取)
Task2报告
    ↓ (归档)
archive_pool/ (归档池，保留90天)
```

---

**文档版本**: 第一批中间交付物
**覆盖范围**: 阶段1-6（入口与核心工作流、RSS采集、过滤校验、处理解析、存储、报告生成）
**创建时间**: 2026-03-15
**状态**: 待整合到完整文档
