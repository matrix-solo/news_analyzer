# Layer 5: 整合层文档

---

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|-----|------|------|-----|
| v5.0 | 2026-03-22 | ✅ 已完成 | 整合所有层级信息，生成最终文档 |

---

## 上层文档同步检查

**参考文档**：`阶段一_文档生成工作记录.md` (Layer 0 v0.5)

| 检查项 | 阶段一记录 | Layer 5实际 | 状态 | 说明 |
|-------|-----------|------------|------|-----|
| Layer 0 框架层 | ✅ 已完成 | 已整合 | ✅ 一致 | 模块架构、业务流程 |
| Layer 1 模块层 | ✅ 已完成 | 已整合 | ✅ 一致 | 12个模块、~69个文件 |
| Layer 2 函数层 | ✅ 已完成 | 已整合 | ✅ 一致 | ~120类、~142函数、~380方法 |
| Layer 3 字段层 | ✅ 已完成 | 已整合 | ✅ 一致 | 18表、news表47字段 |
| Layer 4 关联层 | ✅ 已完成 | 已整合 | ✅ 一致 | 函数-字段映射、关联异常 |

---

## 一、文档生成说明

### 1.1 整合层目的

将前四层（框架层、模块层、函数层、字段层、关联层）的信息整合成两份最终参考文档：

| 文档 | 内容 | 用途 |
|-----|------|------|
| `MODULE_REFERENCE.md` | 模块函数说明文档 | 开发人员参考 |
| `DATA_FIELDS_REFERENCE.md` | 数据字段文档 | 数据分析参考 |

### 1.2 文档来源

| 来源文档 | 版本 | 整合内容 |
|---------|------|---------|
| Layer 0 框架层 | v0.5 | 模块架构、业务流程图 |
| Layer 1 模块层 | v1.1 | 模块清单、职责说明 |
| Layer 2 函数层 | v2.1 | 函数列表、参数、返回值、使用状态 |
| Layer 3 字段层 | v3.2 | 数据库Schema、字段定义、关联状态 |
| Layer 4 关联层 | v4.2 | 函数-字段映射、关联异常报告 |

---

## 二、生成的最终文档

### 2.1 MODULE_REFERENCE.md（模块函数说明文档）

**位置**：`docs/MODULE_REFERENCE.md`

**内容结构**：
```
1. 概述
   1.1 项目简介
   1.2 技术栈
   1.3 模块架构图

2. 核心模块
   2.1 collector 采集模块
   2.2 processor 处理模块
   2.3 storage 存储模块
   2.4 filters 过滤模块
   2.5 models 数据模型
   2.6 config 配置模块
   2.7 scheduler 调度模块
   2.8 service 服务模块
   2.9 utils 工具模块

3. 商业版模块
   3.1 compliance 合规模块
   3.2 services 服务模块
   3.3 subscription 订阅模块
   3.4 web Web模块

4. 函数索引（按名称排序）
```

### 2.2 DATA_FIELDS_REFERENCE.md（数据字段文档）

**位置**：`docs/DATA_FIELDS_REFERENCE.md`

**内容结构**：
```
1. 概述
   1.1 数据库架构
   1.2 表关系图

2. 核心表
   2.1 news 新闻主表
   2.2 raw_news 原始新闻表
   2.3 processed_news 已处理表
   2.4 rejected_news 被拒绝表

3. 知识图谱表
   3.1 entities 实体表
   3.2 news_entities 关联表
   3.3 event_clusters 聚类表
   3.4 knowledge_index 索引表

4. 辅助表
   4.1 hotboard_cache 热榜缓存
   4.2 market_context 市场上下文

5. 字段数据流追踪
   5.1 采集阶段
   5.2 处理阶段
   5.3 存储阶段

6. 字段索引（按名称排序）
```

---

## 三、文档统计

### 3.1 MODULE_REFERENCE.md 统计

| 统计项 | 数量 |
|-------|------|
| 模块数 | 13 |
| 文件数 | 84 |
| 类数 | 133 |
| 模块级函数 | 154 |
| 类方法 | ~410 |
| 函数总计 | ~564 |

### 3.2 DATA_FIELDS_REFERENCE.md 统计

| 统计项 | 数量 |
|-------|------|
| 数据库表 | 18 |
| 核心业务表 | 4 |
| 知识图谱表 | 4 |
| 辅助功能表 | 2 |
| FTS5虚拟表 | 5 |
| 历史/测试表 | 3 |
| news表字段 | 47 |
| 总字段数 | ~120 |

---

## 四、关联异常汇总

### 4.1 未关联字段（17个）

| 优先级 | 字段 | 问题 |
|-------|------|------|
| 🔴 高 | `source_score` | 有读取无写入 |
| 🔴 高 | `rejected_news.*` | 无Python INSERT代码 |
| 🟡 中 | `initial_domain` | 无写入代码 |
| 🟡 中 | `initial_tags` | 无写入代码 |
| 🟡 中 | `compliance_score` | 无写入代码 |
| 🟡 中 | `classification_confidence` | 无写入代码 |
| 🟡 中 | `accuracy_score` | 有计算无存储 |
| 🟡 中 | `original_summary` | 有计算无存储 |
| 🟢 低 | `system_summary` | 无写入代码 |
| 🟢 低 | `access_time` | 无写入代码 |
| 🟢 低 | `score` | 已废弃 |
| 🟢 低 | `score_*` (4个) | 已废弃 |
| 🟢 低 | `source_reliability_score` | 已废弃 |
| 🟢 低 | `entities.subtype` | 预留字段 |
| 🟢 低 | `news_entities.extra` | 预留字段 |

### 4.2 未关联函数（4个）

| 模块 | 函数 | 问题 |
|-----|------|------|
| utils/source_scorer.py | `get_source_score()` | 有读取无写入 |
| processor/combined_processor.py | `_evaluate_accuracy()` | 计算结果未写入 |
| processor/ai_processor.py | `extract_tags()` | 需确认调用链 |
| processor/ai_processor.py | `generate_summary()` | 需确认调用链 |

---

## 五、校验清单

- [x] Layer 0-4 信息是否已整合？ → 已整合所有层级信息
- [x] MODULE_REFERENCE.md 是否已生成？ → 已生成
- [x] DATA_FIELDS_REFERENCE.md 是否已生成？ → 已生成
- [x] 关联异常是否已记录？ → 已记录在两份文档中
- [x] 文档结构是否清晰？ → 按模块/表分类，含索引

---

## 六、文档清单

| 文档 | 路径 | 说明 |
|-----|------|------|
| Layer 0 框架层 | `Layer0_框架层文档.md` | 模块架构、业务流程 |
| Layer 1 模块层 | `Layer1_模块层文档.md` | 模块清单、职责 |
| Layer 2 函数层 | `Layer2_函数层文档.md` | 函数列表、使用状态 |
| Layer 3 字段层 | `Layer3_字段层文档.md` | 数据库Schema |
| Layer 4 关联层 | `Layer4_关联层文档.md` | 函数-字段映射、关联异常 |
| Layer 5 整合层 | `Layer5_整合层文档.md` | 本文档 |
| **模块函数说明** | `docs/MODULE_REFERENCE.md` | 最终文档-模块函数 |
| **数据字段文档** | `docs/DATA_FIELDS_REFERENCE.md` | 最终文档-数据字段 |
| 工作记录 | `阶段一_文档生成工作记录.md` | 过程记录 |

---

## 七、下一步

阶段一（文档生成）已全部完成。建议：

1. **审核文档**：人工审核两份最终文档的准确性
2. **修复异常**：处理关联异常报告中的问题
3. **持续维护**：代码更新时同步更新文档
