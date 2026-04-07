# Layer 1: 模块层文档

---

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|-----|------|------|-----|
| v1.0 | 2026-03-21 | ⏸️ 已反馈 | 完成所有模块扫描 |
| v1.2 | 2026-04-07 | ✅ 已完成 | Phase 1 清理：删除死代码模块、更新模块状态和文件数量 |
| v1.1 | 2026-03-21 | ✅ 已完成 | 修正文件数量、补充模块状态分析、修正领域定义差异 |

---

## 上层文档同步检查

**参考文档**：`阶段一_文档生成工作记录.md` (Layer 0 v0.5)

| 检查项 | 状态 | 说明 |
|-------|------|-----|
| 模块数量 | ✅ 一致 | core(8) + commercial(4) = 12个（scheduler 已删除） |
| 模块名称 | ✅ 一致 | collector, processor, storage, filters, models, config, service, utils |
| 文件数量 | ✅ 已修正 | 见下文详细统计 |

---

## 一、模块总览

### 1.1 模块清单

| 序号 | 模块名 | 路径 | 类型 | 文件数 | 使用状态 |
|-----|-------|------|------|-------|---------|
| 1 | collector | core/collector/ | 核心 | 11 | ✅ 正常使用 |
| 2 | processor | core/processor/ | 核心 | 17 | ✅ 正常使用 |
| 3 | storage | core/storage/ | 核心 | 3 | ✅ 正常使用 |
| 4 | filters | core/filters/ | 核心 | 2 | ✅ 正常使用 |
| 5 | models | core/models/ | 核心 | 2 | ✅ 正常使用 |
| 6 | config | core/config/ | 核心 | 3 | ✅ 正常使用 |
| 7 | service | core/service/ | 核心 | 1 | ✅ 正常使用 |
| 8 | utils | core/utils/ | 核心 | 19 | ✅ 正常使用 |
| 9 | compliance | commercial/compliance/ | 商业版 | 5 | ✅ 正常使用 |
| 10 | services | commercial/services/ | 商业版 | 2 | ✅ 正常使用 |
| 11 | subscription | commercial/subscription/ | 商业版 | 2 | ✅ 正常使用 |
| 12 | web | commercial/web/ | 商业版 | 2 | ✅ 正常使用 |

**总计**：12个模块，~69个Python文件（Phase 1 清理后删除 17 个死代码文件）

### 1.2 使用状态说明

| 状态 | 含义 | 模块 |
|-----|------|-----|
| ✅ 正常使用 | 模块被项目实际调用 | collector, processor, storage, filters, models, config, service, utils, compliance, services, subscription, web |

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
| `combined_processor.py` | 合并处理器(含BACKUP兜底) | `CombinedProcessor` (BACKUP provider fallback, DefaultValues) | ✅ |
| `content_parser.py` | 内容解析 | `ParseConfidence`, `ParseResult`, `ParsingRules`, `RuleBasedParser`, `ExtractedEntity`, `EntityExtractor` | ✅ |
| `data_validator.py` | 数据验证 | `DataValidator` | ✅ |
| `depth_analyzer.py` | 深度分析 | `DepthAnalysis`, `DepthAnalyzer` | ✅ |
| `field_normalizer.py` | 字段标准化 | `FieldNormalizer` | ✅ |
| `heat_processor.py` | 热度评分(配置驱动) | `HeatProcessor` (相似度阈值从配置读取) | ✅ |
| `history_relation_engine_bge3.py` | BGE-M3历史关联 | `RelatedRecord`, `_FAISSIndex`, `BGE3HistoryRelationEngine` | ✅ |
| `history_relation_engine_fulltext.py` | 全文历史关联 | `FullTextRelatedRecord`, `_FAISSIndex`, `BGE3FullTextEngine` | ✅ |
| `investment_advisor.py` | 投资顾问 | `InvestmentAdvice`, `MarketImpact`, `InvestmentAdvisor` | ✅ |
| `lightweight_classifier.py` | 轻量级分类(配置驱动) | `LightweightClassifier` (置信度阈值从配置读取) | ✅ |
| `generators/__init__.py` | generators子模块入口 | 导出: ReportGenerator | ✅ |
| `generators/report_generator.py` | 报告生成器 | `DomainContext`, `ReportGenerator` | ✅ |

**模块架构**：
```
核心AI层 → 分类层 → 解析层 → 处理层 → 验证层 → 评分层 → 关联层 → 分析层 → 报告层
```

**设计说明**：`generators/`子目录单独存在的原因：
1. **职责分离**：报告生成是独立功能域，与数据处理逻辑分离
2. **扩展性**：未来可添加更多生成器（图表生成器、PDF生成器等）
3. **代码整洁**：processor模块文件较多（17个），抽离报告生成减少顶层文件

---

### 2.3 storage 模块

**路径**：`core/storage/`

**职责**：数据库操作、文件管理

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | 导出: `NewsDatabase`, `get_db` | ✅ |
| `database.py` | SQLite数据库管理 | `NewsData`, `ConnectionPool`, `NewsDatabase` | ✅ |
| `file_manager.py` | 文件管理 + 原始新闻保存 | `FileManager`, `save_original_news()` | ✅ |

---

### 2.4 filters 模块

**路径**：`core/filters/`

**职责**：信源验证

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `__init__.py` | 模块入口 | 导出: SourceValidator, ValidationResult | ✅ |
| `source_validator.py` | 信源校验(白名单+可信度) | `ValidationResult`, `SourceValidator` | ✅ |

**清理说明**（2026-04-07）：
- `content_filter.py` 已删除（功能有限，未被主流程使用）
- `deduplication.py` 已删除（去重已内联到 task1_collector）
- `ai_filter_agent.py` 已删除（BACKUP provider fallback 已合并到 CombinedProcessor）

**当前过滤流程**：
```
白名单校验 + 可信度校验（SourceValidator）→ 历史去重（task1_collector 内联）→ AI合并处理（CombinedProcessor）
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

**配置文件**：
- `core_config.yaml`: 核心配置（评分权重、Tier映射、热度规则、AI处理参数）
- `report_templates.yaml`: 报告模板

**清理说明**（2026-04-07）：
- `report_templates.py` 已删除（被 report_templates.yaml 替代）
- knowledge 配置段已从 core_config.yaml 删除

---

### 2.7 service 模块

**路径**：`core/service/`

**职责**：健康监控

**使用状态**：✅ 正常使用

**文件清单**：

| 文件名 | 职责 | 主要类/函数 | 状态 |
|-------|------|-----------|------|
| `health_monitor/health_monitor.py` | 健康监控器 | `HealthMonitor`, `get_health_monitor()` | ✅ |

**清理说明**（2026-04-07）：
- `monitoring_data.py` 已删除（未被任何代码导入）

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
| **错误处理** | `error_handling.py` | 错误处理 | `NewsAnalyzerError`, `error_handler()` | ✅ |
| **监控追踪** | `heartbeat.py` | 心跳监控 | `HeartbeatStatus`, `HeartbeatMonitor` | ✅ |
| | `performance.py` | 性能监控 | `PerformanceMetric`, `PerformanceMonitor`, `timed()` | ✅ |
| | `workflow_timer.py` | 工作流时间追踪 | `StageMetric`, `WorkflowRun`, `WorkflowTimer` | ✅ |
| **热榜数据** | `hotboard_fetcher.py` | 热榜获取 | `HotItem`, `HotboardFetcher` | ⚠️ 已弃用 |
| | `hotboard_manager.py` | 热榜管理 | `HotItem`, `HotboardCache`, `HotboardManager` | ✅ |
| **采集相关** | `collection_config.py` | 采集配置 | `CollectionConfigManager` | ✅ |
| | `incremental_tracker.py` | 增量追踪 | `IncrementalTracker` | ✅ |
| | `source_scorer.py` | 信源评分(配置驱动) | `get_source_score()`, `get_scoring_config()`, `calc_final_score()` | ✅ |
| **日志系统** | `log_utils.py` | 日志脱敏 | `SanitizedLogger`, `sanitize_text()` | ✅ |
| **报告生成** | `md2pdf.py` | Markdown转PDF | `create_pdf_from_md()`, `convert_md_file_to_pdf()` | ✅ |
| | `email_sender.py` | 邮件发送 | `send_email_with_attachments()`, `send_report_email()` | ✅ |
| **市场数据** | `market_data_fetcher.py` | 市场数据获取 | `MarketSnapshot`, `MarketDataFetcher` | ✅ |
| **工具函数** | `text_utils.py` | 文本处理 | `get_news_title()`, `parse_json_str()` | ✅ |
| | `task_lock.py` | 任务锁 | `TaskLock`, `task_lock()` | ✅ |
| **默认值** | `defaults.py` | 统一默认值常量 | `DefaultValues` | ✅ |
| 入口 | `__init__.py` | 模块入口 | 导出HTTP相关功能 | ✅ |

**清理说明**（2026-04-07）：已删除 8 个未使用模块：proxy_config.py, cache.py, errors.py, monitoring.py, logging_config.py, chart_generator.py, security.py, api_optimizer.py

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
│  ❌ scheduler: 已删除（2026-04-07 Phase 1 清理）                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 五、校验清单

- [x] 所有模块是否已扫描完成？ → 12个模块全部扫描（scheduler 已删除）
- [x] 每个文件的职责是否清晰？ → 已列出所有文件职责
- [x] 主要类/函数是否已列出？ → 已列出核心类和函数
- [x] 与Layer 0文档是否一致？ → 模块数量、名称一致
- [x] 文件数量是否准确？ → Phase 1 清理后已更新
- [x] 每个模块的使用状态是否标注？ → 已补充状态分析
- [x] 废弃文件是否有说明？ → Phase 1 已删除所有死代码文件（17个）

---

## 六、待解决问题

1. **领域定义不一致**：`data_models.py`（10类）与 `lightweight_classifier.py`（8类）不一致，需要在Layer 2核实实际使用

---

## 七、下一步

Layer 1 模块层已完成，下一步进入 **Layer 2: 函数层**，逐模块扫描所有函数的详细签名和说明。
