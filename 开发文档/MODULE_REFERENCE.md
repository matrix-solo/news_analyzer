# 模块函数说明文档

> 本文档由 Layer 5 整合层自动生成，整合了 Layer 0-4 的所有信息。
> 
> 生成日期：2026-03-22

---

## 一、概述

### 1.1 项目简介

新闻分析工作流系统，实现从RSS采集、AI处理、热度评分到报告生成的完整流程。

### 1.2 技术栈

| 技术 | 用途 |
|-----|------|
| Python 3.10+ | 主要开发语言 |
| SQLite + FTS5 | 数据存储与全文搜索 |
| OpenAI API | AI处理（翻译、摘要、分类） |
| BGE-M3 | 向量嵌入 |
| Flask | Web服务（商业版） |

### 1.3 模块架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        新闻分析工作流系统                          │
├─────────────────────────────────────────────────────────────────┤
│  核心模块                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  collector   │  │  processor   │  │   storage    │          │
│  │   采集模块    │  │   处理模块    │  │   存储模块    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   filters    │  │   models     │  │    config    │          │
│  │   过滤模块    │  │   数据模型    │  │   配置模块    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │  scheduler   │  │   service    │                            │
│  │   调度模块    │  │   服务模块    │                            │
│  └──────────────┘  └──────────────┘                            │
├─────────────────────────────────────────────────────────────────┤
│  辅助模块                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    utils     │  │  commercial  │  │   scripts    │          │
│  │   工具模块    │  │   商业版模块   │  │   脚本工具    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 1.4 统计概览

| 统计项 | 数量 |
|-------|------|
| 模块数 | 13 |
| 文件数 | 84 |
| 类数 | 133 |
| 模块级函数 | 154 |
| 类方法 | ~410 |
| 函数总计 | ~564 |

---

## 二、核心模块

### 2.1 collector 采集模块

**路径**：`core/collector/`

**职责**：RSS采集、爬虫、信源管理、增量采集

**统计**：18个类，5个模块级函数，约80个类方法

**使用状态**：✅ 正常使用

#### 2.1.1 主要类

| 类名 | 文件 | 功能 | 状态 |
|-----|------|------|------|
| `RSSSource` | sources.py | RSS信源配置 | ✅ |
| `RSSSourceManager` | sources.py | 信源管理器 | ✅ |
| `RSSCollector` | collector.py | RSS采集器 | ✅ |
| `RSSIncrementalCollector` | incremental_collector.py | 增量采集器 | ✅ |
| `RSSParser` | parser.py | RSS解析器 | ✅ |
| `BaseCrawler` | crawlers/base.py | 爬虫基类 | ✅ |
| `CrawlerFactory` | crawlers/factory.py | 爬虫工厂 | ✅ |

#### 2.1.2 主要方法

| 方法 | 所属类 | 功能 |
|-----|-------|------|
| `fetch_feed(source)` | RSSCollector | 获取RSS订阅内容 |
| `fetch_all(type)` | RSSCollector | 获取所有RSS源 |
| `get_enabled_sources()` | RSSSourceManager | 获取启用的信源 |
| `get_source(name)` | RSSSourceManager | 获取指定信源 |

#### 2.1.3 模块级函数

| 函数 | 文件 | 功能 |
|-----|------|------|
| `run_once()` | incremental_collector.py | 单次采集 |
| `run_daemon(interval)` | incremental_collector.py | 守护进程采集 |

---

### 2.2 processor 处理模块

**路径**：`core/processor/`

**职责**：AI处理、热度评分、历史关联、报告生成

**统计**：38个类，36个模块级函数，100个类方法

**使用状态**：✅ 正常使用

#### 2.2.1 主要类

| 类名 | 文件 | 功能 | 状态 |
|-----|------|------|------|
| `AIProcessor` | ai_processor.py | AI处理器 | ✅ |
| `CombinedProcessor` | combined_processor.py | 合并处理器 | ✅ |
| `DataValidator` | data_validator.py | 数据校验器 | ✅ |
| `LightweightClassifier` | lightweight_classifier.py | 轻量分类器 | ✅ |
| `HeatProcessor` | heat_processor.py | 热度处理器 | ✅ |
| `BGE3HistoryRelationEngine` | history_relation_engine_bge3.py | BGE3关联引擎 | ✅ |
| `ReportGenerator` | generators/report_generator.py | 报告生成器 | ✅ |
| `EntityExtractor` | content_parser.py | 实体提取器 | ✅ |

#### 2.2.2 主要方法

| 方法 | 所属类 | 功能 |
|-----|-------|------|
| `process_news(news)` | CombinedProcessor | 处理单条新闻（翻译+摘要+5W1H+评分） |
| `classify_single(news)` | LightweightClassifier | 单条新闻分类 |
| `calculate_heat_score(news)` | HeatProcessor | 计算热度评分 |
| `find_related_news(target, top_k)` | BGE3HistoryRelationEngine | 查找相关新闻 |
| `generate_brief_report(news_list)` | ReportGenerator | 生成简要报告 |
| `generate_deep_report(news_list)` | ReportGenerator | 生成深度报告 |
| `validate_combined_result(news, result)` | DataValidator | 校验处理结果 |

#### 2.2.3 模块级函数

| 函数 | 文件 | 功能 |
|-----|------|------|
| `get_ai_processor()` | ai_processor.py | 获取AI处理器实例 |
| `get_bge3_engine(history_news)` | history_relation_engine_bge3.py | 获取BGE3引擎实例 |
| `encode_text(text)` | history_relation_engine_bge3.py | 文本向量化 |
| `format_related_section(records)` | history_relation_engine_bge3.py | 格式化相关新闻 |

---

### 2.3 storage 存储模块

**路径**：`core/storage/`

**职责**：数据库操作、文件管理、基线管理

**统计**：7个类，3个模块级函数，约40个类方法

**使用状态**：✅ 正常使用

#### 2.3.1 主要类

| 类名 | 文件 | 功能 | 状态 |
|-----|------|------|------|
| `NewsDatabase` | database.py | 新闻数据库管理器 | ✅ |
| `ConnectionPool` | database.py | 连接池 | ✅ |
| `StorageManager` | storage_manager.py | 存储管理器 | ✅ |
| `FileManager` | file_manager.py | 文件管理器 | ✅ |

#### 2.3.2 主要方法

| 方法 | 所属类 | 功能 |
|-----|-------|------|
| `insert_news_with_processed(news)` | NewsDatabase | 插入新闻并标记已处理 |
| `insert_raw_news_batch(raw_items)` | NewsDatabase | 批量插入原始数据 |
| `get_recent_news(hours)` | NewsDatabase | 获取最近N小时新闻 |
| `get_history_news(days)` | NewsDatabase | 获取最近N天新闻 |
| `search_by_keywords(keywords, days)` | NewsDatabase | 关键词搜索 |
| `search_by_domain(domain, hours)` | NewsDatabase | 按领域查询 |
| `filter_processed_ids(news_ids)` | NewsDatabase | 批量检查已处理ID |
| `update_news(news_id, updates)` | NewsDatabase | 更新新闻字段 |
| `save_hotboard_cache(cache_data)` | NewsDatabase | 保存热榜缓存 |
| `get_hotboard_cache()` | NewsDatabase | 获取热榜缓存 |
| `backup_database(backup_dir)` | NewsDatabase | 备份数据库 |

#### 2.3.3 模块级函数

| 函数 | 文件 | 功能 |
|-----|------|------|
| `get_db()` | database.py | 获取数据库实例（单例） |

---

### 2.4 filters 过滤模块

**路径**：`core/filters/`

**职责**：内容过滤、去重、信源验证

**统计**：10个类，0个模块级函数，约30个类方法

**使用状态**：⚠️ 部分废弃

#### 2.4.1 主要类

| 类名 | 文件 | 功能 | 状态 |
|-----|------|------|------|
| `ContentFilter` | content_filter.py | 内容过滤器 | ✅ |
| `AIFilterAgent` | ai_filter_agent.py | AI过滤代理 | ✅ |
| `DeduplicationFilter` | deduplication.py | 去重过滤器 | ⚠️ |

#### 2.4.2 主要方法

| 方法 | 所属类 | 功能 |
|-----|-------|------|
| `filter(news_list)` | ContentFilter | 过滤新闻列表 |
| `filter_with_ai(news)` | AIFilterAgent | AI过滤单条新闻 |

---

### 2.5 models 数据模型

**路径**：`core/models/`

**职责**：数据类定义（NewsItem, NewsData等）

**统计**：7个类，0个模块级函数，约15个类方法

**使用状态**：✅ 正常使用

#### 2.5.1 主要类

| 类名 | 文件 | 功能 |
|-----|------|------|
| `NewsItem` | data_models.py | 新闻数据项 |
| `NewsData` | database.py | 新闻数据库结构 |

---

### 2.6 config 配置模块

**路径**：`core/config/`

**职责**：配置加载、模板管理

**统计**：1个类，19个模块级函数，约10个类方法

**使用状态**：✅ 正常使用

#### 2.6.1 主要函数

| 函数 | 文件 | 功能 |
|-----|------|------|
| `get_config()` | loader.py | 获取配置实例 |
| `get_env(key, default)` | loader.py | 获取环境变量 |
| `get_project_root()` | loader.py | 获取项目根目录 |

---

### 2.7 scheduler 调度模块

**路径**：`core/scheduler/`

**职责**：任务调度

**统计**：2个类，1个模块级函数，约15个类方法

**使用状态**：❌ 未使用

---

### 2.8 service 服务模块

**路径**：`core/service/`

**职责**：健康监控

**统计**：2个类，1个模块级函数，约10个类方法

**使用状态**：✅ 正常使用

---

### 2.9 utils 工具模块

**路径**：`core/utils/`

**职责**：工具函数（日志、HTTP、邮件等）

**统计**：36个类，73个模块级函数，约60个类方法

**使用状态**：✅ 正常使用

#### 2.9.1 主要函数

| 函数 | 文件 | 功能 |
|-----|------|------|
| `get_source_score(source_name)` | source_scorer.py | 获取信源评分 |
| `get_translated_title(news)` | text_utils.py | 获取翻译标题 |
| `format_tags(tags)` | text_utils.py | 格式化标签 |

---

## 三、商业版模块

### 3.1 compliance 合规模块

**路径**：`commercial/compliance/`

**职责**：AI敏感检查、内容过滤、字段映射

**统计**：9个类，2个模块级函数，约30个类方法

**使用状态**：✅ 正常使用

---

### 3.2 services 服务模块

**路径**：`commercial/services/`

**职责**：商业版邮件服务

**统计**：1个类，1个模块级函数，约10个类方法

**使用状态**：✅ 正常使用

---

### 3.3 subscription 订阅模块

**路径**：`commercial/subscription/`

**职责**：订阅者管理

**统计**：2个类，0个模块级函数，约10个类方法

**使用状态**：✅ 正常使用

---

### 3.4 web Web模块

**路径**：`commercial/web/`

**职责**：Flask Web应用

**统计**：0个类，13个模块级函数

**使用状态**：✅ 正常使用

---

## 四、函数索引

### 4.1 按字母排序（A-F）

| 函数名 | 模块 | 功能 |
|-------|------|------|
| `backup_database()` | storage | 备份数据库 |
| `calculate_heat_score()` | processor | 计算热度评分 |
| `check_news_exists()` | storage | 检查新闻是否存在 |
| `check_news_processed()` | storage | 检查新闻是否已处理 |
| `classify_single()` | processor | 单条新闻分类 |
| `cleanup_raw_news()` | storage | 清理原始数据 |
| `encode_text()` | processor | 文本向量化 |
| `fetch_feed()` | collector | 获取RSS订阅 |
| `filter_processed_ids()` | storage | 批量检查已处理ID |
| `format_related_section()` | processor | 格式化相关新闻 |

### 4.2 按字母排序（G-O）

| 函数名 | 模块 | 功能 |
|-------|------|------|
| `get_ai_processor()` | processor | 获取AI处理器 |
| `get_bge3_engine()` | processor | 获取BGE3引擎 |
| `get_config()` | config | 获取配置实例 |
| `get_db()` | storage | 获取数据库实例 |
| `get_env()` | config | 获取环境变量 |
| `get_hotboard_cache()` | storage | 获取热榜缓存 |
| `get_recent_news()` | storage | 获取最近新闻 |
| `get_source_score()` | utils | 获取信源评分 |
| `get_stats()` | storage | 获取统计信息 |
| `insert_news_with_processed()` | storage | 插入新闻 |
| `insert_raw_news_batch()` | storage | 批量插入原始数据 |

### 4.3 按字母排序（P-Z）

| 函数名 | 模块 | 功能 |
|-------|------|------|
| `process_news()` | processor | 处理单条新闻 |
| `run_daemon()` | collector | 守护进程采集 |
| `run_once()` | collector | 单次采集 |
| `save_hotboard_cache()` | storage | 保存热榜缓存 |
| `search_by_domain()` | storage | 按领域查询 |
| `search_by_keywords()` | storage | 关键词搜索 |
| `update_news()` | storage | 更新新闻字段 |
| `validate_combined_result()` | processor | 校验处理结果 |

---

## 五、关联异常说明

### 5.1 未关联函数

以下函数存在但计算结果未写入数据库：

| 模块 | 函数 | 问题 |
|-----|------|------|
| utils/source_scorer.py | `get_source_score()` | 有读取无写入，`source_score`字段未填充 |
| processor/combined_processor.py | `_evaluate_accuracy()` | 计算结果未写入`accuracy_score`字段 |

### 5.2 建议修复

1. 添加`source_score`写入逻辑
2. 将`accuracy_score`计算结果存入数据库
3. 确认`initial_domain`/`initial_tags`是否废弃

---

## 六、业务流程参考

### 6.1 Task1 采集流程（11阶段）

```
阶段1: RSS采集 → 阶段2: 字段标准化 → 阶段3: 存原始数据
→ 阶段4: 轻量分类 → 阶段5: 三层过滤 → 阶段6: AI处理
→ 阶段7: 数据校验 → 阶段8: 向量化 → 阶段9: 热度评分
→ 阶段10: 存入DB → 阶段11: 修复数据
```

### 6.2 Task2 报告流程

```
阶段1: 读近24h → 阶段3: 简要报告 → 阶段4: 深度报告 → 阶段6: 发送邮件
```

---

*文档结束*
