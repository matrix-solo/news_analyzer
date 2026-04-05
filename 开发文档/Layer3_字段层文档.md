# Layer 3: 字段层文档

---

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|-----|------|------|-----|
| v3.0 | 2026-03-22 | ✅ 已完成 | 完成数据库Schema扫描 |
| v3.1 | 2026-03-22 | ✅ 已完成 | 修正上层文档同步检查、添加表写入接口状态、验证领域定义、更新待解决问题调查结论 |
| v3.2 | 2026-03-22 | ✅ 已完成 | 反向更新：根据Layer 4关联异常报告，标注字段关联状态 |
| v3.3 | 2026-03-25 | ✅ 已完成 | 阶段6-7深度分析：发现文档与实际Schema严重不符，标注虚构字段 |

---

## 上层文档同步检查

**参考文档**：`阶段一_文档生成工作记录.md` (Layer 0 v0.5)

| 检查项 | 阶段一记录 | Layer 3实际 | 状态 | 说明 |
|-------|-----------|------------|------|-----|
| 数据库表数量 | 18个 | 18个 | ✅ 一致 | - |
| 核心业务表 | 4个 | 4个 | ✅ 一致 | news, raw_news, processed_news, rejected_news |
| FTS5虚拟表 | 5个 | 5个 | ✅ 一致 | news_fts及4个辅助表 |
| 知识图谱表 | 4个 | 4个 | ✅ 一致 | entities, news_entities, event_clusters, knowledge_index |
| 辅助功能表 | 2个 | 2个 | ✅ 一致 | hotboard_cache, market_context |
| 历史/测试表 | 3个 | 3个 | ✅ 一致 | news_raw, persistence_test, sqlite_sequence |

---

## 一、数据库概览

### 1.1 基本信息

| 属性 | 值 |
|-----|-----|
| **数据库路径** | `data/news.db` |
| **数据库类型** | SQLite |
| **表数量** | 18 |
| **核心表** | news (47字段) |
| **存储模式** | WAL (Write-Ahead Logging) |

> ⚠️ **重要发现（v3.3）**：经阶段6-7深度分析，发现INSERT语句只覆盖了30个字段，存在17个字段未被写入的问题。详见第十一章节。

### 1.2 表分类

| 分类 | 表名 | 数量 | 写入接口状态 |
|-----|------|-----|-------------|
| **核心业务表** | news, raw_news, processed_news, rejected_news | 4 | ✅ news/raw_news/processed_news有写入函数；⚠️ rejected_news有数据但无Python写入代码 |
| **FTS5全文搜索** | news_fts, news_fts_config, news_fts_data, news_fts_docsize, news_fts_idx | 5 | 🔧 触发器自动同步 |
| **知识图谱** | entities, news_entities, event_clusters, knowledge_index | 4 | ⚠️ 预留表，暂无活跃写入 |
| **辅助功能** | hotboard_cache, market_context | 2 | ✅ hotboard_cache有写入函数；⚠️ market_context无Python写入代码 |
| **历史/测试** | news_raw, persistence_test, sqlite_sequence | 3 | ❌ news_raw已废弃；🔧 persistence_test为测试用；🔧 sqlite_sequence为系统表 |

**写入接口状态说明**：
- ✅ **正常使用**：有活跃的Python写入函数
- ⚠️ **部分使用/遗留**：有数据但无Python写入代码（可能由外部脚本或已删除代码写入）
- 🔧 **自动/系统**：由触发器或系统自动维护
- ❌ **已废弃**：无写入接口，数据为历史遗留

---

## 二、核心业务表

### 2.1 news 表（新闻主表）

**用途**：存储所有已处理的新闻数据，是系统的核心表。

**字段数量**：47个

#### 2.1.1 基础信息字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 说明 |
|-------|------|------|-------|------|------|
| `id` | TEXT | PK | - | MD5生成 | 新闻唯一标识 |
| `title` | TEXT | NOT NULL | - | RSS/API | 原始标题 |
| `translated_title` | TEXT | NULL | - | AI翻译 | 翻译后的标题 |
| `link` | TEXT | NULL | - | RSS/API | 新闻链接 |
| `source` | TEXT | NULL | - | RSS源 | 信源标识（如reuters） |
| `source_name` | TEXT | NULL | - | RSS源 | 信源名称（如路透社） |
| `pub_date` | DATETIME | NULL | - | RSS/API | 发布时间 |
| `content` | TEXT | NULL | - | 网页抓取 | 新闻正文 |
| `summary` | TEXT | NULL | - | AI生成 | 新闻摘要 |

#### 2.1.2 5W1H分析字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 说明 |
|-------|------|------|-------|------|------|
| `who` | TEXT | NULL | - | AI提取 | 事件主体（谁） |
| `what` | TEXT | NULL | - | AI提取 | 事件内容（什么） |
| `when_time` | TEXT | NULL | - | AI提取 | 事件时间（何时） |
| `where_place` | TEXT | NULL | - | AI提取 | 事件地点（何地） |
| `why` | TEXT | NULL | - | AI提取 | 事件原因（为何） |
| `how` | TEXT | NULL | - | AI提取 | 事件方式（如何） |

#### 2.1.3 分类标签字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `domain` | TEXT | NULL | - | AI分类 | ✅ 有写入 | 新闻领域（政治/经济等） |
| `tags` | TEXT | NULL | - | AI提取 | ✅ 有写入 | 标签列表（JSON数组） |
| `keywords` | TEXT | NULL | - | AI提取 | ✅ 有写入 | 关键词列表（JSON数组） |
| `initial_domain` | TEXT | NULL | - | 规则分类 | ❌ 无写入代码 | 初始领域分类（待确认是否废弃） |
| `initial_tags` | TEXT | NULL | - | 规则提取 | ❌ 无写入代码 | 初始标签（待确认是否废弃） |

#### 2.1.4 评分字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | Schema状态 | 关联状态 | 说明 |
|-------|------|------|-------|------|-----------|---------|------|
| `source_score` | REAL | NULL | - | 规则计算 | ✅ 存在 | ⚠️ 有读取无写入 | 信源评分（需补充写入逻辑） |
| `heat_score` | REAL | NULL | - | 热榜匹配 | ✅ 存在 | ✅ 有写入 | 热度评分 |
| `influence_score` | REAL | NULL | - | AI评估 | ✅ 存在 | ✅ 有写入 | 影响力评分 |
| `value_score` | REAL | NULL | - | AI评估 | ✅ 存在 | ✅ 有写入 | 价值评分 |
| `compliance_score` | REAL | NULL | - | 合规检查 | ✅ 存在 | ❌ 无写入代码 | 合规评分（功能未实现） |
| `final_score` | REAL | NULL | - | 综合计算 | ✅ 存在 | ✅ 有写入 | 最终评分 |
| `classification_confidence` | REAL | NULL | - | AI输出 | ✅ 存在 | ❌ 无写入代码 | 分类置信度（功能未实现） |
| `accuracy_score` | REAL | NULL | - | 校验计算 | ✅ 存在 | ⚠️ 有计算无写入 | 准确度评分（需添加写入逻辑） |

#### 2.1.5 旧版评分字段（兼容）

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `score` | REAL | NULL | - | 旧版计算 | ❌ 已废弃 | 综合评分（建议删除） |
| `score_timeliness` | REAL | NULL | - | 旧版计算 | ❌ 已废弃 | 时效性评分（建议删除） |
| `score_importance` | REAL | NULL | - | 旧版计算 | ❌ 已废弃 | 重要性评分（建议删除） |
| `score_credibility` | REAL | NULL | - | 旧版计算 | ❌ 已废弃 | 可信度评分（建议删除） |
| `score_impact` | REAL | NULL | - | 旧版计算 | ❌ 已废弃 | 影响力评分（建议删除） |
| `source_reliability_score` | REAL | NULL | - | 旧版计算 | ❌ 已废弃 | 信源可靠性评分（建议删除） |

#### 2.1.6 处理状态字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 说明 |
|-------|------|------|-------|------|------|
| `extraction_method` | TEXT | NULL | 'unknown' | 处理器 | 提取方法 |
| `combined_processing_status` | TEXT | NULL | - | 处理器 | 合并处理状态 |
| `validation_status` | TEXT | NULL | - | 校验器 | 校验状态 |
| `repair_count` | INTEGER | NULL | 0 | 修复器 | 修复次数 |

#### 2.1.7 向量嵌入字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 说明 |
|-------|------|------|-------|------|------|
| `embedding` | BLOB | NULL | - | BGE-M3 | 向量嵌入（1024维float32） |
| `embedding_updated_at` | DATETIME | NULL | - | 系统 | 向量更新时间 |

#### 2.1.8 原始数据字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | Schema状态 | 关联状态 | 说明 |
|-------|------|------|-------|------|-----------|---------|------|
| `raw_item_json` | TEXT | NULL | - | RSS/API | ✅ 存在 | ✅ 有写入 | 原始JSON数据 |
| `raw_news_id` | INTEGER | NULL | - | raw_news表 | ✅ 存在 | ✅ 有写入 | 原始数据ID |
| `original_summary` | TEXT | NULL | - | AI生成 | ✅ 存在 | ⚠️ 有计算无写入 | CombinedProcessor产出但未写入INSERT |
| `system_summary` | TEXT | NULL | - | 系统生成 | ✅ 存在 | ❌ 无写入代码 | 系统摘要（功能未实现） |

#### 2.1.9 系统字段

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 关联状态 | 说明 |
|-------|------|------|-------|------|---------|------|
| `created_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 系统 | ✅ 系统自动 | 创建时间 |
| `updated_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 系统 | ✅ 系统自动 | 更新时间 |
| `access_time` | DATETIME | NULL | - | 系统 | ❌ 无写入代码 | 访问时间（待确认是否废弃） |

#### 2.1.10 索引

```
idx_pub_date          - pub_date
idx_created_at        - created_at
idx_domain            - domain
idx_final_score       - final_score
idx_source            - source
idx_extraction_method - extraction_method
idx_combined_status   - combined_processing_status
idx_repair_count      - repair_count
idx_score             - score
```

---

### 2.2 raw_news 表（原始新闻表）

**用途**：存储采集到的原始新闻数据，用于增量处理。

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 说明 |
|-------|------|------|-------|------|------|
| `id` | INTEGER | PK | 自增 | 系统 | 自增主键 |
| `news_id` | TEXT | UNIQUE | - | MD5生成 | 新闻唯一标识 |
| `raw_json` | TEXT | NOT NULL | - | RSS/API | 原始JSON数据 |
| `source_name` | TEXT | NULL | - | RSS源 | 信源名称 |
| `fetched_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 系统 | 采集时间 |
| `processed` | INTEGER | NULL | 0 | 处理器 | 是否已处理（0/1） |

**索引**：
- `idx_raw_news_fetched_at` - fetched_at
- `idx_raw_news_processed` - processed
- `idx_raw_news_source` - source_name

---

### 2.3 processed_news 表（已处理ID表）

**用途**：存储已处理的新闻ID，用于去重。

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 说明 |
|-------|------|------|-------|------|------|
| `news_id` | TEXT | PK | - | MD5生成 | 新闻唯一标识 |
| `processed_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 系统 | 处理时间 |

**索引**：
- `idx_processed_at` - processed_at

---

### 2.4 rejected_news 表（被拒绝新闻表）

**用途**：存储被过滤掉的新闻，用于审计和分析。

| 字段名 | 类型 | 约束 | 默认值 | 来源 | 说明 |
|-------|------|------|-------|------|------|
| `id` | INTEGER | PK | 自增 | 系统 | 自增主键 |
| `news_id` | TEXT | NOT NULL | - | MD5生成 | 新闻唯一标识 |
| `title` | TEXT | NOT NULL | - | RSS/API | 新闻标题 |
| `link` | TEXT | NULL | - | RSS/API | 新闻链接 |
| `source_name` | TEXT | NULL | - | RSS源 | 信源名称 |
| `pub_date` | DATETIME | NULL | - | RSS/API | 发布时间 |
| `content` | TEXT | NULL | - | 网页抓取 | 新闻正文 |
| `reject_reason` | TEXT | NULL | - | 过滤器 | 拒绝原因 |
| `reject_type` | TEXT | NULL | - | 过滤器 | 拒绝类型 |
| `is_factual` | INTEGER | NULL | - | AI判断 | 是否为事实新闻 |
| `content_type` | TEXT | NULL | - | AI判断 | 内容类型 |
| `w5h1_score` | INTEGER | NULL | - | AI评估 | 5W1H完整度评分 |
| `confidence` | REAL | NULL | - | AI输出 | 置信度 |
| `created_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 系统 | 创建时间 |

**索引**：
- `idx_rejected_news_type` - reject_type
- `idx_rejected_news_source` - source_name
- `idx_rejected_news_created_at` - created_at

---

## 三、FTS5全文搜索表

### 3.1 news_fts 表（FTS5虚拟表）

**用途**：全文搜索索引，自动与news表同步。

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `title` | - | 标题 |
| `translated_title` | - | 翻译标题 |
| `content` | - | 正文内容 |
| `keywords` | - | 关键词 |
| `tags` | - | 标签 |

**同步机制**：通过触发器自动同步
- `news_fts_insert` - INSERT触发器
- `news_fts_update` - UPDATE触发器
- `news_fts_delete` - DELETE触发器

### 3.2 FTS5辅助表

| 表名 | 用途 |
|-----|------|
| `news_fts_config` | FTS5配置 |
| `news_fts_data` | FTS5数据块 |
| `news_fts_docsize` | 文档大小 |
| `news_fts_idx` | 词汇索引 |

---

## 四、知识图谱表

### 4.1 entities 表（实体表）

**用途**：存储从新闻中提取的实体（人物、组织、地点等）。

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | INTEGER | PK | 自增 | 实体ID |
| `name` | TEXT | NOT NULL | - | 实体名称 |
| `type` | TEXT | NOT NULL | - | 实体类型（PERSON/ORG/LOC等） |
| `subtype` | TEXT | NULL | - | 子类型 |
| `normalized_name` | TEXT | NULL | - | 标准化名称 |
| `created_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 更新时间 |

**索引**：
- `idx_entities_name_type` - (name, type)
- `idx_entities_type_norm` - (type, normalized_name)

### 4.2 news_entities 表（新闻-实体关联表）

**用途**：存储新闻与实体的多对多关系。

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | INTEGER | PK | 自增 | 关联ID |
| `news_id` | TEXT | NOT NULL | - | 新闻ID |
| `entity_id` | INTEGER | NOT NULL | - | 实体ID |
| `role` | TEXT | NULL | - | 实体角色 |
| `weight` | REAL | NULL | 1.0 | 权重 |
| `extra` | TEXT | NULL | - | 扩展信息（JSON） |
| `created_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 创建时间 |

**索引**：
- `idx_news_entities_news_id` - news_id
- `idx_news_entities_entity_id` - entity_id

### 4.3 event_clusters 表（事件聚类表）

**用途**：存储事件聚类结果。

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | INTEGER | PK | 自增 | 聚类ID |
| `cluster_date` | DATE | NOT NULL | - | 聚类日期 |
| `domain` | TEXT | NOT NULL | - | 领域 |
| `event_name` | TEXT | NOT NULL | - | 事件名称 |
| `news_ids` | TEXT | NOT NULL | - | 新闻ID列表（JSON） |
| `representative_id` | TEXT | NOT NULL | - | 代表新闻ID |
| `reason` | TEXT | NULL | - | 聚类原因 |
| `cluster_metadata` | TEXT | NULL | - | 元数据（JSON） |
| `created_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 创建时间 |

**索引**：
- `idx_event_clusters_date` - cluster_date
- `idx_event_clusters_domain` - domain
- `idx_event_clusters_rep_id` - representative_id

### 4.4 knowledge_index 表（知识索引表）

**用途**：知识库索引。

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `news_id` | INTEGER | PK | - | 新闻ID |
| `indexed_at` | TIMESTAMP | NULL | CURRENT_TIMESTAMP | 索引时间 |
| `chunk_count` | INTEGER | NULL | 0 | 分块数量 |

---

## 五、辅助功能表

### 5.1 hotboard_cache 表（热榜缓存表）

**用途**：缓存各平台热榜数据，用于热度评分。

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | INTEGER | PK | 自增 | 记录ID |
| `platform` | TEXT | NOT NULL | - | 平台名称（weibo/zhihu等） |
| `rank` | INTEGER | NOT NULL | - | 排名 |
| `title` | TEXT | NOT NULL | - | 热榜标题 |
| `hot_value` | INTEGER | NULL | - | 热度值 |
| `url` | TEXT | NULL | - | 链接 |
| `embedding` | BLOB | NULL | - | 向量嵌入 |
| `fetched_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 采集时间 |
| `expires_at` | DATETIME | NOT NULL | - | 过期时间 |

**索引**：
- `idx_hotboard_platform` - platform
- `idx_hotboard_expires` - expires_at
- `idx_hotboard_title` - title

### 5.2 market_context 表（市场上下文表）

**用途**：存储市场数据快照。

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | INTEGER | PK | 自增 | 记录ID |
| `date` | TEXT | NOT NULL | UNIQUE | 日期 |
| `snapshot_json` | TEXT | NOT NULL | - | 市场快照（JSON） |
| `fetched_at` | DATETIME | NULL | CURRENT_TIMESTAMP | 采集时间 |

**索引**：
- `idx_market_context_date` - date

---

## 六、历史/测试表

### 6.1 news_raw 表（历史原始数据表）

**用途**：旧版原始数据表，可能已废弃。

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | TEXT | PK | - | 新闻ID |
| `title` | TEXT | NOT NULL | - | 标题 |
| `link` | TEXT | NULL | - | 链接 |
| `content` | TEXT | NULL | - | 内容 |
| `source_name` | TEXT | NULL | - | 信源名称 |
| `source_type` | TEXT | NULL | - | 信源类型 |
| `category` | TEXT | NULL | - | 分类 |
| `credibility` | TEXT | NULL | - | 可信度 |
| `pub_date` | DATETIME | NULL | - | 发布时间 |
| `original_data` | TEXT | NULL | - | 原始数据 |
| `normalized_data` | TEXT | NULL | - | 标准化数据 |
| `collection_time` | DATETIME | NULL | CURRENT_TIMESTAMP | 采集时间 |

### 6.2 persistence_test 表（测试表）

**用途**：部署测试用表。

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `id` | INTEGER | PK | 自增 | 记录ID |
| `test_data` | TEXT | NULL | - | 测试数据 |
| `created_at` | TIMESTAMP | NULL | CURRENT_TIMESTAMP | 创建时间 |

### 6.3 sqlite_sequence 表（系统表）

**用途**：SQLite自增序列管理。

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `name` | - | 表名 |
| `seq` | - | 当前序列值 |

---

## 七、字段来源追踪

### 7.1 news表字段来源分布

| 来源模块 | 字段数 | 字段列表 |
|---------|-------|---------|
| **collector** | 7 | id, title, link, source, source_name, pub_date, raw_item_json |
| **processor (AI)** | 15 | translated_title, summary, who, what, when_time, where_place, why, how, domain, tags, keywords, influence_score, value_score, classification_confidence, original_summary |
| **processor (热度)** | 1 | heat_score |
| **processor (分类)** | 2 | initial_domain, initial_tags |
| **storage** | 3 | created_at, updated_at, access_time |
| **filters** | 2 | compliance_score, accuracy_score |
| **规则计算** | 1 | source_score |
| **向量引擎** | 2 | embedding, embedding_updated_at |
| **综合计算** | 1 | final_score |
| **状态追踪** | 4 | extraction_method, combined_processing_status, validation_status, repair_count |
| **关联** | 1 | raw_news_id |
| **旧版兼容** | 6 | score, score_timeliness, score_importance, score_credibility, score_impact, source_reliability_score |
| **系统** | 1 | system_summary |

### 7.2 核心字段数据流

```
采集阶段 (collector)
├── id (MD5生成)
├── title (RSS/API)
├── link (RSS/API)
├── source (RSS源标识)
├── source_name (RSS源名称)
├── pub_date (RSS/API)
└── raw_item_json (原始数据)
    │
    ▼
处理阶段 (processor)
├── translated_title (AI翻译)
├── summary (AI生成)
├── who/what/when/where/why/how (AI提取)
├── domain (AI分类)
├── tags/keywords (AI提取)
├── heat_score (热榜匹配)
├── influence_score (AI评估)
├── value_score (AI评估)
└── final_score (综合计算)
    │
    ▼
存储阶段 (storage)
├── created_at (系统时间)
├── updated_at (系统时间)
└── embedding (BGE-M3向量化)
```

---

## 八、与Layer 1/2一致性校验

### 8.1 表数量校验

| 检查项 | Layer 0 | Layer 3 | 状态 |
|-------|---------|---------|------|
| 表总数 | 18 | 18 | ✅ 一致 |
| 核心业务表 | 4 | 4 | ✅ 一致 |
| FTS5表 | 5 | 5 | ✅ 一致 |
| 知识图谱表 | 4 | 4 | ✅ 一致 |

### 8.2 领域定义校验

**数据库实际存储的domain字段值**（已验证）：

| 领域 | 记录数 | 来源 |
|-----|-------|------|
| 科技 | 960 | 数据库查询 |
| 政治 | 399 | 数据库查询 |
| 经济 | 385 | 数据库查询 |
| 社会 | 251 | 数据库查询 |
| 军事 | 81 | 数据库查询 |
| 文化 | 78 | 数据库查询 |
| 体育 | 62 | 数据库查询 |
| 已拒绝 | 51 | 数据库查询 |
| 娱乐 | 30 | 数据库查询 |
| 其他/边缘值 | 若干 | 数据库查询 |

**与代码定义对比**：

| 来源 | 领域定义 | 差异说明 |
|-----|---------|---------|
| data_models.py | 10类（科技/政治/经济/社会/军事/文化/体育/娱乐/教育/健康） | 缺少"已拒绝"，多出"教育/健康" |
| lightweight_classifier.py | 8类 | 精简版本 |
| 数据库实际值 | 9类（含"已拒绝"） | "已拒绝"为特殊状态标记 |

**结论**：数据库实际存储的领域值与代码定义存在差异，"已拒绝"是运行时添加的特殊状态标记，用于标识被过滤的新闻。

### 8.3 字段与函数对应

| 字段 | 写入函数 | 读取函数 | 状态 |
|-----|---------|---------|------|
| news.* | `insert_news_with_processed()` | `get_recent_news()` | ✅ |
| raw_news.* | `insert_raw_news_batch()` | - | ✅ |
| processed_news.* | `insert_news_with_processed()` | `filter_processed_ids()` | ✅ |
| rejected_news.* | - | - | ⚠️ 需核实 |
| hotboard_cache.* | `save_hotboard_cache()` | `get_hotboard_cache()` | ✅ |

---

## 九、校验清单

- [x] 所有表是否已扫描完成？ → 18个表全部扫描
- [x] 所有字段是否已列出？ → news表47个字段已列出
- [x] 字段类型是否准确？ → 从PRAGMA table_info获取
- [x] 字段来源是否标注？ → 已标注来源模块
- [x] 与Layer 0/1/2是否一致？ → 表数量一致

---

## 十、待解决问题

### 10.1 rejected_news表写入函数 ✅ 已调查

**调查结果**：
- 表中有524条记录
- reject_type分布：评论(167), 事实新闻(116), 广告(64), 预测(46), 其他(40), 观点(31), 不完整(29), 重复(19), 低质量(12)
- **代码中无INSERT语句**：搜索整个项目未发现写入rejected_news表的Python代码
- `_mark_news_as_rejected_v2`函数只更新news.domain='已拒绝'，不写入rejected_news表

**结论**：rejected_news表的数据可能由以下方式产生：
1. 已删除的历史代码写入
2. 外部脚本直接操作数据库
3. 需进一步确认数据来源

### 10.2 news_raw表状态 ✅ 已确认

**调查结果**：
- 表中有0条记录
- 搜索整个项目：**无任何Python代码引用此表**
- 无INSERT、SELECT、UPDATE、DELETE操作

**结论**：news_raw表已废弃，为历史遗留表，可考虑删除。

### 10.3 领域定义实际值 ✅ 已验证

见8.2节，已查询数据库实际存储的domain字段值。

### 10.4 数据流断裂问题 🔴 新发现（v3.3）

**问题描述**：阶段6-7深度分析发现，INSERT语句只覆盖了30个字段，以下字段在代码中被计算/产出，但未写入数据库：

| 字段 | 严重度 | 问题 | 建议 |
|------|--------|------|------|
| `accuracy_score` | 🔴 高 | 计算但未写入INSERT | 修改INSERT语句添加字段 |
| `original_summary` | 🔴 高 | 产出但未写入INSERT | 修改INSERT语句添加字段 |
| `classification_confidence` | 🟡 中 | 无写入代码 | 实现写入逻辑 |
| `compliance_score` | 🟡 中 | 无写入代码 | 实现写入逻辑 |
| `embedding_updated_at` | 🟡 中 | 无写入代码 | 向量生成时写入 |

**影响**：
- 无法追踪AI输出质量（accuracy_score缺失）
- 丢失原始摘要信息（original_summary缺失）
- 无法评估分类可靠性（classification_confidence缺失）
- 无法评估合规性（compliance_score缺失）

### 10.5 旧版废弃字段问题 🟢 新发现（v3.3）

**问题描述**：以下字段为旧版评分系统遗留，已废弃但未清理：

| 字段 | 问题 | 建议 |
|------|------|------|
| `score` | 旧版综合评分 | 后续清理删除 |
| `score_timeliness` | 旧版时效性评分 | 后续清理删除 |
| `score_importance` | 旧版重要性评分 | 后续清理删除 |
| `score_credibility` | 旧版可信度评分 | 后续清理删除 |
| `score_impact` | 旧版影响力评分 | 后续清理删除 |
| `source_reliability_score` | 旧版信源可靠性 | 后续清理删除 |

**建议**：暂不处理，待后续数据库清理时统一删除。

---

## 十一、阶段6-7深度分析发现（v3.3）

### 11.1 核心发现

**数据库实际有47个字段，但INSERT语句只覆盖了30个字段，存在17个字段未被写入的问题。**

```
数据库字段总数: 47个
INSERT语句覆盖: 30个
未覆盖字段: 17个
```

### 11.2 未写入字段分类汇总

| 分类 | 字段数 | 字段列表 | 优先级 |
|------|--------|---------|--------|
| **旧版废弃字段** | 6 | score, score_timeliness, score_importance, score_credibility, score_impact, source_reliability_score | 🟢 低 |
| **数据流断裂字段** | 4 | accuracy_score, original_summary, classification_confidence, compliance_score | 🔴 高 |
| **预留/未使用字段** | 4 | initial_domain, initial_tags, system_summary, access_time | 🟡 中 |
| **系统自动字段** | 2 | created_at, updated_at | ✅ 无需处理 |
| **向量字段** | 1 | embedding_updated_at | 🟡 中 |

### 11.3 数据流断裂字段详细分析

| 字段名 | 来源 | 用途 | 当前状态 | 影响 |
|--------|------|------|---------|------|
| `accuracy_score` | `combined_processor.py:222` `_evaluate_accuracy()` | 评估AI输出完整性（0-1分） | ⚠️ **计算但未写入** | 无法追踪AI输出质量 |
| `original_summary` | `combined_processor.py:205` | 来源网站原始摘要 | ⚠️ **产出但未写入** | 丢失原始摘要信息 |
| `classification_confidence` | 轻量分类器 | 分类置信度 | ❌ **无写入代码** | 无法评估分类可靠性 |
| `compliance_score` | 合规检查模块 | 合规评分 | ❌ **无写入代码** | 无法评估合规性 |

**代码证据**：

```python
# combined_processor.py 第171-172行
accuracy = self._evaluate_accuracy(result)
return result, accuracy  # accuracy 返回但未存储

# task1_collector.py 第377行
for news, result, accuracy in batch_results:
    # accuracy 被接收但未传入 NewsData
```

### 11.4 旧版废弃字段说明

| 字段名 | 来源 | 当前状态 | 说明 |
|--------|------|---------|------|
| `score` | 旧版评分系统 | ❌ 已废弃 | 新版用final_score |
| `score_timeliness` | 旧版评分系统 | ❌ 已废弃 | 新版用heat_score |
| `score_importance` | 旧版评分系统 | ❌ 已废弃 | 新版用influence_score |
| `score_credibility` | 旧版评分系统 | ❌ 已废弃 | 新版用source_score |
| `score_impact` | 旧版评分系统 | ❌ 已废弃 | 新版用value_score |
| `source_reliability_score` | 旧版评分系统 | ❌ 已废弃 | 新版用source_score |

**结论**：这些字段是历史遗留，无需修复。建议后续清理数据库时删除。

### 11.5 预留/未使用字段说明

| 字段名 | 用途 | 当前状态 | 建议 |
|--------|------|---------|------|
| `initial_domain` | 初始领域分类 | ❌ 无写入代码 | 待业务需求明确 |
| `initial_tags` | 初始标签 | ❌ 无写入代码 | 待业务需求明确 |
| `system_summary` | 系统摘要 | ❌ 无写入代码 | 功能未实现 |
| `access_time` | 访问时间 | ❌ 无写入代码 | 访问统计缺失 |

### 11.6 修复优先级矩阵

| 优先级 | 字段 | 问题类型 | 修复方案 | 工作量 |
|--------|------|---------|---------|--------|
| 🔴 **紧急** | `accuracy_score` | 数据流断裂 | 添加到INSERT语句 | 🟢 小 |
| 🔴 **紧急** | `original_summary` | 数据流断裂 | 添加到INSERT语句 | 🟢 小 |
| 🟡 **中期** | `classification_confidence` | 功能缺失 | 实现写入逻辑 | 🟡 中 |
| 🟡 **中期** | `compliance_score` | 功能缺失 | 实现写入逻辑 | 🟡 中 |
| 🟡 **中期** | `embedding_updated_at` | 功能缺失 | 向量生成时写入 | 🟢 小 |
| 🟢 **低** | `initial_domain/tags` | 预留字段 | 待业务需求明确 | - |
| 🟢 **低** | 旧版废弃字段 | 历史遗留 | 建议删除 | - |

### 11.7 修复方案

**最小修复方案（推荐）**：

```python
# 1. database.py - NewsData 添加字段
@dataclass
class NewsData:
    # ... 现有字段 ...
    accuracy_score: Optional[float] = None
    original_summary: Optional[str] = None

# 2. database.py - INSERT_NEWS_SQL 添加字段
INSERT_NEWS_SQL = """
    INSERT INTO news (
        ..., 
        accuracy_score, original_summary
    ) VALUES (
        ..., 
        :accuracy_score, :original_summary
    )
"""

# 3. task1_collector.py - 构建NewsData时传入
news_data = NewsData(
    ...,
    accuracy_score=accuracy,
    original_summary=result.get('original_summary', '')
)
```

**预计工作量**：约30分钟

---

## 十二、下一步

Layer 3 字段层已完成，下一步进入 **Layer 4: 关联层**，建立函数与字段的关系映射。
