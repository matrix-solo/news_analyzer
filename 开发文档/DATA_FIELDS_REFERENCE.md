# 数据字段文档

> 本文档由 Layer 5 整合层自动生成，整合了 Layer 0-4 的所有信息。
> 
> 生成日期：2026-03-22

---

## 一、概述

### 1.1 数据库架构

| 属性 | 值 |
|-----|-----|
| **数据库类型** | SQLite |
| **数据库路径** | `data/news.db` |
| **存储模式** | WAL (Write-Ahead Logging) |
| **表数量** | 18 |

### 1.2 表分类

| 分类 | 表名 | 数量 | 写入接口状态 |
|-----|------|-----|-------------|
| **核心业务表** | news, raw_news, processed_news, rejected_news | 4 | ✅ news/raw_news/processed_news有写入；⚠️ rejected_news无写入代码 |
| **FTS5全文搜索** | news_fts, news_fts_config, news_fts_data, news_fts_docsize, news_fts_idx | 5 | 🔧 触发器自动同步 |
| **知识图谱** | entities, news_entities, event_clusters, knowledge_index | 4 | ⚠️ entities/news_entities有写入；event_clusters/knowledge_index预留 |
| **辅助功能** | hotboard_cache, market_context | 2 | ✅ hotboard_cache有写入；⚠️ market_context预留 |
| **历史/测试** | news_raw, persistence_test, sqlite_sequence | 3 | ❌ news_raw已废弃 |

### 1.3 字段统计

| 表名 | 字段数 | 状态 |
|-----|-------|------|
| news | 47 | ✅ 核心表 |
| raw_news | 6 | ✅ 活跃 |
| processed_news | 2 | ✅ 活跃 |
| rejected_news | 14 | ⚠️ 遗留 |
| hotboard_cache | 9 | ✅ 活跃 |
| entities | 7 | ✅ 活跃 |
| news_entities | 7 | ✅ 活跃 |
| event_clusters | 9 | ⚠️ 预留 |
| knowledge_index | 3 | ⚠️ 预留 |
| market_context | 4 | ⚠️ 预留 |
| news_raw | 12 | ❌ 废弃 |

---

## 二、核心业务表

### 2.1 news 表（新闻主表）

**用途**：存储所有已处理的新闻数据，是系统的核心表。

**写入函数**：`insert_news_with_processed()`, `update_news()`

**读取函数**：`get_recent_news()`, `search_by_keywords()`, `search_by_domain()` 等

#### 2.1.1 基础信息字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `id` | TEXT | PRIMARY KEY | - | MD5生成 | ✅ 有写入 | 新闻唯一标识（MD5） |
| `title` | TEXT | NOT NULL | - | RSS/API | ✅ 有写入 | 新闻标题 |
| `translated_title` | TEXT | NULL | - | AI翻译 | ✅ 有写入 | 翻译后的标题 |
| `link` | TEXT | NULL | - | RSS/API | ✅ 有写入 | 原文链接 |
| `source` | TEXT | NULL | - | RSS源 | ✅ 有写入 | 信源标识 |
| `source_name` | TEXT | NULL | - | RSS源 | ✅ 有写入 | 信源名称 |
| `pub_date` | TEXT | NULL | - | RSS/API | ✅ 有写入 | 发布时间 |
| `content` | TEXT | NULL | - | 网页抓取 | ✅ 有写入 | 新闻正文 |
| `summary` | TEXT | NULL | - | AI生成 | ✅ 有写入 | 新闻摘要 |

#### 2.1.2 5W1H分析字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `who` | TEXT | NULL | - | AI提取 | ✅ 有写入 | 事件主体（谁） |
| `what` | TEXT | NULL | - | AI提取 | ✅ 有写入 | 事件内容（什么） |
| `when_time` | TEXT | NULL | - | AI提取 | ✅ 有写入 | 事件时间（何时） |
| `where_place` | TEXT | NULL | - | AI提取 | ✅ 有写入 | 事件地点（何地） |
| `why` | TEXT | NULL | - | AI提取 | ✅ 有写入 | 事件原因（为什么） |
| `how` | TEXT | NULL | - | AI提取 | ✅ 有写入 | 事件过程（如何） |

#### 2.1.3 分类标签字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `domain` | TEXT | NULL | - | AI分类 | ✅ 有写入 | 新闻领域 |
| `tags` | TEXT | NULL | - | AI提取 | ✅ 有写入 | 标签列表（JSON） |
| `keywords` | TEXT | NULL | - | AI提取 | ✅ 有写入 | 关键词列表（JSON） |
| `initial_domain` | TEXT | NULL | - | 规则分类 | ❌ 无写入 | 初始领域（待确认废弃） |
| `initial_tags` | TEXT | NULL | - | 规则提取 | ❌ 无写入 | 初始标签（待确认废弃） |

**domain字段实际值**：
- 科技(960), 政治(399), 经济(385), 社会(251), 军事(81)
- 文化(78), 体育(62), 已拒绝(51), 娱乐(30)

#### 2.1.4 评分字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `source_score` | REAL | NULL | - | 规则计算 | ⚠️ 有读取无写入 | 信源评分 |
| `heat_score` | REAL | NULL | - | 热榜匹配 | ✅ 有写入 | 热度评分 |
| `influence_score` | REAL | NULL | - | AI评估 | ✅ 有写入 | 影响力评分 |
| `value_score` | REAL | NULL | - | AI评估 | ✅ 有写入 | 价值评分 |
| `compliance_score` | REAL | NULL | - | 合规检查 | ❌ 无写入 | 合规评分 |
| `final_score` | REAL | NULL | - | 综合计算 | ✅ 有写入 | 最终评分 |
| `classification_confidence` | REAL | NULL | - | AI输出 | ❌ 无写入 | 分类置信度 |
| `accuracy_score` | REAL | NULL | - | 校验计算 | ⚠️ 有计算无存储 | 准确度评分 |

#### 2.1.5 旧版评分字段（已废弃）

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `score` | REAL | ❌ 已废弃，建议删除 |
| `score_timeliness` | REAL | ❌ 已废弃，建议删除 |
| `score_importance` | REAL | ❌ 已废弃，建议删除 |
| `score_credibility` | REAL | ❌ 已废弃，建议删除 |
| `score_impact` | REAL | ❌ 已废弃，建议删除 |
| `source_reliability_score` | REAL | ❌ 已废弃，建议删除 |

#### 2.1.6 处理状态字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `extraction_method` | TEXT | NULL | - | 系统 | ✅ 有写入 | 提取方法标识 |
| `combined_processing_status` | TEXT | NULL | - | 系统 | ✅ 有写入 | 处理状态 |
| `validation_status` | TEXT | NULL | - | 校验 | ✅ 有写入 | 校验状态 |
| `repair_count` | INTEGER | NULL | 0 | 系统 | ✅ 有写入 | 修复次数 |

#### 2.1.7 向量嵌入字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `embedding` | BLOB | NULL | - | BGE-M3 | ✅ 有写入 | 向量嵌入 |
| `embedding_updated_at` | TEXT | NULL | - | 系统 | ✅ 有写入 | 向量更新时间 |

#### 2.1.8 原始数据字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `raw_item_json` | TEXT | NULL | - | RSS/API | ✅ 有写入 | 原始JSON数据 |
| `raw_news_id` | INTEGER | NULL | - | raw_news表 | ✅ 有写入 | 原始数据ID |
| `original_summary` | TEXT | NULL | - | AI生成 | ⚠️ 有计算无存储 | 原始摘要 |
| `system_summary` | TEXT | NULL | - | 系统 | ❌ 无写入 | 系统摘要（待确认） |

#### 2.1.9 系统字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `created_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 系统 | ✅ 系统自动 | 创建时间 |
| `updated_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 系统 | ✅ 系统自动 | 更新时间 |
| `access_time` | DATETIME | NULL | - | 系统 | ❌ 无写入 | 访问时间（待确认） |

---

### 2.2 raw_news 表（原始新闻表）

**用途**：存储采集的原始新闻数据，用于去重和追溯。

**写入函数**：`insert_raw_news_batch()`

**读取函数**：`get_unprocessed_raw_news()`, `get_raw_news_by_id()`

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | INTEGER | PRIMARY KEY | AUTOINCREMENT | 自增主键 |
| `news_id` | TEXT | NULL | - | 新闻唯一标识（MD5） |
| `raw_json` | TEXT | NULL | - | 原始JSON数据 |
| `source_name` | TEXT | NULL | - | 信源名称 |
| `fetched_at` | TEXT | NULL | - | 采集时间 |
| `processed` | INTEGER | NULL | 0 | 是否已处理（0/1） |

---

### 2.3 processed_news 表（已处理表）

**用途**：记录已处理的新闻ID，用于增量采集去重。

**写入函数**：`insert_news_with_processed()`

**读取函数**：`filter_processed_ids()`, `check_news_processed()`

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `news_id` | TEXT | PRIMARY KEY | - | 新闻唯一标识 |
| `processed_at` | TEXT | NULL | - | 处理时间 |

---

### 2.4 rejected_news 表（被拒绝表）

**用途**：存储被过滤拒绝的新闻数据。

**状态**：⚠️ 有524条记录，但无Python写入代码

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `id` | INTEGER | 自增主键 |
| `news_id` | TEXT | 新闻唯一标识 |
| `title` | TEXT | 新闻标题 |
| `link` | TEXT | 原文链接 |
| `source_name` | TEXT | 信源名称 |
| `pub_date` | TEXT | 发布时间 |
| `content` | TEXT | 新闻正文 |
| `reject_reason` | TEXT | 拒绝原因 |
| `reject_type` | TEXT | 拒绝类型 |
| `is_factual` | INTEGER | 是否为事实新闻 |
| `content_type` | TEXT | 内容类型 |
| `w5h1_score` | REAL | 5W1H完整度评分 |
| `confidence` | REAL | 置信度 |
| `created_at` | DATETIME | 创建时间 |

**reject_type分布**：评论(167), 事实新闻(116), 广告(64), 预测(46), 其他(40), 观点(31), 不完整(29), 重复(19), 低质量(12)

---

### 2.5 hotboard_cache 表（热榜缓存表）

**用途**：缓存各平台热榜数据，用于热度评分。

**写入函数**：`save_hotboard_cache()`

**读取函数**：`get_hotboard_cache()`, `get_hotboard_stats()`

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | INTEGER | PRIMARY KEY | AUTOINCREMENT | 自增主键 |
| `platform` | TEXT | NULL | - | 平台名称（weibo/zhihu等） |
| `rank` | INTEGER | NULL | - | 排名 |
| `title` | TEXT | NULL | - | 热榜标题 |
| `hot_value` | TEXT | NULL | - | 热度值 |
| `url` | TEXT | NULL | - | 链接 |
| `embedding` | BLOB | NULL | - | 向量嵌入 |
| `expires_at` | TEXT | NULL | - | 过期时间 |
| `fetched_at` | TEXT | NULL | - | 采集时间 |

---

## 三、知识图谱表

### 3.1 entities 表（实体表）

**用途**：存储提取的实体信息（人物、组织、地点等）。

**写入函数**：`EntityExtractor._upsert_entity()`

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | INTEGER | PRIMARY KEY | AUTOINCREMENT | 自增主键 |
| `name` | TEXT | NULL | - | 实体名称 |
| `type` | TEXT | NULL | - | 实体类型（PERSON/ORG/LOC等） |
| `subtype` | TEXT | NULL | - | 子类型（预留） |
| `normalized_name` | TEXT | NULL | - | 标准化名称 |
| `created_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 更新时间 |

---

### 3.2 news_entities 表（新闻-实体关联表）

**用途**：存储新闻与实体的关联关系。

**写入函数**：`EntityExtractor._upsert_news_entity()`

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | INTEGER | PRIMARY KEY | AUTOINCREMENT | 自增主键 |
| `news_id` | TEXT | NULL | - | 新闻ID |
| `entity_id` | INTEGER | NULL | - | 实体ID |
| `role` | TEXT | NULL | - | 实体角色 |
| `weight` | REAL | NULL | - | 权重 |
| `extra` | TEXT | NULL | - | 扩展信息（预留） |
| `created_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 创建时间 |

---

### 3.3 event_clusters 表（事件聚类表）

**用途**：存储事件聚类结果。

**状态**：⚠️ 预留表，暂无活跃写入函数

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `id` | INTEGER | 自增主键 |
| `cluster_date` | TEXT | 聚类日期 |
| `domain` | TEXT | 领域 |
| `event_name` | TEXT | 事件名称 |
| `news_ids` | TEXT | 新闻ID列表（JSON） |
| `representative_id` | TEXT | 代表新闻ID |
| `reason` | TEXT | 聚类原因 |
| `cluster_metadata` | TEXT | 元数据（JSON） |
| `created_at` | DATETIME | 创建时间 |

---

### 3.4 knowledge_index 表（知识索引表）

**用途**：存储知识库索引信息。

**状态**：⚠️ 预留表，暂无活跃写入函数

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `news_id` | TEXT | 新闻ID |
| `indexed_at` | TEXT | 索引时间 |
| `chunk_count` | INTEGER | 分块数量 |

---

## 四、辅助表

### 4.1 market_context 表（市场上下文表）

**用途**：存储市场背景信息。

**状态**：⚠️ 预留表，暂无活跃写入函数

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `id` | INTEGER | 自增主键 |
| `date` | TEXT | 日期 |
| `snapshot_json` | TEXT | 市场快照（JSON） |
| `fetched_at` | TEXT | 采集时间 |

---

## 五、字段数据流追踪

### 5.1 采集阶段

```
RSS/API → raw_news表
├── news_id (MD5生成)
├── raw_json (原始数据)
├── source_name (信源名称)
└── fetched_at (采集时间)
```

### 5.2 处理阶段

```
raw_news → processor → news表
├── 基础字段: title, link, source, pub_date, content
├── 翻译: translated_title
├── 摘要: summary
├── 5W1H: who, what, when_time, where_place, why, how
├── 分类: domain, tags, keywords
├── 评分: influence_score, value_score, heat_score, final_score
└── 向量: embedding
```

### 5.3 存储阶段

```
news表 → processed_news表
├── news_id
└── processed_at
```

---

## 六、关联异常说明

### 6.1 未关联字段汇总

| 优先级 | 字段 | 问题 | 建议 |
|-------|------|------|------|
| 🔴 高 | `source_score` | 有读取无写入 | 添加写入逻辑 |
| 🔴 高 | `rejected_news.*` | 无Python INSERT代码 | 确认数据来源 |
| 🟡 中 | `initial_domain` | 无写入代码 | 确认是否废弃 |
| 🟡 中 | `initial_tags` | 无写入代码 | 确认是否废弃 |
| 🟡 中 | `compliance_score` | 无写入代码 | 检查commercial模块 |
| 🟡 中 | `accuracy_score` | 有计算无存储 | 添加存储逻辑 |
| 🟢 低 | `score_*` (6个) | 已废弃 | 建议删除 |

---

## 七、字段索引

### 7.1 按字母排序（A-F）

| 字段名 | 所属表 | 类型 | 说明 |
|-------|-------|------|------|
| `access_time` | news | DATETIME | 访问时间 |
| `accuracy_score` | news | REAL | 准确度评分 |
| `chunk_count` | knowledge_index | INTEGER | 分块数量 |
| `classification_confidence` | news | REAL | 分类置信度 |
| `cluster_date` | event_clusters | TEXT | 聚类日期 |
| `cluster_metadata` | event_clusters | TEXT | 元数据 |
| `compliance_score` | news | REAL | 合规评分 |
| `content` | news, rejected_news | TEXT | 新闻正文 |
| `content_type` | rejected_news | TEXT | 内容类型 |
| `created_at` | 多表 | DATETIME | 创建时间 |
| `date` | market_context | TEXT | 日期 |
| `domain` | news, event_clusters | TEXT | 领域 |
| `embedding` | news, hotboard_cache | BLOB | 向量嵌入 |
| `embedding_updated_at` | news | TEXT | 向量更新时间 |
| `event_name` | event_clusters | TEXT | 事件名称 |
| `expires_at` | hotboard_cache | TEXT | 过期时间 |
| `extra` | news_entities | TEXT | 扩展信息 |
| `fetched_at` | 多表 | TEXT | 采集时间 |
| `final_score` | news | REAL | 最终评分 |
| `heat_score` | news | REAL | 热度评分 |
| `hot_value` | hotboard_cache | TEXT | 热度值 |
| `how` | news | TEXT | 事件过程 |
| `id` | 多表 | INTEGER/TEXT | 主键 |
| `influence_score` | news | REAL | 影响力评分 |
| `initial_domain` | news | TEXT | 初始领域 |
| `initial_tags` | news | TEXT | 初始标签 |
| `is_factual` | rejected_news | INTEGER | 是否事实新闻 |
| `keywords` | news | TEXT | 关键词列表 |
| `link` | news, rejected_news | TEXT | 原文链接 |
| `name` | entities | TEXT | 实体名称 |
| `news_id` | 多表 | TEXT | 新闻ID |
| `normalized_name` | entities | TEXT | 标准化名称 |
| `platform` | hotboard_cache | TEXT | 平台名称 |
| `processed` | raw_news | INTEGER | 是否已处理 |
| `processed_at` | processed_news | TEXT | 处理时间 |
| `pub_date` | news, rejected_news | TEXT | 发布时间 |
| `rank` | hotboard_cache | INTEGER | 排名 |
| `raw_item_json` | news | TEXT | 原始JSON |
| `raw_json` | raw_news | TEXT | 原始JSON |
| `raw_news_id` | news | INTEGER | 原始数据ID |
| `reason` | event_clusters | TEXT | 聚类原因 |
| `reject_reason` | rejected_news | TEXT | 拒绝原因 |
| `reject_type` | rejected_news | TEXT | 拒绝类型 |
| `repair_count` | news | INTEGER | 修复次数 |
| `representative_id` | event_clusters | TEXT | 代表新闻ID |
| `role` | news_entities | TEXT | 实体角色 |
| `score` | news | REAL | 综合评分（已废弃） |
| `score_credibility` | news | REAL | 可信度评分（已废弃） |
| `score_impact` | news | REAL | 影响力评分（已废弃） |
| `score_importance` | news | REAL | 重要性评分（已废弃） |
| `score_timeliness` | news | REAL | 时效性评分（已废弃） |
| `snapshot_json` | market_context | TEXT | 市场快照 |
| `source` | news | TEXT | 信源标识 |
| `source_name` | 多表 | TEXT | 信源名称 |
| `source_reliability_score` | news | REAL | 信源可靠性（已废弃） |
| `source_score` | news | REAL | 信源评分 |
| `subtype` | entities | TEXT | 子类型 |
| `summary` | news | TEXT | 新闻摘要 |
| `system_summary` | news | TEXT | 系统摘要 |
| `tags` | news | TEXT | 标签列表 |
| `title` | 多表 | TEXT | 标题 |
| `translated_title` | news | TEXT | 翻译标题 |
| `type` | entities | TEXT | 实体类型 |
| `updated_at` | 多表 | DATETIME | 更新时间 |
| `url` | hotboard_cache | TEXT | 链接 |
| `validation_status` | news | TEXT | 校验状态 |
| `value_score` | news | REAL | 价值评分 |
| `w5h1_score` | rejected_news | REAL | 5W1H完整度 |
| `weight` | news_entities | REAL | 权重 |
| `what` | news | TEXT | 事件内容 |
| `when_time` | news | TEXT | 事件时间 |
| `where_place` | news | TEXT | 事件地点 |
| `who` | news | TEXT | 事件主体 |
| `why` | news | TEXT | 事件原因 |

---

*文档结束*
