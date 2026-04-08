# 缓存持久化改进报告

## 改进日期
2026-04-08

## 改进背景
GitHub Actions 每次运行都是全新容器环境，依赖 `actions/cache` 进行数据持久化。经过全面诊断，发现以下风险：
1. 缓存可能因失败而未被保存
2. 缺乏缓存健康监控机制
3. raw_news 状态不一致问题

## 实施的改进

### 1. 添加 `save-always` 配置

**修改文件**: `.github/workflows/collect.yml`

**修改内容**:
```yaml
- name: 恢复数据缓存
  uses: actions/cache@v4
  with:
    path: data
    key: news-analyzer-data-v1
    restore-keys: news-analyzer-data-
    save-always: true  # 新增：即使任务失败也保存缓存
```

**作用**: 确保即使采集任务失败，已处理的数据也不会丢失，避免下次全量重采。

### 2. 添加缓存健康检查步骤

**修改文件**: `.github/workflows/collect.yml`

**修改内容**:
```yaml
- name: 缓存健康检查
  if: always()
  run: python scripts/cache_health_check.py
```

**作用**: 每次任务结束后自动检查数据库一致性，及时发现问题。

### 3. 创建健康检查脚本

**新建文件**: `scripts/cache_health_check.py`

**功能**:
- 检查数据库文件存在性
- 验证 news 表与 processed_news 表一致性
- 检测未处理 raw_news 数量
- 检查重复新闻
- 验证关键索引存在

**返回码**:
- 0: 健康
- 1: 存在问题

### 4. 创建详细诊断报告

**新建文件**: `docs/CACHE_PERSISTENCE_DIAGNOSIS.md`

**内容涵盖**:
- 缓存机制分析
- 数据库初始化逻辑
- 去重机制验证
- 事务处理分析
- 并发控制机制
- 潜在风险识别
- 改进建议

## 改进效果

### 改进前风险
| 风险 | 概率 | 影响 |
|------|------|------|
| 缓存失效导致全量重采 | 中 | AI调用费用激增 |
| 数据不一致无法及时发现 | 高 | 重复采集累积 |
| 任务失败丢失缓存 | 中 | 数据丢失 |

### 改进后保护
| 保护措施 | 覆盖风险 |
|---------|---------|
| save-always | 任务失败缓存丢失 |
| 健康检查脚本 | 数据不一致、重复新闻 |
| 诊断报告 | 系统性风险识别 |

## 验证方法

### 1. 本地验证健康检查脚本

```bash
cd /path/to/news_analyzer
python scripts/cache_health_check.py
```

### 2. GitHub Actions 中查看健康检查输出

在 Actions 运行日志中找到 "缓存健康检查" 步骤，查看输出：
```
[OK] 数据库文件存在: 22.5MB
[OK] 表一致性: news=2355, processed_news=2356
[OK] 未处理raw_news: 0条
[OK] 24小时新闻量: 0条
[OK] 未发现重复新闻
[OK] 关键索引检查通过
[OK] 健康检查通过
```

### 3. 监控缓存命中情况

在 GitHub Actions 日志中查看缓存步骤：
```
Cache Size: ~23 MB (23456789 B)
Cache restored successfully
```

## 后续优化建议

### 短期（已实施）
- [x] 添加 save-always 配置
- [x] 添加健康检查脚本
- [x] 创建诊断文档

### 中期（建议实施）
- [ ] 改进 raw_news 状态管理（写入时同步标记处理中）
- [ ] 添加新闻ID来源标识增强唯一性
- [ ] 缓存Key添加分支名区分

### 长期（可选）
- [ ] 考虑使用外部数据库（如PostgreSQL）替代SQLite
- [ ] 实现分布式锁替代文件锁
- [ ] 添加更细粒度的缓存策略（分离数据库和模型缓存）

## 相关文件

| 文件 | 路径 | 说明 |
|------|------|------|
| Workflow配置 | `.github/workflows/collect.yml` | 缓存和健康检查步骤 |
| 健康检查脚本 | `scripts/cache_health_check.py` | 自动化健康检查 |
| 诊断报告 | `docs/CACHE_PERSISTENCE_DIAGNOSIS.md` | 完整技术分析 |
| 改进报告 | `docs/CACHE_IMPROVEMENTS.md` | 本文件 |
