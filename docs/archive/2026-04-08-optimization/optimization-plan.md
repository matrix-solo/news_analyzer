# 新闻分析项目问题验证与优化方案

**生成日期**: 2026-04-08  
**验证范围**: C:\Users\matrix\Desktop\news_workflow\news_analyzer

---

## 一、问题确认清单

| 问题 | 是否存在 | 证据 | 根因 |
|------|----------|------|------|
| **1. GitHub Actions 归档缺失** | ✅ 存在 | `.github/workflows/collect.yml:105-111` 仅使用 `actions/upload-artifact` 临时上传，保留期仅1天，无git提交或长期归档 | Artifact保留期过短，无自动提交到仓库reports/目录的机制 |
| **2. 评分显示不一致** | ✅ 存在 | `combined_processor.py:44-47` LLM输出0-10分制；`source_scorer.py:186-217` final_score计算为0-100分制；`report_generator.py:568-580` 表格同时显示final_score(0-100)和influence/heat(0-10) | 未统一转换显示，高分阈值80仅适用于final_score，但描述与趋势判断逻辑混用 |
| **3. "点击查看"链接** | ✅ 存在 | `report_generator.py:752,800` 使用 `[点击查看]({url})` 格式 | 模板硬编码"点击查看"文本 |
| **4. 领域字段冗余** | ✅ 存在 | `report_generator.py:753,801` 在事件详情中显示领域字段；已是领域报告内 | 模板未判断上下文，无条件输出领域 |
| **5. 历史关联逻辑错误** | ⚠️ 部分存在 | `history_relation_engine_bge3.py:247-303` 未显式排除当前新闻自身；`fulltext_related` 使用0.7语义+0.2时间+0.1实体加权，导致相似度1.0时unified_score约0.9 | 未在查询时排除当前news_id；评分公式设计导致综合评分低于语义相似度 |
| **6. 5W1H 要素提取失败** | ✅ 存在 | `combined_processor.py:35-40` 允许"暂无信息"作为有效值；`depth_analyzer.py:256-266` 直接显示"无"；无完整性校验筛选逻辑 | LLM被允许返回空值，系统未强制要求，也未在筛选时检查5W1H完整性 |
| **7. 表格格式影响阅读** | ✅ 存在 | `md2pdf.py:280-292` 表格使用默认样式，背景色、网格线突出；`depth_analyzer.py:256-266` 5W1H表格样式未优化 | PDF生成时表格样式过于醒目，缺乏视觉层次 |

---

## 二、优化方案

### 1. GitHub Actions 归档优化

**修改文件**: `.github/workflows/collect.yml`

**方案A: 延长Artifact保留期 + 自动提交归档（推荐）**

```yaml
# ========== 在第111行后添加 ==========

      - name: 提交报告到仓库归档
        if: success()
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          
          # 创建日期目录
          REPORT_DATE=$(date +%Y-%m-%d)
          mkdir -p reports/archive/${REPORT_DATE}
          
          # 复制报告
          cp reports/${REPORT_DATE}/depth/*.pdf reports/archive/${REPORT_DATE}/ 2>/dev/null || true
          cp reports/${REPORT_DATE}/brief/*.md reports/archive/${REPORT_DATE}/ 2>/dev/null || true
          
          # 提交
          git add reports/archive/
          git diff --staged --quiet || git commit -m "📊 归档 ${REPORT_DATE} 新闻分析报告"
          git push
```

**修改 retention-days**:
```yaml
# 第109-111行修改
      - name: 上传报告
        uses: actions/upload-artifact@v4
        if: success()
        with:
          name: daily-report-${{ github.run_id }}
          path: reports/
          retention-days: 30  # 从1天改为30天
```

---

### 2. 评分统一优化

**修改文件**: `core/processor/generators/report_generator.py`

**统一为0-100分制显示**:

```python
# ========== 第568-580行修改 ==========

# 在 ReportGenerator 类中添加转换方法:
def _normalize_score(self, score, field_name):
    """统一转换为0-100分制"""
    if score is None:
        return 0
    # influence_score, value_score, heat_score 原始为0-10，转0-100
    if field_name in ('influence', 'value', 'heat'):
        return round(float(score) * 10, 1)
    # final_score, source_score 已经是0-100
    return round(float(score), 1)

# 在 _build_domain_report 中修改表格行:
lines.extend(
    [
        "| 指标 | 当日 | 近7天日均 | 近30天日均 | 说明 |",
        "|------|------|-----------|------------|------|",
        f"| 新闻数量 | {ctx.stats['count_today']} | {ctx.stats['avg_daily_count_7d']} | {ctx.stats['avg_daily_count_30d']} | 数值越高，信息密度越大 |",
        f"| 平均综合评分 | {ctx.stats['avg_score_today']} | {ctx.stats['avg_score_7d']} | {ctx.stats['avg_score_30d']} | 越高代表整体事件重要性越高 |",
        f"| 最高分事件 | {ctx.stats['max_score_today']} | - | - | 以下事件列表按综合评分排序 |",
        f"| 高分事件数(≥80分) | {ctx.stats['high_score_count_today']} | {ctx.stats['high_score_avg_7d']:.1f} | {ctx.stats['high_score_avg_30d']:.1f} | 重大事件数量 |",
        f"| 高分事件占比 | {ctx.stats['high_score_ratio_today']}% | - | - | 当日重大事件占比 |",
        "",
    ]
)

# 事件列表表格统一显示（第645-657行）:
for idx, cluster in enumerate(ctx.clusters, 1):
    rep_news = cluster.get("representative_news") or {}
    title = cluster.get("event_name") or rep_news.get(
        "translated_title", rep_news.get("title", "")
    )
    source = rep_news.get("source_name", rep_news.get("source", "未知"))
    # 统一转换为0-100分制
    score = self._normalize_score(rep_news.get("final_score"), "final")
    influence = self._normalize_score(rep_news.get("influence_score"), "influence")
    heat = self._normalize_score(rep_news.get("heat_score"), "heat")

    lines.append(
        f"| {idx} | {title} | {source} | {score:.0f} | {influence:.0f} | {heat:.0f} |"
    )
```

---

### 3. 链接显示优化

**修改文件**: `core/processor/generators/report_generator.py`

```python
# ========== 第751-752行修改 ==========
# 原代码:
# if url:
#     lines.append(f"- **原文链接**：[点击查看]({url})")

# 修改为:
if url:
    lines.append(f"- **原文链接**: {url}")

# ========== 第799-800行修改 ==========
# 同样修改深度报告中的链接显示
```

---

### 4. 领域字段移除冗余

**修改文件**: `core/processor/generators/report_generator.py`

```python
# ========== 第795-801行修改 ==========
# 删除领域行显示，改为通过报告标题判断

# 原代码:
# lines.append(f"- **领域**：{domain}")

# 修改为: 删除该行（报告标题已显示领域）
```

---

### 5. 历史关联逻辑修复

**修改文件**: `core/processor/history_relation_engine_bge3.py`

```python
# ========== 第247-303行 find_related_news 方法修改 ==========

def find_related_news(
    self,
    target_news: Dict,
    top_k: int = 5,
    threshold: float = MIN_SIMILARITY,
) -> List[RelatedRecord]:
    if self._index.size == 0:
        return []

    # 获取当前新闻ID用于排除
    target_news_id = str(target_news.get('news_id', ''))

    query_vec = _vec_from_news(target_news)
    # ... 编码逻辑不变 ...

    candidates = self._index.search(query_vec, top_k * 2)

    results: List[RelatedRecord] = []
    for sim, news_id, meta in candidates:
        # ========== 新增: 排除自身 ==========
        if news_id == target_news_id:
            continue
        # ========== 结束新增 ==========

        if sim < threshold:
            continue
        # ... 其余逻辑不变 ...

    results.sort(key=lambda r: r.unified_score, reverse=True)
    return results[:top_k]
```

**修改评分公式**（如需提高语义权重）:

```python
# ========== 第28-32行修改权重 ==========
# 原权重: semantic 0.7 / time 0.2 / entity 0.1
# 调整为更强调语义相似度:
W_SEMANTIC     = 0.8  # 从0.7提升
W_TIME         = 0.15 # 从0.2降低
W_ENTITY       = 0.05 # 从0.1降低
```

---

### 6. 5W1H 提取与筛选优化

**修改文件A**: `core/processor/combined_processor.py`

```python
# ========== 第35-49行修改系统Prompt ==========

_COMBINED_SYSTEM = """你是一个专业的新闻分析专家...

  "analysis": {
    "who": "涉及的主体（人/机构/国家），必须填写，不能为暂无信息",
    "what": "发生了什么事，必须填写，不能为暂无信息", 
    "when": "时间信息，必须填写，不能为暂无信息",
    "where": "地点信息，必须填写，不能为暂无信息",
    "why": "原因/背景，不清楚则填'背景待确认'",
    "how": "方式/过程/结果，不清楚则填'细节待补充'"
  },

## 评分标准（0-10）..."""
```

**修改文件B**: `core/processor/generators/report_generator.py`

```python
# ========== 在第313-315行后添加5W1H筛选 ==========

def _has_minimal_5w1h(self, news: Dict, min_required: int = 3) -> bool:
    """检查新闻是否有至少min_required个有效的5W1H字段"""
    fields = ['who', 'what', 'when', 'where', 'why', 'how']
    valid_count = 0
    for field in fields:
        value = news.get(field, '')
        if value and value not in ('暂无信息', '无', '', None):
            valid_count += 1
    return valid_count >= min_required

# 在 generate_depth_reports 中修改聚类筛选:
for cluster in clusters:
    # ... 原有逻辑 ...
    
    # 新增: 检查5W1H完整性
    rep_news = cluster.get('representative_news', {})
    if not self._has_minimal_5w1h(rep_news, min_required=3):
        # 5W1H不完整，降低优先级或跳过
        cluster['low_quality'] = True
        logger.warning(f"事件5W1H不完整: {rep_news.get('news_id')}")
```

**修改文件C**: `core/processor/depth_analyzer.py`

```python
# ========== 第256-266行修改5W1H显示 ==========

def format_for_report(self, analysis: DepthAnalysis) -> list[str]:
    lines = []

    # 检查5W1H有效性
    w5h1_fields = {
        '何时': analysis.when,
        '何地': analysis.where, 
        '何人': analysis.who,
        '何事': analysis.what,
        '为何': analysis.why,
        '如何': analysis.how
    }
    
    # 过滤无效值
    valid_fields = {k: v for k, v in w5h1_fields.items() 
                   if v and v not in ('无', '暂无信息', '', None)}
    
    if not valid_fields:
        lines.append("> ⚠️ 该事件关键要素提取不完整，以下分析基于有限信息")
        lines.append("")
        return lines

    lines.append("### 5W1H要素")
    lines.append("")
    lines.append("| 要素 | 内容 |")
    lines.append("|------|------|")
    for field_name, value in valid_fields.items():
        lines.append(f"| {field_name} | {value} |")
    lines.append("")

    # ... 其余逻辑 ...
```

---

### 7. 表格样式优化

**修改文件**: `core/utils/md2pdf.py`

```python
# ========== 第278-293行修改表格样式 ==========

# 普通表格样式优化
t = Table(table_data, colWidths=[None] * len(table_data[0]))
t.setStyle(TableStyle([
    ('FONTNAME', (0, 0), (-1, -1), font_name),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    # 表头样式：深灰背景+白字
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('FONTNAME', (0, 0), (-1, 0), font_name),  # 表头加粗
    # 数据行样式
    ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # 纯白背景
    # 交替行背景（可选）
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
    # 边框：仅保留水平细线
    ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#4a4a4a')),  # 表头上边框
    ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#4a4a4a')),  # 表头下边框
    ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor('#dddddd')),  # 底部边框
    ('LINEABOVE', (0, 1), (-1, 1), 0.5, colors.HexColor('#eeeeee')),  # 首行数据上边框
    # 移除垂直边框: ('GRID', ...) 删除
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
]))

# 5W1H表格专用样式（更简洁）
def create_5w1h_table(data, font_name):
    t = Table(data, colWidths=[80, 400])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        # 要素列（第一列）样式
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        # 内容列样式
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#333333')),
        # 边框：仅保留水平分隔线
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor('#eeeeee')),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor('#eeeeee')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t
```

---

## 三、实施优先级与测试建议

### 优先级排序

| 优先级 | 问题 | 原因 |
|--------|------|------|
| 🔴 **高** | 5W1H提取与筛选 | 影响报告质量核心，用户明确指出的"推测语气"问题 |
| 🔴 **高** | 评分统一 | 直接影响数据可信度，表格显示混乱 |
| 🟡 **中** | 历史关联逻辑修复 | 影响分析深度，关联自身是明显bug |
| 🟡 **中** | GitHub Actions归档 | 影响数据留存，但当前有1天临时归档 |
| 🟢 **低** | 链接显示/领域字段 | 纯UI优化，影响较小 |
| 🟢 **低** | 表格样式 | 视觉优化，可后续迭代 |

### 关键测试用例

```python
# 测试1: 评分统一性验证
def test_score_unification():
    """验证所有分数统一为0-100分制显示"""
    news = {
        'final_score': 85.0,      # 0-100
        'influence_score': 8.5,   # 0-10, 应显示为85
        'heat_score': 7.0,        # 0-10, 应显示为70
    }
    # 期望: 表格显示 85 | 85 | 70

# 测试2: 5W1H完整性筛选
def test_5w1h_filtering():
    """验证5W1H不完整事件被降级"""
    incomplete_news = {
        'who': '暂无信息',
        'what': '暂无信息',
        'when': '2024-01-01',
        'where': '暂无信息',
        'why': '暂无信息',
        'how': '暂无信息',
    }
    # 期望: 该新闻不应进入重点事件列表

# 测试3: 历史关联排除自身
def test_history_exclude_self():
    """验证关联结果不包含当前新闻自身"""
    target = {'news_id': 'news_001', 'title': '测试'}
    history = [
        {'news_id': 'news_001', 'title': '测试'},  # 自身
        {'news_id': 'news_002', 'title': '相关'},
    ]
    results = engine.find_related_news(target, history)
    # 期望: results 中不包含 news_001

# 测试4: Artifact归档验证
def test_artifact_archiving():
    """验证报告生成后自动提交到git"""
    # 运行工作流后检查:
    # 1. reports/archive/YYYY-MM-DD/ 目录存在
    # 2. 包含 .pdf 和 .md 文件
```

---

## 四、修改文件汇总

| 序号 | 文件路径 | 修改类型 | 问题关联 |
|------|----------|----------|----------|
| 1 | `.github/workflows/collect.yml` | 新增/修改 | 问题1 |
| 2 | `core/processor/generators/report_generator.py` | 新增方法/修改 | 问题2,3,4,6 |
| 3 | `core/processor/history_relation_engine_bge3.py` | 修改 | 问题5 |
| 4 | `core/processor/combined_processor.py` | 修改Prompt | 问题6 |
| 5 | `core/processor/depth_analyzer.py` | 修改 | 问题6 |
| 6 | `core/utils/md2pdf.py` | 修改样式 | 问题7 |

---

**备注**: 本方案基于代码验证结果生成，实施前建议在测试分支验证各修改点。
