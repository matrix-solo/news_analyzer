# 新闻采集系统修复报告

## 修复日期
2026-04-08

## 执行记录

### 数据清理执行结果
- **备份文件**: `news.db.backup.20260408_120648` (22MB)
- **删除过期数据**: 611 条未处理的 raw_news 记录（超过7天）
- **数据一致性**: news=2355, processed_news=2356 (差值1，可接受)
- **重复新闻**: 未发现重复

### 600条"重复新闻"真相

**问题本质**: 不是重复新闻，而是任务取消导致的 **611 条未处理中间数据**

**根因链**:
1. 采集任务启动 → raw_news 写入 611 条
2. AI处理耗时过长 → GitHub Actions 超时/取消
3. 数据残留在 raw_news 表（processed=0）
4. 下次采集可能重复获取相同新闻

**解决措施**:
1. 已删除 611 条过期未处理数据
2. 统一超时为 240 分钟
3. 时区配置修复（避免调度混乱）
4. 存储前二次去重检查

## 问题清单

### 1. 时区配置问题 ✅ 已修复

**问题描述**：
GitHub Actions 使用 UTC 时间，但配置的调度时间未正确转换为北京时间。

**修复方案**：
- 早间报告任务：UTC 00:00 = 北京时间 08:00
- 午后采集任务：UTC 07:00 = 北京时间 15:00
- 夜间采集任务：UTC 15:00 = 北京时间 23:00

**修改文件**：`.github/workflows/collect.yml`

### 2. 超时时间不一致 ✅ 已修复

**问题描述**：
`collect` 任务设置 90 分钟超时，不足以完成完整采集流程。

**修复方案**：
统一两个任务的超时时间为 240 分钟（4小时）。

**修改文件**：`.github/workflows/collect.yml`

### 3. 补救采集时区问题 ✅ 已修复

**问题描述**：
补救采集使用本地时间（UTC）与 RSS 时间（可能带时区）比较，导致时区不一致。

**修复方案**：
- 使用 `datetime.now(timezone.utc)` 统一使用 UTC 时间
- 处理 RSS 时间时统一转换为 UTC 进行比较
- 添加默认值处理防止 AttributeError

**修改文件**：`task1_collector.py`

### 4. 数据重复问题 📋 待监控

**根因分析**：
1. **任务取消导致状态不一致**：GitHub Actions 超时/取消时，`processed_news` 表可能未更新
2. **时区不一致**：历史遗留数据可能存在时区不一致问题

**短期修复**：
- 已增强存储前去重检查（C-09）
- 创建数据清理脚本

**长期建议**：
- 考虑使用数据库唯一约束防止重复插入
- 实现幂等性采集机制

## 交付物清单

| 文件 | 用途 | 位置 |
|------|------|------|
| `collect.yml` | GitHub Actions 工作流（已更新） | `.github/workflows/` |
| `task1_collector.py` | 采集逻辑（已修复时区） | 根目录 |
| `cleanup_duplicate_news.sql` | SQL 清理脚本 | `scripts/` |
| `check_duplicate_stats.py` | 重复检查脚本 | `scripts/` |
| `FIX_SUMMARY.md` | 本修复报告 | `docs/` |

## 使用指南

### 1. 清理重复数据（如需要）

```bash
# 进入项目目录
cd /path/to/news_analyzer

# 备份数据库
cp data/news.db data/news.db.backup.$(date +%Y%m%d)

# 使用 SQLite 执行清理脚本
sqlite3 data/news.db < scripts/cleanup_duplicate_news.sql
```

### 2. 检查重复统计

```bash
# 运行检查脚本
python scripts/check_duplicate_stats.py
```

### 3. 监控采集情况

建议定期运行检查脚本：
```bash
# 添加到 crontab（本地运行）
0 9 * * * cd /path/to/news_analyzer && python scripts/check_duplicate_stats.py >> logs/duplicate_check.log 2>&1
```

## 验证步骤

1. **检查工作流配置**：
   ```bash
   cat .github/workflows/collect.yml | grep -A 5 "schedule:"
   ```

2. **检查下次触发时间**：
   - 在 GitHub 仓库页面 → Actions → News Collection Workflow
   - 查看 "Schedule" 触发器的下次运行时间

3. **观察下次运行结果**：
   - 关注采集数量是否正常（通常 100-300 条/天）
   - 检查是否有重复新闻警告

## 风险提示

1. **首次运行可能采集较多数据**：
   - 由于时区调整，调度时间发生变化
   - 这是正常行为，后续会恢复正常

2. **历史数据时区问题**：
   - `pub_date` 字段存储格式可能不统一
   - 建议使用 SQL 脚本检查并修复

## 后续优化建议

1. **数据库层面**：
   ```sql
   -- 添加唯一约束（需先清理重复数据）
   CREATE UNIQUE INDEX idx_unique_news ON news(title, link);
   ```

2. **采集策略**：
   - 考虑限制每个信源的单次采集数量
   - 实现更智能的增量采集窗口

3. **监控告警**：
   - 当日采集量超过阈值时发送告警
   - 监控重复率变化趋势
