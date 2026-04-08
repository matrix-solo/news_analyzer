# 批量修复记录 2026-04-08

基于 `OPTIMIZATION_PLAN_2026-04-08.md` 的验证结果，按第一性原理优先级实施。

---

## 修复清单

### P0: 数据正确性

| # | 问题 | 修复 | 文件 |
|---|------|------|------|
| 0 | CI 重复执行 task1 | 删除第一个无 id 的采集步骤 | `collect.yml:91-92` |
| 1 | 历史关联返回自身 | `find_related_news` 循环内排除 `target_news_id` | `history_relation_engine_bge3.py` |
| 2 | 评分量纲混排 | influence/heat ×10 转百分制显示 | `report_generator.py` |

### P1: 5W1H 质量

| # | 问题 | 修复 | 文件 |
|---|------|------|------|
| 3 | Prompt 允许推测 | 强化为"严禁推测，必须从原文提取" | `combined_processor.py` |
| 4 | "无"与"暂无信息"不统一 | 新增 `normalize_5w1h()`，无效值统一映射 | `defaults.py` |
| 5 | data_validator 用"无" | 改用 `normalize_5w1h` | `data_validator.py` |
| 6 | depth_analyzer 用"无" | 改用 `normalize_5w1h` | `depth_analyzer.py` |
| 7 | task1_collector 默认值 | 改用 `normalize_5w1h` | `task1_collector.py` |
| 8 | 重点新闻无质量门控 | 新增 `_has_minimal_5w1h()`，排序加权 | `report_generator.py`, `task2_reporter.py` |

### P2: 报告格式

| # | 问题 | 修复 | 文件 |
|---|------|------|------|
| 9 | "点击查看"链接 | 改为直接显示 URL | `report_generator.py:775,823` |
| 10 | 深度报告领域冗余 | 删除事件内"领域"行（简报保留） | `report_generator.py:824` |
| 11 | PDF 表格样式粗糙 | 深色表头 + 斑马纹 + 仅水平线 | `md2pdf.py` |

### P2: CI 归档

| # | 问题 | 修复 | 文件 |
|---|------|------|------|
| 12 | Artifact 仅保留 1 天 | 延长至 30 天 | `collect.yml` |
| 13 | 无长期归档 | 新增 git commit 步骤到 `reports/archive/` | `collect.yml` |

---

## 关键设计决定

### normalize_5w1h() 设计

- **无效值黑名单**：`''`, `'无'`, `'未知'`, `'不详'`, `'未提及'`, `'N/A'`, `'none'`, `'null'` 等 16 种
- **推测性前缀去除**：正则 `^(可能是|据推测|似乎|大概|也许|疑似|可能)\s*`
- **兜底值**：统一为 `DefaultValues.TEXT_UNKNOWN`（"暂无信息"）
- **调用点**：`task1_collector._fill_defaults`、`data_validator._fill_default_values`、`depth_analyzer.format_for_report`

### 评分百分制显示

存储层保持原始精度（sub-scores 0-10, final_score 0-100），仅在报告表格输出时将 influence/heat ×10 转为百分制。好处：数据库中的值保持 LLM 原始输出，不改存储结构。

### 重点新闻质量门控

不直接丢弃低质量新闻，而是通过排序加权让 5W1H 完整的新闻排在前面：
- `generate_depth_reports`：`(final_score, has_5w1h)` 二级排序
- `_select_top_n`：5W1H 全部无效时 score ×0.5 降权

### CI 归档

使用 git commit 推送到主分支的 `reports/archive/YYYY-MM-DD/` 目录，而非单独分支。原因：报告体积小（每天几十 KB PDF），不会显著膨胀仓库。

---

## 额外修复

- **task1_collector.py 预存语法错误**：`补救截止时间` if 块缺少缩进体，`continue` 未在 if 块内。已修复缩进。
