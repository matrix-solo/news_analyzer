# 新闻分析系统优化方案（基于代码验证）

**分析日期**: 2026-04-08  
**验证方式**: 直接代码审查 + 数据库验证  
**分析范围**: 数据输入层 → 清洗处理层 → 分析计算层 → 报告生成层

---

## 一、项目理解确认

### 1.1 核心流程

```
RSS采集 → 字段标准化 → 轻量级分类(规则匹配) → 基础过滤(白名单/可信度/去重) → 
AI合并处理(翻译+摘要+5W1H+评分) → 向量化 → 热度评分 → 数据校验 → 
存储 → 简报生成(TOP10) / 深度报告(领域聚类)
```

### 1.2 关键模块对应关系

| 模块功能 | 主要文件 | 关键方法/类 |
|---------|---------|------------|
| 数据采集 | `task1_collector.py` | `_collect_from_sources()` |
| 去重处理 | `task1_collector.py:1568` | `_generate_news_id()` - MD5(title+link) |
|  | `core/storage/database.py:682` | `filter_processed_ids()` |
| 新闻分类 | `core/processor/lightweight_classifier.py:14` | `LightweightClassifier` - 规则匹配，无重试 |
|  | `task1_collector.py:370-388` | 分类结果合并逻辑 |
| 热度评分 | `core/processor/heat_processor.py` | `calculate_heat_score()` - 热榜API + BGE-M3 + TF-IDF降级 |
| AI处理 | `core/processor/combined_processor.py:75` | `CombinedProcessor` - 含熔断器 |
|  | `task1_collector.py:463-520` | 批量处理 + 失败重试逻辑 |
| 简报生成 | `core/processor/generators/report_generator.py:144` | `generate_brief_report()` - 仅标题/来源/摘要 |
| 深度报告 | `core/processor/generators/report_generator.py:240` | `generate_depth_reports()` - 含当日vs历史对比 |

---

## 二、问题清单（仅列出需要优化的项）

### 问题1: 熔断器触发后数据丢失

| 项目 | 内容 |
|------|------|
| **问题描述** | AI处理阶段熔断器触发后，剩余批次新闻被跳过且不存储，导致数据丢失 |
| **代码证据** | `task1_collector.py:428-437` |
| **具体代码** | ```python\nif self.combined_processor.is_circuit_open():\n    skipped = len(passed_news) - batch_idx\n    failed_news.extend(passed_news[batch_idx:])\n    self.stats['circuit_breaker_skipped'] = skipped\n    break  # 直接退出，未处理数据不存储\n``` |
| **影响** | 当AI服务连续3次致命错误(401/403等)后，当日剩余新闻全部丢失，可能导致重要新闻遗漏 |
| **优先级** | **P0** |

### 问题2: 信源健康监控缺失

| 项目 | 内容 |
|------|------|
| **问题描述** | 无系统化源健康度监控，无法及时发现某源长期无产出或异常 |
| **代码证据** | `task1_collector.py:960-963` - 仅有异常日志，无统计 |
| **具体代码** | ```python\nexcept Exception as e:\n    logger.warning(f"采集信源失败 {source.name}: {e}")\n# 仅记录日志，无后续统计/告警\n``` |
| **影响** | 某源RSS链接失效或源关闭时无法及时发现，导致该源新闻长期缺失，影响报告完整性 |
| **优先级** | **P1** |

---

## 三、用户要求检查项结论（无需优化的明确说明）

### ✅ 去重逻辑 - 未发现需要优化
- **检查结果**: Duplicate groups: 0（数据库中无重复title+link）
- **实现**: `_generate_news_id()` 使用 MD5(title+link)，`filter_processed_ids()` 批量查询，存储前二次检查
- **结论**: 去重逻辑有效，无重复数据

### ✅ 新闻分类重试 - 无需优化（澄清机制）
- **实际机制**: 轻量级分类器基于规则匹配(`lightweight_classifier.py:14-124`)，无重试逻辑
- **AI分类优先级**: AI处理阶段输出的domain优先级最高(`task1_collector.py:1423-1427`)，覆盖规则分类
- **结论**: 机制合理，非"错误重试"而是"优先级覆盖"

### ✅ 热榜API降级 - 未发现需要优化
- **实现**: `heat_processor.py` 已实现三级降级
  1. BGE-M3向量匹配(主要)
  2. 关键词匹配降级(命中热榜词+1分)
  3. 无热榜时返回0分
- **结论**: 降级方案完善

### ✅ 时间维度处理 - 未发现需要优化
- **实现**: 
  - 采集阶段: `item.pub_date.replace(tzinfo=None)` 统一移除时区(`task1_collector.py:748-761`)
  - 深度报告: 已包含当日vs近7天/30天统计 + 趋势描述(`report_generator.py:444-600`)
- **结论**: 时区处理正确，历史对比已实现

### ✅ 简报生成格式 - 确认仅含来源+摘要
- **实现**: `report_generator.py:190-230`
- **输出字段**: 标题(`title`)、来源(`source_name`)、摘要(`summary`)，无得分
- **结论**: 符合用户描述

---

## 四、优化方案

### 方案1: 熔断器数据暂存机制 (P0)

#### 4.1.1 问题分析
当前熔断器触发时，仅将剩余新闻添加到`failed_news`列表，但该列表在后续流程中仅记录日志而不存储，导致数据丢失。

#### 4.1.2 设计目标
- 熔断时暂存未处理新闻
- 下次采集时自动补救
- 不影响现有正常流程

#### 4.1.3 数据库表设计
```sql
-- 新增 pending_news 表
CREATE TABLE IF NOT EXISTS pending_news (
    news_id TEXT PRIMARY KEY,
    raw_json TEXT NOT NULL,          -- 原始新闻数据JSON
    source_name TEXT,
    failed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER DEFAULT 0,   -- 重试次数
    status TEXT DEFAULT 'pending',   -- pending/processing/failed/permanent_failed
    fail_reason TEXT                 -- 失败原因(熔断/AI错误/其他)
);

CREATE INDEX idx_pending_status ON pending_news(status, retry_count);
CREATE INDEX idx_pending_source ON pending_news(source_name);
```

#### 4.1.4 代码修改点

**修改1: 熔断时暂存数据** (`task1_collector.py:428-437`)
```python
# 原有代码
if self.combined_processor.is_circuit_open():
    skipped = len(passed_news) - batch_idx
    logger.critical(f"熔断器已断开，跳过剩余 {skipped} 条新闻")
    failed_news.extend(passed_news[batch_idx:])
    self.stats['circuit_breaker_skipped'] = skipped
    break

# 修改为
if self.combined_processor.is_circuit_open():
    skipped = len(passed_news) - batch_idx
    pending_news = passed_news[batch_idx:]
    logger.critical(f"熔断器已断开，暂存 {skipped} 条新闻到pending表")
    
    # 暂存到pending表
    self._save_pending_news(pending_news, fail_reason='circuit_breaker')
    
    self.stats['circuit_breaker_skipped'] = skipped
    self.stats['circuit_breaker_pending_saved'] = len(pending_news)
    break
```

**修改2: 新增暂存方法** (`task1_collector.py` 新增方法)
```python
def _save_pending_news(self, news_list: List[Dict], fail_reason: str = 'unknown'):
    """将未处理新闻暂存到pending表"""
    if not news_list:
        return
    
    pending_items = []
    for news in news_list:
        news_id = news.get('news_id') or self._generate_news_id(news)
        pending_items.append({
            'news_id': news_id,
            'raw_json': json.dumps(news, ensure_ascii=False),
            'source_name': news.get('source_name'),
            'fail_reason': fail_reason,
            'status': 'pending'
        })
    
    try:
        saved = self.db.insert_pending_news_batch(pending_items)
        logger.info(f"已暂存 {saved}/{len(news_list)} 条新闻到pending表")
    except Exception as e:
        logger.error(f"暂存pending新闻失败: {e}")

def _retry_pending_news(self, max_retry: int = 50) -> int:
    """重试pending表中的新闻"""
    try:
        pending = self.db.get_pending_news(limit=max_retry)
        if not pending:
            return 0
        
        logger.info(f"开始补救处理 {len(pending)} 条pending新闻")
        
        # 转换为正常新闻格式
        news_list = []
        for p in pending:
            try:
                news = json.loads(p['raw_json'])
                news['pending_id'] = p['news_id']  # 标记来源
                news_list.append(news)
            except json.JSONDecodeError:
                logger.warning(f"解析pending新闻失败: {p['news_id']}")
                self.db.update_pending_status(p['news_id'], 'failed', 'json_parse_error')
        
        if not news_list:
            return 0
        
        # 重新进入AI处理流程
        processed = self._process_news_batch(news_list)
        
        # 更新pending状态
        success_count = 0
        for news in processed:
            if news.get('combined_result'):
                self.db.update_pending_status(news['pending_id'], 'processed')
                success_count += 1
            else:
                # 增加重试计数
                retry_cnt = self.db.increment_pending_retry(news['pending_id'])
                if retry_cnt >= 3:
                    self.db.update_pending_status(news['pending_id'], 'permanent_failed', 'max_retry_exceeded')
        
        logger.info(f"Pending补救完成: {success_count}/{len(news_list)} 成功")
        return success_count
        
    except Exception as e:
        logger.error(f"补救pending新闻失败: {e}")
        return 0
```

**修改3: 数据库方法** (`core/storage/database.py` 新增)
```python
def insert_pending_news_batch(self, items: List[Dict]) -> int:
    """批量插入pending新闻"""
    if not items:
        return 0
    
    sql = """
        INSERT OR REPLACE INTO pending_news 
        (news_id, raw_json, source_name, failed_at, fail_reason, status)
        VALUES (:news_id, :raw_json, :source_name, datetime('now'), :fail_reason, :status)
    """
    
    with self.transaction() as conn:
        cursor = conn.cursor()
        cursor.executemany(sql, items)
        return cursor.rowcount

def get_pending_news(self, limit: int = 100) -> List[Dict]:
    """获取待重试的pending新闻"""
    sql = """
        SELECT news_id, raw_json, source_name, retry_count 
        FROM pending_news 
        WHERE status = 'pending' AND retry_count < 3
        ORDER BY failed_at ASC
        LIMIT ?
    """
    
    with self.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (limit,))
        return [dict(row) for row in cursor.fetchall()]

def update_pending_status(self, news_id: str, status: str, note: str = None):
    """更新pending新闻状态"""
    sql = """
        UPDATE pending_news 
        SET status = ?, 
            retry_count = CASE WHEN ? = 'processing' THEN retry_count + 1 ELSE retry_count END,
            fail_reason = COALESCE(?, fail_reason)
        WHERE news_id = ?
    """
    
    with self.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (status, status, note, news_id))
```

**修改4: 采集流程集成** (`task1_collector.py:run()` 开头)
```python
def run(self, max_per_source: int = None) -> Dict[str, Any]:
    """执行采集任务"""
    max_per_source = max_per_source or self.MAX_PER_SOURCE
    
    # 步骤0: 补救处理pending新闻
    with _timer.stage("补救pending新闻"):
        retry_count = self._retry_pending_news(max_retry=50)
        if retry_count > 0:
            logger.info(f"补救完成: {retry_count} 条pending新闻已处理")
    
    # 原有步骤1-12...
```

#### 4.1.5 日志告警格式
```
# 熔断时
[CRITICAL] 熔断器已断开，暂存 156 条新闻到pending表 (原因: 连续3次致命错误)
[INFO] 已暂存 156/156 条新闻到pending表
[STAT] circuit_breaker_skipped: 156, circuit_breaker_pending_saved: 156

# 补救时
[INFO] 开始补救处理 156 条pending新闻
[INFO] Pending补救完成: 142/156 成功 (14条失败，已增加重试计数)

# 达到最大重试
[WARNING] Pending新闻 {news_id} 达到最大重试次数(3)，标记为永久失败
```

#### 4.1.6 与现有流程衔接
- **正常流程**: 不受影响，仅当熔断器触发时执行暂存
- **下次采集**: 自动检测并处理pending表，无需人工干预
- **数据一致性**: pending_news使用独立表，不影响news表和processed_news表
- **清理策略**: 已处理或永久失败的pending记录保留7天后自动清理

---

### 方案2: 信源健康监控脚本 (P1)

#### 4.2.1 设计目标
- 监控各信源产出稳定性
- 发现长期无产出或异常源
- 生成定期健康报告

#### 4.2.2 实现方案

**新增文件**: `scripts/source_health_monitor.py`

```python
#!/usr/bin/env python3
"""信源健康监控脚本"""
import sqlite3
import yaml
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SourceHealthMonitor:
    def __init__(self, db_path: str = None, sources_path: str = None):
        self.db_path = Path(db_path or 'data/news.db')
        self.sources_path = Path(sources_path or 'sources.yaml')
        
    def load_sources(self) -> Dict:
        """加载配置的信源列表"""
        with open(self.sources_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_db_stats(self, days: int = 7) -> Dict:
        """获取数据库中各源产出统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 各源近N天产出
        cursor.execute('''
            SELECT source_name, COUNT(*) as cnt,
                   MIN(pub_date) as earliest,
                   MAX(pub_date) as latest
            FROM news
            WHERE pub_date >= datetime('now', '-{} days')
            GROUP BY source_name
        '''.format(days))
        
        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = {
                'count': row[1],
                'earliest': row[2],
                'latest': row[3]
            }
        
        conn.close()
        return stats
    
    def check_source_health(self) -> Dict:
        """检查信源健康度"""
        sources = self.load_sources()
        db_stats = self.get_db_stats(days=7)
        
        report = {
            'date': datetime.now().isoformat(),
            'sources': [],
            'alerts': []
        }
        
        # 遍历所有配置的源
        for section, value in sources.items():
            if isinstance(value, dict):
                for sub_section, src_list in value.items():
                    if isinstance(src_list, list):
                        for src in src_list:
                            if isinstance(src, dict) and src.get('enabled'):
                                name = src.get('name')
                                tier = src.get('tier', 'N/A')
                                
                                # 检查数据库产出
                                stat = db_stats.get(name, {})
                                count = stat.get('count', 0)
                                latest = stat.get('latest')
                                
                                # 健康度判断
                                if count == 0:
                                    status = 'ERROR'  # 7天无产出
                                    alert = f'源 [{name}] 近7天无产出，请检查RSS链接'
                                    report['alerts'].append(alert)
                                elif count < 3:
                                    status = 'WARNING'  # 产出过低
                                else:
                                    status = 'OK'
                                
                                report['sources'].append({
                                    'name': name,
                                    'tier': tier,
                                    'count_7d': count,
                                    'latest': latest,
                                    'status': status
                                })
        
        return report
    
    def generate_report(self) -> str:
        """生成健康报告"""
        report = self.check_source_health()
        
        lines = [
            f"# 信源健康报告 ({report['date'][:10]})",
            "",
            "## 概览",
            f"- 总配置源数: {len(report['sources'])}",
            f"- 正常源: {sum(1 for s in report['sources'] if s['status'] == 'OK')}",
            f"- 警告源: {sum(1 for s in report['sources'] if s['status'] == 'WARNING')}",
            f"- 异常源: {sum(1 for s in report['sources'] if s['status'] == 'ERROR')}",
            "",
        ]
        
        if report['alerts']:
            lines.extend([
                "## ⚠️ 异常告警",
                ""
            ])
            for alert in report['alerts']:
                lines.append(f"- {alert}")
            lines.append("")
        
        lines.extend([
            "## 各源产出统计(近7天)",
            "",
            "| 信源 | Tier | 产出数 | 最新文章 | 状态 |",
            "|------|------|--------|----------|------|"
        ])
        
        for src in sorted(report['sources'], key=lambda x: x['count_7d'], reverse=True):
            latest = src['latest'][:10] if src['latest'] else 'N/A'
            status_icon = {'OK': '✓', 'WARNING': '⚠', 'ERROR': '✗'}.get(src['status'], '?')
            lines.append(f"| {src['name']} | {src['tier']} | {src['count_7d']} | {latest} | {status_icon} |")
        
        return '\n'.join(lines)

if __name__ == '__main__':
    monitor = SourceHealthMonitor()
    report = monitor.generate_report()
    print(report)
    
    # 保存报告
    report_file = Path('logs/source_health_report.md')
    report_file.write_text(report, encoding='utf-8')
    logger.info(f"报告已保存: {report_file}")
```

#### 4.2.3 集成到CI
`.github/workflows/collect.yml` 新增步骤:
```yaml
- name: 信源健康检查
  if: always()
  run: python scripts/source_health_monitor.py
```

#### 4.2.4 工作量
- **开发**: 3小时
- **测试**: 1小时
- **文档**: 30分钟

---

## 五、信源覆盖检查结论

### 5.1 检查结果

**配置层面**:
- 总启用源数: 34个
- Tier 1源: 3个（路透社、美联社、法新社）
- 中文源: 3个（8.8%）- 新华社、央视、环球时报

**数据库层面** (近7天产出):
- 总新闻数: 2355条
- 来源分布: 40个不同source_name
- 无重复组: Duplicate groups = 0

### 5.2 结论

**中文源覆盖**: 
- 数量占比8.8%，但包含新华社、央视等权威源
- 代码中无针对中文源的特殊兜底或异常捕获
- 异常处理统一在`task1_collector.py:960-963`，仅记录日志

**建议**:
- 当前覆盖充足，新华社+央视可提供足够中文视角
- **无需额外优化**，但建议实施方案2的源健康监控，及时发现某源失效

---

## 六、实施顺序与注意事项

### 6.1 实施顺序

```
Phase 1 (立即): 方案1 - 熔断器数据暂存
  - 新增pending_news表
  - 修改task1_collector.py集成暂存和补救逻辑
  - 新增数据库方法

Phase 2 (本周): 方案2 - 信源健康监控
  - 开发source_health_monitor.py
  - 集成到CI流程
```

### 6.2 测试要点

**方案1测试**:
1. 模拟熔断器触发(修改阈值临时触发)
2. 验证pending表数据写入
3. 验证下次采集时自动补救
4. 验证重试3次后标记永久失败

**方案2测试**:
1. 验证源列表加载
2. 验证产出统计准确性
3. 验证异常告警生成

### 6.3 回滚策略

**方案1回滚**:
```bash
# 如出现问题，回滚到上一版本
git checkout task1_collector.py
git checkout core/storage/database.py

# pending_news表保留，不影响主流程
```

**方案2回滚**:
```bash
# 删除CI步骤即可，不影响主流程
```

---

## 七、第一性原理复核

| 优化项 | 提升报告质量？ | 避免不必要复杂性？ | 未违反排除方向？ |
|--------|---------------|-------------------|-----------------|
| 熔断器暂存 | ✓ 避免重要新闻丢失 | ✓ 仅新增表和独立流程 | ✓ |
| 源健康监控 | ✓ 保障数据完整性 | ✓ 独立脚本不影响主流程 | ✓ |

**结论**: 两项优化均直接提升报告质量（完整性、可靠性），未引入过度复杂性，未违反用户排除方向。

---

**方案确认后，可立即开始实施Phase 1（熔断器数据暂存）。**
