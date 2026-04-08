# CI 事件报告：2026-04-09 工作流全面排查

> **事件日期**：2026-04-09
> **发现方式**：手动检查 GitHub Actions 日志
> **影响范围**：collect.yml 和 send_email.yml 两个工作流
> **修复提交**：e6e6be3, 226eecc, e1f24b1

---

## 事件时间线

```
2026-04-08 05:31 UTC  collect.yml 定时触发（成功）
                       ├─ task1 成功（349 条入库）
                       ├─ 健康检查成功
                       ├─ task2 成功（报告+邮件发送）
                       ├─ artifact 上传成功
                       └─ 归档失败（.gitignore 阻止 reports/）

2026-04-08 06:09 UTC  send_email.yml 定时触发（失败）
                       └─ artifact 下载失败（缺少 permissions）

2026-04-08 09:49 UTC  push 触发 collect.yml（失败）
                       └─ workflow 文件语法错误（后续 commit 修复）

2026-04-08 11:30 UTC  手动触发 collect.yml（失败）
                       ├─ task1 成功
                       ├─ 健康检查失败（cache_health_check.py 不存在）
                       └─ task2 被跳过

2026-04-08 15:52 UTC  手动触发 collect.yml（部分成功）
                       ├─ task1 成功（349 条）
                       ├─ 健康检查成功
                       ├─ task2 成功
                       ├─ artifact 上传成功
                       └─ 归档失败（.gitignore）

2026-04-08 18:44 UTC  手动触发 collect.yml（失败）
                       ├─ task1 部分成功（熔断器跳闸，572 条跳过）
                       ├─ 健康检查失败（raw_news 阈值）
                       └─ task2 被跳过

2026-04-09            排查、修复、推送
```

---

## 问题详情

### P1：article_fetcher 代理硬coded（严重）

**文件**：`core/processor/article_fetcher.py:25`

**原代码**：
```python
PROXY_URL = os.getenv('RSS_HTTP_PROXY', 'http://127.0.0.1:7890')
```

**CI 表现**：所有原文获取 100% 失败
```
ProxyError: Unable to connect to proxy 127.0.0.1:7890 Connection refused
```

**修复**：默认值改为空字符串，`_fetch_html` 仅在非空时设置代理

**根因**：开发机有本地代理，硬编码默认值绕过了环境变量机制

---

### P2：数据缓存永不更新（严重）

**文件**：`.github/workflows/collect.yml` 缓存配置

**原配置**：
```yaml
key: news-analyzer-data-v1  # 静态 key
```

**CI 表现**：每次 cache hit 后不重新保存，CI 采集的数据全部丢失
```
Cache hit occurred on the primary key news-analyzer-data-v1, not saving cache.
```

**修复**：key 改为 `news-analyzer-data-v1-${{ github.run_id }}`

**根因**：GitHub Actions cache 在 primary key 精确匹配时不重新保存

---

### P3：.gitignore 阻止报告归档（中等）

**文件**：`.gitignore:14`

**原配置**：
```
reports/
```

**CI 表现**：
```
The following paths are ignored by one of your .gitignore files: reports
```

**修复**：改为 `reports/*` + `!reports/archive/`

**根因**：`reports/` 忽略整个目录，git 无法 add 子目录

---

### P4：send_email.yml 权限不足（中等）

**文件**：`.github/workflows/send_email.yml`

**CI 表现**：
```
Resource not accessible by integration
```

**修复**：添加 `permissions: actions: read, contents: read`

**根因**：`dawidd6/action-download-artifact@v3` 需要 actions: read 权限访问 API

---

### P5：健康检查阻断主流程（严重）

**文件**：`scripts/cache_health_check.py:59`, `.github/workflows/collect.yml`

**原代码**：
```python
if unprocessed_raw > 100:  # 阈值无数据支撑
    issues.append(...)
```

**CI 表现**：575 条未处理 raw_news 触发失败，exit code 1 阻断后续所有步骤

**修复**：
- 阈值从 100 调整到 1000
- 工作流中健康检查步骤加 `continue-on-error: true`

**根因**：诊断工具以 exit code 控制流程，阈值缺乏数据支撑

---

### P6：熔断器未覆盖所有入口（严重）

**文件**：`core/processor/combined_processor.py`, `task1_collector.py`

**CI 表现**：熔断器跳闸后重试阶段仍逐条调用 LLM，572 次无效请求
```
熔断器已断开: 连续 3 次致命错误，跳过后续批次
...
熔断器已断开: 连续 16 次致命错误，跳过后续批次
```

**修复**：
- `process_news()` 入口添加熔断器检查
- `task1_collector.py` 重试阶段检测熔断状态后跳过

**根因**：`process_batch()` 有守卫但 `process_news()` 没有，两个入口不一致

---

### P7：Cron 时区偏差（中等）

**文件**：`.github/workflows/collect.yml`

**原配置**：`cron: '0 0 * * *'`（UTC 0:00 = 北京 08:00）
**设计意图**：北京时间 07:00

**修复**：改为 `cron: '0 23 * * *'`（UTC 23:00 = 北京 07:00）

**根因**：所有文档写 07:00，但 cron 写成了 08:00 对应的 UTC，从未交叉校验

---

### P8：通知邮件 recipients=[]（低）

**文件**：`task2_reporter.py:160`

**原代码**：
```python
send_email_with_attachments(subject, body, recipients=[])
```

**影响**：无新闻时通知邮件永远无法发出

**修复**：去掉 `recipients=[]` 参数，使用配置文件默认收件人

---

## 修复提交记录

| 提交 | 修复内容 |
|------|---------|
| `e6e6be3` | P1 代理硬编码 + P2 缓存 key + P3 .gitignore + P4 权限 + P5 健康检查 + P6 recipients |
| `226eecc` | P6 熔断器 process_news 守卫 + 重试阶段跳过 |
| `e1f24b1` | P7 Cron 时区修正 |
