# 数据库持久化诊断报告

## 执行日期
2026-04-08

---

## 一、缓存机制分析

### 1.1 缓存配置检查

| 项目 | 配置 | 状态 |
|------|------|------|
| **缓存路径** | `data` | ✅ 正确，覆盖数据库目录 |
| **缓存Key** | `news-analyzer-data-v1` | ✅ 固定Key，支持累积 |
| **回退Key** | `news-analyzer-data-` | ✅ 支持前缀匹配 |
| **Save-Always** | 未配置 | ⚠️ 建议添加 |

### 1.2 缓存恢复流程

```
GitHub Actions 启动
    │
    ▼
┌─────────────────────┐
│ actions/cache@v4    │
│ - 尝试恢复 data目录  │
│ - 使用 news-analyzer│
│   -data-v1 key     │
└──────────┬──────────┘
           │
    命中 ◄─┴─► 未命中
     │         │
     ▼         ▼
┌────────┐ ┌──────────┐
│恢复已有│ │全新环境  │
│数据库  │ │重新初始化│
└────────┘ └──────────┘
```

---

## 二、数据库初始化逻辑

### 2.1 表结构初始化（`_init_database`）

**正常机制**：
- ✅ 使用 `CREATE TABLE IF NOT EXISTS`，不会覆盖已有数据
- ✅ 使用 `CREATE INDEX IF NOT EXISTS`，不会重复创建索引
- ✅ 支持数据库升级迁移（`_migrate_add_missing_columns`）

**关键表**：
| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `news` | 主新闻表 | `id` (TEXT PRIMARY KEY) |
| `processed_news` | 去重基线表 | `news_id` (TEXT PRIMARY KEY) |
| `raw_news` | 原始数据缓冲 | `news_id` (TEXT UNIQUE) |
| `news_fts` | 全文搜索 | 虚拟表 |

### 2.2 初始化代码分析

```python
# 关键：IF NOT EXISTS 保证不覆盖已有数据
cursor.execute('''
    CREATE TABLE IF NOT EXISTS news (
        id TEXT PRIMARY KEY,
        ...
    )
''')
```

**结论**：✅ 初始化逻辑安全，不会因缓存恢复导致数据丢失

---

## 三、去重机制验证

### 3.1 新闻ID生成算法

```python
def _generate_news_id(self, news: Dict) -> str:
    """生成新闻唯一ID"""
    content = f"{news['title']}_{news['link']}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()
```

| 特性 | 分析 |
|------|------|
| **唯一性** | MD5(title+link)，碰撞概率极低 |
| **稳定性** | 相同内容始终生成相同ID |
| **风险** | 标题或链接微小变化会生成不同ID |

### 3.2 多层去重检查

```
采集流程
    │
    ├─► Stage 1: raw_news 唯一约束
    │   └─► news_id TEXT UNIQUE
    │
    ├─► Stage 2: 内存去重
    │   └─► 同一批次内基于dict去重
    │
    ├─► Stage 3: 数据库去重 (filter_processed_ids)
    │   └─► SELECT news_id FROM processed_news
    │
    ├─► Stage 4: 存储前去重 (C-09)
    │   └─► _store_batch_to_database() 二次检查
    │
    └─► Stage 5: 单条插入检查
        └─► SELECT 1 FROM news WHERE id = ?
```

### 3.3 批量去重查询效率

```python
def filter_processed_ids(self, news_ids: List[str]) -> Set[str]:
    # 使用 IN 子句批量查询，O(1) 参数绑定
    placeholders = ','.join('?' * len(news_ids))
    sql = f"SELECT news_id FROM processed_news WHERE news_id IN ({placeholders})"
    cursor.execute(sql, news_ids)
```

| 指标 | 评估 |
|------|------|
| **时间复杂度** | O(N)，N为待查询ID数量 |
| **空间复杂度** | O(N)，返回已处理ID集合 |
| **SQL优化** | 使用索引 idx_processed_at |
| **批量上限** | SQLite默认999参数限制 |

---

## 四、事务处理分析

### 4.1 事务上下文管理器

```python
@contextmanager
def transaction(self):
    """事务上下文管理器"""
    with self.get_connection() as conn:
        try:
            yield conn
            conn.commit()      # 成功提交
        except Exception as e:
            conn.rollback()    # 失败回滚
            logger.error(f"事务回滚: {e}")
            raise
```

### 4.2 批量插入事务

```python
def insert_news_batch(self, news_list: List[NewsData]) -> int:
    with self.transaction() as conn:
        # 1. 批量插入 news 表
        cursor.executemany(self.INSERT_NEWS_SQL, news_dicts)
        # 2. 批量插入 processed_news 表
        cursor.executemany(self.INSERT_PROCESSED_SQL, processed_dicts)
        # 3. 原子提交
```

**原子性保证**：
- ✅ `news` 表和 `processed_news` 表在同一事务中
- ✅ 事务失败时自动回滚，不会部分写入
- ⚠️ 但 `raw_news` 表在单独事务中写入

### 4.3 并发写入冲突处理

```python
def _execute_with_retry(self, conn, sql, params, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return cursor.execute(sql, params)
        except sqlite3.OperationalError as e:
            if "locked" in msg or "busy" in msg:
                # 指数退避重试
                delay = base_delay * (2 ** attempt) + random.uniform(0, base_delay)
                time.sleep(delay)
```

---

## 五、并发控制机制

### 5.1 任务锁（Task Lock）

```python
with task_lock('collect', timeout=3600, blocking=False):
    collector = Task1NewsCollector()
    result = collector.run()
```

| 特性 | 配置 |
|------|------|
| **锁文件位置** | `data/locks/collect.lock` |
| **超时时间** | 3600秒（1小时） |
| **阻塞模式** | False（非阻塞） |
| **跨平台** | Windows/Unix双支持 |

### 5.2 并发场景分析

```
场景1: 正常执行
    Job A 获取锁 → 执行 → 释放锁
    
场景2: 并发冲突
    Job A 获取锁 → Job B 尝试获取 → 失败跳过
    
场景3: 超时残留
    Job A 崩溃 → 锁残留 → Job B 检测过期 → 强制释放
```

**风险评估**：✅ 并发控制完善

---

## 六、潜在风险识别

### 6.1 高风险项

#### ❌ 风险1: 缓存失效导致全量重采

| 项目 | 说明 |
|------|------|
| **触发条件** | GitHub Actions 缓存过期/被清除 |
| **影响** | `processed_news` 表为空，所有新闻被视为新数据 |
| **后果** | AI调用量激增，API费用大幅增加 |
| **概率** | 中（缓存7天无访问自动过期） |

**缓解措施**：
- 建议添加 `save-always: true` 确保缓存保存
- 考虑添加缓存健康检查

#### ❌ 风险2: raw_news 与 processed_news 状态不一致

```
流程问题:
1. _save_raw_news() 写入 raw_news (事务A)
2. AI处理 (耗时30-60分钟)
3. 任务取消
4. _store_batch_to_database() 未执行
5. processed_news 无记录
6. raw_news 标记为未处理
```

| 项目 | 说明 |
|------|------|
| **影响** | 下次采集可能重复处理相同新闻 |
| **后果** | AI资源浪费，数据重复 |
| **概率** | 高（任务超时/取消频繁） |

**建议修复**：
- raw_news 写入时应同时写入 processed_news（标记为"处理中"）
- 或移除 raw_news 的使用，简化架构

### 6.2 中风险项

#### ⚠️ 风险3: 新闻ID碰撞

```python
# 当前实现：仅使用 title + link
content = f"{news['title']}_{news['link']}"
```

| 问题 | 说明 |
|------|------|
| **碰撞场景** | 不同来源相同标题和链接 |
| **概率** | 低，但存在 |
| **建议** | 添加 source_name 增加唯一性 |

#### ⚠️ 风险4: SQLite 并发写入限制

| 限制 | 说明 |
|------|------|
| **写入锁** | SQLite 只支持单写入者 |
| **重试上限** | 3次重试后仍失败会抛出异常 |
| **风险** | 极端并发时可能丢失数据 |

### 6.3 低风险项

#### ℹ️ 风险5: 缓存Key过于简单

- 当前使用固定Key `news-analyzer-data-v1`
- 无法区分不同分支/环境的缓存
- 建议添加分支名或日期

---

## 七、数据一致性验证方法

### 7.1 健康检查脚本

```python
# 检查表一致性
def check_consistency():
    conn = sqlite3.connect('data/news.db')
    cursor = conn.cursor()
    
    # 检查1: news vs processed_news 数量
    cursor.execute("SELECT COUNT(*) FROM news")
    news_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM processed_news")
    processed_count = cursor.fetchone()[0]
    
    if news_count != processed_count:
        print(f"[警告] 数量不一致: news={news_count}, processed={processed_count}")
    
    # 检查2: 未处理的raw_news
    cursor.execute("SELECT COUNT(*) FROM raw_news WHERE processed = 0")
    unprocessed = cursor.fetchone()[0]
    
    if unprocessed > 100:  # 阈值可调
        print(f"[警告] 大量未处理raw_news: {unprocessed}")
```

### 7.2 GitHub Actions 集成

建议在 workflow 中添加缓存验证步骤：

```yaml
- name: 验证数据库一致性
  run: |
    python -c "
    import sqlite3
    conn = sqlite3.connect('data/news.db')
    # 执行健康检查
    "
```

---

## 八、改进建议

### 8.1 高优先级

#### 1. 添加 save-always 配置

```yaml
- name: 恢复数据缓存
  uses: actions/cache@v4
  with:
    path: data
    key: news-analyzer-data-v1
    restore-keys: news-analyzer-data-
    save-always: true  # 即使任务失败也保存缓存
```

#### 2. 改进 raw_news 状态管理

```python
# 方案A: 写入raw_news时同步写入processed_news
# 标记为 pending 状态，区分"处理中"和"已完成"

def _save_raw_news(self, normalized_news):
    # ... 现有逻辑 ...
    
    # 新增：同时标记为处理中
    for news in normalized_news:
        self.db.mark_processing(news['news_id'])  # 新接口
```

### 8.2 中优先级

#### 3. 增强新闻ID唯一性

```python
def _generate_news_id(self, news: Dict) -> str:
    # 添加 source_name 增加唯一性
    content = f"{news['source_name']}_{news['title']}_{news['link']}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()
```

#### 4. 缓存Key优化

```yaml
key: news-analyzer-data-${{ github.ref }}-${{ github.run_id }}
restore-keys: |
  news-analyzer-data-${{ github.ref }}-
  news-analyzer-data-
```

### 8.3 低优先级

#### 5. 添加缓存监控

```python
# 在采集开始时记录缓存状态
def log_cache_status():
    db_size = Path('data/news.db').stat().st_size
    logger.info(f"数据库大小: {db_size / 1024 / 1024:.1f}MB")
    
    processed_count = db.get_processed_count()
    logger.info(f"已处理新闻: {processed_count}")
```

---

## 九、总结

| 维度 | 评估 | 说明 |
|------|------|------|
| **缓存机制** | ✅ 良好 | 配置正确，支持累积 |
| **数据库初始化** | ✅ 安全 | IF NOT EXISTS 保证不覆盖 |
| **去重机制** | ✅ 完善 | 多层检查，基本可靠 |
| **事务处理** | ✅ 正确 | 原子性保证 |
| **并发控制** | ✅ 充分 | 任务锁+重试机制 |
| **风险防控** | ⚠️ 需改进 | 缓存失效和raw_news问题 |

### 总体评分: 8/10

**主要优势**：
- 多层去重检查机制完善
- 事务处理保证原子性
- 并发控制考虑周全

**主要风险**：
- 缓存失效可能导致全量重采
- raw_news 状态不一致问题
- 建议尽快实施高优先级改进
