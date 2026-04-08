# 基于代码验证的分层检查与迭代优化方案

**分析日期**: 2026-04-08  
**验证方式**: 直接阅读项目代码  
**分析范围**: 数据输入层 → 清洗处理层 → 分析计算层 → 报告生成层 → 交付反馈层

---

## 一、项目理解确认（基于实际代码）

### 1.1 核心流程验证

```
数据采集 (RSS) → 字段标准化 → 轻量级分类 → 基础过滤 → AI合并处理 → 向量化 → 热度评分 → 存储 → 报告生成
```

### 1.2 用户纠正意见验证结果

| 用户意见 | 验证结果 | 说明 |
|---------|---------|------|
| **中文源覆盖充足** | ✓ 确认 | sources.yaml共34个启用源，中文源4个(11.8%)，但包含新华社、央视等高质量源 |
| **时区缺陷已修复** | ✓ 确认 | 工作流cron已调整为UTC 00:00/07:00/15:00(对应北京时间08:00/15:00/23:00) |
| **分类错误会再次处理** | ✗ 需澄清 | 轻量级分类器无重试逻辑；AI处理阶段输出domain优先级最高，非"错误重试"机制 |
| **权重依赖热榜API** | ✓ 确认 | heat_score依赖热榜API，代码中有降级逻辑(TF-IDF) |
| **去重问题已修复** | ✓ 确认 | news=2355, processed_news=2356(差值1，可接受)；save-always已添加 |
| **熔断器应暂存数据** | ✗ 发现未实现 | 当前熔断后跳过批次，无暂存机制(见task1_collector.py:428-437) |
| **简报无得分展示** | ✓ 确认 | 简报仅展示标题/来源/摘要，无得分(见report_generator.py:144-240) |
| **深度报告有趋势对比** | ✓ 确认 | 已有当日vs近7天/30天统计和趋势描述(见report_generator.py:444-600) |
| **投资分析不使用** | ✓ 确认 | 模块存在但默认关闭(show_investment: false) |
| **置信度指标未展示** | ✗ 发现 | classification_confidence/accuracy_score存在但未在报告中展示 |

---

## 二、分层检查表（基于实际代码）

### 2.1 数据输入层

| 检查项 | 代码证据 | 问题/风险 | 优化建议 |
|--------|---------|-----------|-----------|
| **中文源覆盖统计** | sources.yaml: 34个启用源，中文源4个(11.8%) | 无实时覆盖度报表 | 增加源产出统计脚本，定期输出各源新闻数量/质量报告 |

**代码位置**: `sources.yaml`  
**中文源列表**: 新华社、央视、第一财经、环球时报等

---

### 2.2 清洗处理层

| 检查项 | 代码证据 | 问题/风险 | 优化建议 |
|--------|---------|-----------|-----------|
| **熔断器暂存机制** | task1_collector.py:428-437 | 熔断后跳过剩余批次，数据丢失 | 实现暂存机制：熔断时将剩余新闻写入pending表，下次补救 |
| **分类重试机制** | lightweight_classifier.py:14-124 | 无重试逻辑，用户理解有误 | 文档澄清：轻量级分类基于规则无重试；AI分类结果优先级最高 |
| **热榜降级逻辑** | heat_processor.py (需检查) | 依赖外部API，可能失效 | 增强本地缓存，延长缓存有效期至24小时 |

**关键代码** (task1_collector.py:428-437):
```python
if self.combined_processor.is_circuit_open():
    skipped = len(passed_news) - batch_idx
    failed_news.extend(passed_news[batch_idx:])  # 添加到失败列表但不会被存储
    self.stats['circuit_breaker_skipped'] = skipped
    break  # 直接跳出循环，未处理数据不会被保存
```

---

### 2.3 分析计算层

| 检查项 | 代码证据 | 问题/风险 | 优化建议 |
|--------|---------|-----------|-----------|
| **置信度指标展示** | task1_collector.py:383, report_generator.py | classification_confidence/accuracy_score计算但不展示 | 在深度报告中增加"数据质量"指标卡片 |

---

### 2.4 报告生成层

| 检查项 | 代码证据 | 问题/风险 | 优化建议 |
|--------|---------|-----------|-----------|
| **简报趋势对比** | report_generator.py:144-240 | 简报只有当日数据，无历史对比 | 简报头部增加"今日vs昨日"关键指标对比(3-4个数字) |
| **深度报告时间维度** | report_generator.py:444-600 | 已实现但可优化 | 增加可视化趋势图(ASCII图表或emoji趋势) |
| **领域覆盖** | report_generator.py:248 | 硬编码政治/经济/科技 | 用户确认当前重点，不作更改 |

**已实现的深度报告统计** (report_generator.py:457-550):
- 当日 vs 近7天日均 vs 近30天日均
- 高分事件数(≥80分)对比
- 当日平均分在近30天中的百分位
- 趋势描述(显著高于/低于/基本持平)

---

### 2.5 交付反馈层

| 检查项 | 代码证据 | 问题/风险 | 优化建议 |
|--------|---------|-----------|-----------|
| **反馈闭环** | 无相关代码 | 无用户反馈收集机制 | 设计轻量级反馈接口(见下文架构建议) |

---

## 三、具体优化方案

### 3.1 高优先级（立即实施）

#### 方案1: 熔断器数据暂存机制

**问题**: 熔断器触发后，剩余批次新闻被跳过且不会存入数据库

**实现方案**:
```python
# 新增 pending_news 表结构
CREATE TABLE pending_news (
    news_id TEXT PRIMARY KEY,
    raw_json TEXT NOT NULL,
    source_name TEXT,
    failed_at DATETIME,
    retry_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending'  -- pending/processing/failed
);

# 熔断器触发时暂存
def _circuit_breaker_fallback(self, pending_news_list):
    """熔断触发时暂存未处理新闻"""
    for news in pending_news_list:
        self.db.save_pending_news(news)
    logger.warning(f"已暂存 {len(pending_news_list)} 条新闻到pending表")

# 下次采集时补救
def _retry_pending_news(self):
    """重试pending表中的新闻"""
    pending = self.db.get_pending_news(limit=50)
    if pending:
        logger.info(f"补救处理 {len(pending)} 条pending新闻")
        # 处理逻辑...
```

**工作量**: 4小时  
**风险**: 低（新增表不影响现有流程）

---

#### 方案2: 简报增加趋势对比

**当前简报输出**:
```markdown
# 【2026-04-07 全球新闻简要摘要】
## 当日中国 TOP10 新闻
### 1. {标题}
- **来源**：{来源}
- **摘要**：{摘要}
```

**优化后输出**:
```markdown
# 【2026-04-07 全球新闻简要摘要】

## 今日概览
| 指标 | 今日 | 昨日 | 变化 |
|------|------|------|------|
| 总新闻数 | 156 | 142 | +14 📈 |
| 高分事件(≥80分) | 8 | 5 | +3 📈 |
| 平均评分 | 72.5 | 68.3 | +4.2 📈 |

## 当日中国 TOP10 新闻
...
```

**实现代码** (report_generator.py:144-160新增):
```python
# 获取昨日数据
yesterday_news = self.db.get_news_by_date(yesterday_str)
yesterday_stats = self._calc_brief_stats(yesterday_news)
today_stats = self._calc_brief_stats(all_news)

# 生成对比表
report_lines.extend([
    "## 今日概览",
    "",
    "| 指标 | 今日 | 昨日 | 变化 |",
    "|------|------|------|------|",
    f"| 总新闻数 | {today_stats['count']} | {yesterday_stats['count']} | {self._format_change(today_stats['count'], yesterday_stats['count'])} |",
    f"| 高分事件(≥80分) | {today_stats['high_score']} | {yesterday_stats['high_score']} | {self._format_change(today_stats['high_score'], yesterday_stats['high_score'])} |",
    f"| 平均评分 | {today_stats['avg_score']:.1f} | {yesterday_stats['avg_score']:.1f} | {self._format_change(today_stats['avg_score'], yesterday_stats['avg_score'])} |",
    ""
])
```

**工作量**: 3小时  
**风险**: 低（仅增加展示字段）

---

### 3.2 中优先级（本周实施）

#### 方案3: 深度报告数据质量指标卡片

**新增展示** (深度报告每个事件前增加):
```markdown
### 事件1：{事件名}

**数据质量指标**：
- 来源可信度：{source_score}/10 (Tier 1)
- AI处理置信度：{accuracy_score*100:.0f}% (翻译+摘要+5W1H完整性)
- 分类置信度：{classification_confidence*100:.0f}% (规则匹配度)
- 时效性：{hours_ago}小时前 (pub_date距当前)

**质量评级**：{高/中/低}
- 高：accuracy_score ≥ 0.8 且 classification_confidence ≥ 0.7
- 中：accuracy_score ≥ 0.6 且 classification_confidence ≥ 0.5
- 低：其他情况（建议谨慎参考）
```

**具体指标定义**:

| 指标 | 计算方式 | 来源字段 |
|------|---------|---------|
| **来源可信度** | source_score (0-10) | news.source_score |
| **AI处理置信度** | accuracy_score (0-1) | news.accuracy_score (来自DataValidator) |
| **分类置信度** | classification_confidence (0-1) | news.classification_confidence |
| **时效性得分** | max(0, 1 - (当前时间-pub_date)/24) | news.pub_date |

**实现位置**: report_generator.py `_format_depth_event` 方法开头  
**工作量**: 4小时  
**风险**: 低

---

#### 方案4: 源覆盖度统计脚本

**新增脚本**: `scripts/source_coverage_report.py`

**输出示例**:
```
=== 信源覆盖度统计 (2026-04-01 至 2026-04-07) ===

Tier 1 源 (8个):
- 路透社: 45条/天 (覆盖率: 100%) ✓
- 新华社: 38条/天 (覆盖率: 100%) ✓
- 美联社: 42条/天 (覆盖率: 100%) ✓
...

Tier 2 源 (15个):
- BBC: 28条/天 (覆盖率: 100%) ✓
- 央视: 15条/天 (覆盖率: 85%) ⚠️ 建议检查
...

中文源覆盖: 4/34 (11.8%)
- 产出占比: 23% (高质量中文源产出占比高于数量占比)

异常源 (近3天无产出):
- 某源: 最后更新 2026-04-04 (建议检查RSS链接)
```

**工作量**: 6小时  
**风险**: 低（独立脚本不影响主流程）

---

### 3.3 低优先级（后续规划）

#### 方案5: 轻量级反馈闭环设计

**架构设计**:
```
报告邮件
   │
   ├─ 嵌入反馈链接: https://feedback.example.com/rate?news_id=xxx&token=yyy
   │
   ▼
简单评分页 (HTML单页)
   ├─ 评分: 1-5星
   ├─ 快速标签: "分类错误"/"摘要不准"/"重要度不准"/"其他"
   └─ 可选文字反馈
   │
   ▼
数据存储
   ├─ 评分数据 → feedback表 (SQLite)
   └─ 定期生成反馈报告 → 指导模型优化
```

**API设计**:
```python
# core/feedback/api.py
class FeedbackAPI:
    def submit_rating(self, news_id: str, rating: int, tags: List[str], comment: str = ""):
        """提交评分"""
        pass
    
    def get_feedback_summary(self, days: int = 7) -> Dict:
        """获取反馈汇总"""
        pass
```

**工作量**: 2天（含前端页面）  
**风险**: 中（需部署Web服务）

---

## 四、架构优化建议

### 4.1 当前架构瓶颈

```
线性流水线瓶颈：
1. AI处理阶段是单点 - 熔断后数据丢失
2. 无反馈闭环 - 无法持续优化
3. 热榜API依赖 - 外部服务失效影响评分
```

### 4.2 演进方向

**Phase 1 (当前优化)**:
- 熔断器暂存机制 → 解决数据丢失
- 简报趋势对比 → 提升可读性
- 质量指标展示 → 增强可信度

**Phase 2 (短期)**:
- 热榜本地缓存增强 → 降低外部依赖
- 源覆盖度监控 → 保障数据完整性
- 轻量级反馈 → 启动闭环

**Phase 3 (中期)**:
- 自适应AI处理深度 → 重要新闻深度处理，普通新闻快速处理
- 多维度质量门控 → 综合confidence/accuracy/source评分

---

## 五、实施优先级与工作量

| 优先级 | 方案 | 工作量 | 预期效果 |
|--------|------|--------|----------|
| **P0** | 熔断器暂存机制 | 4h | 解决数据丢失问题 |
| **P0** | 简报趋势对比 | 3h | 提升简报信息量 |
| **P1** | 深度报告质量指标 | 4h | 增强报告可信度 |
| **P1** | 源覆盖度统计脚本 | 6h | 保障数据完整性 |
| **P2** | 轻量级反馈闭环 | 2天 | 启动持续优化 |

---

## 六、待确认问题

1. **熔断器暂存**: 是否同意实施pending_news表机制？
2. **简报趋势**: 简报中展示"今日vs昨日"对比是否符合期望？需要展示哪些指标？
3. **质量指标**: 深度报告中展示的4个指标（来源可信度、AI置信度、分类置信度、时效性）是否符合期望？
4. **热榜降级**: 当前已有TF-IDF降级，是否需要进一步增强本地缓存？

---

## 附录：关键代码引用

### A1. 熔断器跳过逻辑 (task1_collector.py:428-437)
```python
if self.combined_processor.is_circuit_open():
    skipped = len(passed_news) - batch_idx
    logger.critical(f"熔断器已断开，跳过剩余 {skipped} 条新闻")
    failed_news.extend(passed_news[batch_idx:])  # 仅添加到失败列表，不会被存储
    self.stats['circuit_breaker_skipped'] = skipped
    break
```

### A2. 简报生成逻辑 (report_generator.py:144-240)
```python
for i, news in enumerate(china_top10, 1):
    title = news.get('translated_title', news.get('title', '无标题'))
    summary = news.get('summary') or news.get('content', '')[:200]
    source = news.get('source_name', news.get('source', '未知来源'))
    report_lines.append(f"### {i}. {title}")
    report_lines.append(f"- **来源**：{source}")
    report_lines.append(f"- **摘要**：{summary}")
    # 注意：无得分展示
```

### A3. 深度报告统计实现 (report_generator.py:444-550)
```python
stats = {
    "count_today": len(domain_news),
    "avg_score_today": round(sum(scores) / len(scores), 1),
    "high_score_count_today": len(high_scores),
    "avg_daily_count_7d": round(s7["count"] / 7.0, 1),
    "avg_score_7d": s7["avg_score"],
    "today_score_percentile_30d": round(below_count / len(daily_avgs) * 100, 1),
}
```

### A4. 置信度字段存在但未展示 (task1_collector.py:383)
```python
# P-03 修复：存储分类置信度
news['classification_confidence'] = cls.get('confidence', 0.5)
# 该字段已存储在DB，但report_generator中未使用
```
