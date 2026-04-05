# Layer 1: 模块层文档

---

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|-----|------|------|-----|
| v1.0 | 2026-03-21 | ⏸️ 已反馈 | 完成所有模块扫描 |
| v1.1 | 2026-03-21 | ✅ 已完成 | 修正文件数量、补充模块状态分析、修正领域定义差异 |

---

## 上层文档同步检查

**参考文档**：`阶段一_文档生成工作记录.md` (Layer 0 v0.5)

| 检查项 | 状态 | 说明 |
|-------|------|-----|
| 模块数量 | ✅ 一致 | core(9) + commercial(4) = 13个 |
| 模块名称 | ✅ 一致 | collector, processor, storage, filters, models, config, scheduler, service, utils |
| 文件数量 | ✅ 已修正 | 见下文详细统计（processor=19, service=2） |

---

## 一、模块总览

### 1.1 模块清单

| 序号 | 模块名 | 路径 | 类型 | 文件数 | 使用状态 |
|-----|-------|------|------|-------|---------|
| 1 | collector | core/collector/ | 核心 | 11 | ✅ 正常使用 |
| 2 | processor | core/processor/ | 核心 | 19 | ✅ 正常使用 |
| 3 | storage | core/storage/ | 核心 | 5 | ✅ 正常使用 |
| 4 | filters | core/filters/ | 核心 | 5 | ⚠️ 部分废弃 |
| 5 | models | core/models/ | 核心 | 2 | ✅ 正常使用 |
| 6 | config | core/config/ | 核心 | 4 | ✅ 正常使用 |
| 7 | scheduler | core/scheduler/ | 核心 | 2 | ❌ 未使用 |
| 8 | service | core/service/ | 核心 | 2 | ✅ 正常使用 |
| 9 | utils | core/utils/ | 核心 | 25 | ✅ 正常使用 |
| 10 | compliance | commercial/compliance/ | 商业版 | 5 | ✅ 正常使用 |
| 11 | services | commercial/services/ | 商业版 | 2 | ✅ 正常使用 |
| 12 | subscription | commercial/subscription/ | 商业版 | 2 | ✅ 正常使用 |
| 13 | web | commercial/web/ | 商业版 | 2 | ✅ 正常使用 |

**总计**：13个模块，84个Python文件

### 1.2 使用状态说明

| 状态 | 含义 | 模块 |
|-----|------|-----|
| ✅ 正常使用 | 模块被项目实际调用 | collector, processor, storage, models, config, service, utils, compliance, services, subscription, web |
| ⚠️ 部分废弃 | 模块内部分文件已废弃 | filters (content_filter.py已废弃) |
| ❌ 未使用 | 模块存在但未被任何代码导入 | scheduler |

---

## 二、核心模块详情

### 2.1 collector 模块

**路径**：`core/collector/`

**职责**：RSS采集、爬虫实现、信源管理、增量采集

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口，统一导出 | 导出: RSSParser, RSSCollector, RSSIncrementalCollector等 | ✅ |
| `sources.py` | RSS源配置管理 | `RSSSource`, `RSSSourceManager` | ✅ |
| `collector.py` | RSS采集器 | `RSSCollector` | ✅ |
| `incremental_collector.py` | 增量抓取服务 | `CachedNewsItem`, `RSSIncrementalCollector` | ✅ |
| `api_sources.py` | API源采集 | `APINewsItem`, `NewsAPISource`, `GNewsSource`, `APISourceManager`, `APIToRSSAdapter` | ✅ |
| `parser.py` | RSS解析器 | `RSSItem`, `RSSFeed`, `RSSParser` | ✅ |
| `crawlers/__init__.py` | 爬虫子模块入口 | - | ✅ |
| `crawlers/base.py` | 爬虫抽象基类 | `BaseCrawler`, `NewsAPICrawler` | ✅ |
| `crawlers/factory.py` | 爬虫工厂 | `CrawlerFactory` | ✅ |
| `crawlers/people.py` | 人民日报爬虫 | `PeopleCrawler` | ✅ |
| `crawlers/xinhua.py` | 新华社爬虫 | `XinhuaCrawler` | ✅ |

**模块架构**：
```
入口层 → 配置层 → 解析层 → 采集层 → 增量层 → API层 → 爬虫层
```

---

### 2.2 processor 模块

**路径**：`core/processor/`

**职责**：AI处理、热度评分、历史关联、报告生成

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | 导出: FieldNormalizer, LightweightClassifier, CombinedProcessor等 | ✅ |
| `ai_processor.py` | AI处理核心 | `ValueJudgmentResult`, `ReportResult`, `BaseProvider`, `AIProcessor` | ✅ |
| `ai_fallback_extractor.py` | AI兜底抽取 | `AIFallbackResult`, `AIFallbackExtractor` | ✅ |
| `article_fetcher.py` | 原文获取 | `ArticleFetcher` | ✅ |
| `chart_data_service.py` | 图表数据服务 | `DailyMetric`, `ChartDataService` | ✅ |
| `combined_processor.py` | 合并处理器 | `CombinedProcessor` | ✅ |
| `content_parser.py` | 内容解析 | `ParseConfidence`, `ParseResult`, `ParsingRules`, `RuleBasedParser`, `ExtractedEntity`, `EntityExtractor` | ✅ |
| `data_validator.py` | 数据验证 | `DataValidator` | ✅ |
| `depth_analyzer.py` | 深度分析 | `DepthAnalysis`, `DepthAnalyzer` | ✅ |
| `field_normalizer.py` | 字段标准化 | `FieldNormalizer` | ✅ |
| `heat_processor.py` | 热度评分 | `HeatProcessor` | ✅ |
| `heat_scorer.py` | 热度评分器(简化版) | `HeatScorer` | ✅ |
| `history_relation_engine.py` | 历史关联(融合版) | `RelatedNews`, `UnifiedAnalyzer`, `TimeAnalyzer`, `HistoryRelationEngine` | ✅ |
| `history_relation_engine_bge3.py` | BGE-M3历史关联 | `RelatedRecord`, `_FAISSIndex`, `BGE3HistoryRelationEngine` | ✅ |
| `history_relation_engine_fulltext.py` | 全文历史关联 | `FullTextRelatedRecord`, `_FAISSIndex`, `BGE3FullTextEngine` | ✅ |
| `investment_advisor.py` | 投资顾问 | `InvestmentAdvice`, `MarketImpact`, `InvestmentAdvisor` | ✅ |
| `lightweight_classifier.py` | 轻量级分类 | `LightweightClassifier` | ✅ |
| `generators/__init__.py` | generators子模块入口 | 导出: ReportGenerator | ✅ |
| `generators/report_generator.py` | 报告生成器 | `DomainContext`, `ReportGenerator` | ✅ |

**模块架构**：
```
核心AI层 → 分类层 → 解析层 → 处理层 → 验证层 → 评分层 → 关联层 → 分析层 → 报告层
```

**设计说明**：`generators/`子目录单独存在的原因：
1. **职责分离**：报告生成是独立功能域，与数据处理逻辑分离
2. **扩展性**：未来可添加更多生成器（图表生成器、PDF生成器等）
3. **代码整洁**：processor模块文件较多（19个），抽离报告生成减少顶层文件

---

### 2.3 storage 模块

**路径**：`core/storage/`

**职责**：数据库操作、文件管理、基线管理

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | 导出: `NewsDatabase`, `get_db` | ✅ |
| `database.py` | SQLite数据库管理 | `NewsData`, `ConnectionPool`, `NewsDatabase` | ✅ |
| `baseline.py` | 新闻基准库管理 | `BaselineNews`, `NewsBaseline`, `get_baseline` | ✅ |
| `file_manager.py` | 文件管理 | `FileManager` | ✅ |
| `storage_manager.py` | 存储管理 | `StorageManager`, `get_storage` | ✅ |

---

### 2.4 filters 模块

**路径**：`core/filters/`

**职责**：内容过滤、去重、信源验证、AI过滤

**使用状态**：⚠️ 部分废弃（content_filter.py已废弃）

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | 导出所有过滤器组件 | ✅ |
| `source_validator.py` | 信源校验(第1-2步) | `ValidationResult`, `SourceValidator` | ✅ |
| `content_filter.py` | 内容属性校验(第3步) | `ContentCheckResult`, `ContentFilter` | ❌ **已废弃** |
| `deduplication.py` | 冗余去重(第4步) | `DedupResult`, `DeduplicationFilter` | ✅ |
| `ai_filter_agent.py` | AI判断(第5步) | `AIFactCheckResult`, `AIDedupResult`, `AIFilterLog`, `AIFilterAgent` | ✅ |

**废弃说明**：
- `content_filter.py` 已废弃，仅保留接口兼容性
- **废弃原因**：基于规则的简单校验器功能有限，已被 `AIFilterAgent`（AI智能判断）替代
- 生产环境应使用 `core.filters.ai_filter_agent.AIFilterAgent`

**过滤流程**：
```
第1步: 白名单校验 → 第2步: 可信度校验 → 第3步: (已废弃) → 第4步: 冗余去重 → 第5步: AI判断
```

---

### 2.5 models 模块

**路径**：`core/models/`

**职责**：数据类定义（dataclass）

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | 导出所有数据模型类和常量 | ✅ |
| `data_models.py` | 核心数据模型 | `NewsItem`, `ThirdPartyContent`, `Tag`, `Event`, `NewsReport`, `CrawlerResult`, `AIAnalysisResult` | ✅ |

**常量定义**：
- `DOMAINS`: 新闻领域定义（10个领域）
- `SOURCE_TYPES`: 新闻来源类型（官媒、第三方）
- `CATEGORIES`: 新闻分类（国内、国际）

**⚠️ 领域定义差异**：

| 来源 | 领域数量 | 领域列表 |
|-----|---------|---------|
| **README.md** | 8类 | 政治/经济/科技/军事/社会/文化/体育/娱乐 |
| **lightweight_classifier.py** | 8类 | 政治/经济/科技/军事/社会/文化/体育/娱乐 |
| **data_models.py** | 10类 | 政治/经济/科技/社会/**国际**/军事/文化/体育/娱乐/**综合** |

**差异说明**：`data_models.py` 多了 `国际` 和 `综合` 两个领域，需要在Layer 2进一步核实实际使用情况。

---

### 2.6 config 模块

**路径**：`core/config/`

**职责**：配置加载、模板管理

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 统一配置接口 | `get_config()`, `get_sources()`, `get_ai_providers()` 等 | ✅ |
| `loader.py` | 配置加载与环境验证 | 常量: `HISTORY_NEWS_DAYS`, `BATCH_SIZE` 等; 函数: `load_env()`, `load_sources()` 等 | ✅ |
| `manager.py` | 统一配置管理器 | `ConfigManager`, `get_config_manager()` | ✅ |
| `report_templates.py` | 报告模板配置 | 常量: `DEFAULT_TEMPLATE`, `REPORT_TEMPLATES`; 函数: `get_template()` | ✅ |

**配置文件**：
- `core_config.yaml`: 核心配置
- `report_templates.yaml`: 报告模板

---

### 2.7 scheduler 模块

**路径**：`core/scheduler/`

**职责**：任务调度

**使用状态**：❌ **未被实际使用**

**废弃原因**：项目使用 **GitHub Actions** 定时任务，而非内置调度器

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | 导出: `TaskScheduler`, `ScheduledTask` | ❌ |
| `task_scheduler.py` | 定时任务调度器 | `ScheduledTask`, `TaskScheduler`, `run_scheduler_daemon()` | ❌ |

**说明**：此模块是一个独立可运行的守护进程脚本，但当前项目没有任何代码导入它。

---

### 2.8 service 模块

**路径**：`core/service/`

**职责**：健康监控

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `health_monitor/health_monitor.py` | 健康监控器 | `HealthMonitor`, `get_health_monitor()` | ✅ |
| `health_monitor/monitoring_data.py` | 监控数据结构 | `MonitoringData` | ✅ |

**注意**：此模块没有 `__init__.py` 文件。

---

### 2.9 utils 模块

**路径**：`core/utils/`

**职责**：工具函数集合（日志、HTTP、邮件等）

**使用状态**：✅ 正常使用

**文件清单**：

| 分类 | 文件名 | 职责 | 主要类/函数 | 状态 |
|-----|-------|------|-----------|------|
| **网络请求** | `http_client.py` | HTTP请求工具 | `create_retry_session()`, `safe_request()`, `HEADERS` | ✅ |
| | `proxy_config.py` | 代理配置 | `get_proxy_config()` | ✅ |
| **缓存系统** | `cache.py` | 缓存工具 | `MemoryCache`, `FileCache`, `cached()` | ✅ |
| **错误处理** | `error_handling.py` | 错误处理 | `NewsAnalyzerError`, `error_handler()` | ✅ |
| | `errors.py` | 错误类型 | `CollectionError`, `ProcessingError`, `StorageError` | ✅ |
| **监控追踪** | `heartbeat.py` | 心跳监控 | `HeartbeatStatus`, `HeartbeatMonitor` | ✅ |
| | `monitoring.py` | 监控工具 | `DataFlowMonitor`, `SystemMonitor`, `LoggerOptimizer` | ✅ |
| | `performance.py` | 性能监控 | `PerformanceMetric`, `PerformanceMonitor`, `timed()` | ✅ |
| | `workflow_timer.py` | 工作流时间追踪 | `StageMetric`, `WorkflowRun`, `WorkflowTimer` | ✅ |
| **热榜数据** | `hotboard_fetcher.py` | 热榜获取 | `HotItem`, `HotboardFetcher` | ⚠️ 已弃用 |
| | `hotboard_manager.py` | 热榜管理 | `HotItem`, `HotboardCache`, `HotboardManager` | ✅ |
| **采集相关** | `collection_config.py` | 采集配置 | `CollectionConfigManager` | ✅ |
| | `incremental_tracker.py` | 增量追踪 | `IncrementalTracker` | ✅ |
| | `source_scorer.py` | 信源评分 | `get_source_score()`, `TIER_SCORES` | ✅ |
| **日志系统** | `log_utils.py` | 日志脱敏 | `SanitizedLogger`, `sanitize_text()` | ✅ |
| | `logging_config.py` | 日志配置 | `setup_logging()` | ✅ |
| **报告生成** | `md2pdf.py` | Markdown转PDF | `create_pdf_from_md()`, `convert_md_file_to_pdf()` | ✅ |
| | `chart_generator.py` | 图表生成 | `generate_domain_chart()` | ⚠️ 暂不可用 |
| | `email_sender.py` | 邮件发送 | `send_email_with_attachments()`, `send_report_email()` | ✅ |
| **市场数据** | `market_data_fetcher.py` | 市场数据获取 | `MarketSnapshot`, `MarketDataFetcher` | ✅ |
| **工具函数** | `text_utils.py` | 文本处理 | `get_news_title()`, `parse_json_str()` | ✅ |
| | `security.py` | 安全工具 | `hash_content()`, `sanitize_url()` | ✅ |
| | `api_optimizer.py` | API优化 | `APIOptimizer` | ✅ |
| | `task_lock.py` | 任务锁 | `TaskLock`, `task_lock()` | ✅ |
| 入口 | `__init__.py` | 模块入口 | 导出HTTP相关功能 | ✅ |

---

## 三、商业版模块详情

### 3.1 compliance 模块

**路径**：`commercial/compliance/`

**职责**：AI敏感检查、内容过滤、字段映射

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | - | ✅ |
| `ai_sensitive_checker.py` | AI敏感词检测 | `AISensitiveCheckResult`, `AISensitiveChecker` | ✅ |
| `content_filter.py` | 敏感内容过滤 | `SensitiveMatch`, `ContentFilterResult`, `SensitiveContentFilter` | ✅ |
| `field_mapper.py` | 领域映射 | `FieldMappingRule`, `FieldMapper` | ✅ |
| `source_filter.py` | 信源过滤 | `SourceFilterResult`, `CommercialSourceFilter` | ✅ |

---

### 3.2 services 模块

**路径**：`commercial/services/`

**职责**：商业版邮件服务

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | - | ✅ |
| `email_service.py` | 商业版邮件服务 | `CommercialEmailService` | ✅ |

---

### 3.3 subscription 模块

**路径**：`commercial/subscription/`

**职责**：订阅者管理

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | - | ✅ |
| `subscriber_manager.py` | 订阅者管理 | `Subscriber`, `SubscriberManager` | ✅ |

---

### 3.4 web 模块

**路径**：`commercial/web/`

**职责**：Flask Web应用

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | - | ✅ |
| `app.py` | Flask Web应用 | 路由: `index()`, `subscribe()`, `admin()`, API接口等 | ✅ |

---

## 四、模块依赖关系图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              模块依赖关系                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┐     ┌───────────┐     ┌─────────┐                            │
│  │ config  │ ←── │  所有模块  │ ←── │ models  │                            │
│  └─────────┘     └───────────┘     └─────────┘                            │
│                                                                             │
│  核心流程:                                                                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐              │
│  │collector │ →  │processor │ →  │ filters  │ →  │ storage │              │
│  └──────────┘    └──────────┘    └──────────┘    └─────────┘              │
│       │              │               │               │                     │
│       └──────────────┴───────────────┴───────────────┘                     │
│                              ↓                                              │
│                        ┌─────────┐                                         │
│                        │  utils  │                                         │
│                        └─────────┘                                         │
│                                                                             │
│  商业版:                                                                     │
│  ┌────────────┐    ┌───────────┐    ┌─────────────┐    ┌─────────┐        │
│  │compliance  │ →  │   web     │ ←  │subscription │ ←  │services │        │
│  └────────────┘    └───────────┘    └─────────────┘    └─────────┘        │
│                                                                             │
│  ❌ scheduler: 独立模块，未被其他模块导入                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 五、校验清单

- [x] 所有模块是否已扫描完成？ → 13个模块全部扫描
- [x] 每个文件的职责是否清晰？ → 已列出所有文件职责
- [x] 主要类/函数是否已列出？ → 已列出核心类和函数
- [x] 与Layer 0文档是否一致？ → 模块数量、名称一致
- [x] 文件数量是否准确？ → processor=19, service=2 已修正
- [x] 每个模块的使用状态是否标注？ → 已补充状态分析
- [x] 废弃文件是否有说明？ → content_filter.py已说明废弃原因

---

## 六、待解决问题

1. **领域定义不一致**：`data_models.py`（10类）与 `lightweight_classifier.py`（8类）不一致，需要在Layer 2核实实际使用

---

## 七、下一步

Layer 1 模块层已完成，下一步进入 **Layer 2: 函数层**，逐模块扫描所有函数的详细签名和说明。
