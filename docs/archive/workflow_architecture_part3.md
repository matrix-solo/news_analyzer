# 项目工作流架构文档 - 第三部分（其他模块）

**文档版本**: V2.0  
**批次**: 第三批（阶段10-17）  
**最后更新**: 2026-03-15

---

## 10. 爬虫模块工作流

### 10.1 模块概述

爬虫模块作为RSS采集的补充，用于抓取国内主流媒体网站的新闻内容。支持智能代理切换，国内网站直连，国际网站使用代理。

### 10.2 核心组件

#### 10.2.1 BaseCrawler（爬虫基类）

**文件**: `crawlers/base.py`

```python
class BaseCrawler(ABC):
    """爬虫抽象基类 - 智能代理版本"""
    
    def __init__(self):
        self.name = ""              # 爬虫名称
        self.base_url = ""         # 基础URL
        self.category = ""         # domestic/international
        self.use_proxy = None      # True/False/None(自动)
        self.proxy_url = None      # 自定义代理URL
        self.ignore_ssl = False    # 是否忽略SSL验证
        self.timeout = 30          # 请求超时
        self.max_retries = 3       # 最大重试次数
```

**智能代理策略**:
- `category='international'` → 自动启用代理
- `category='domestic'` → 自动直连
- 代理不可用 → 自动回退到直连模式

**代理状态检查**:
```python
def check_proxy_status(self) -> bool:
    # 10分钟内不重复测试
    if self.last_proxy_check and (datetime.now() - self.last_proxy_check) < timedelta(minutes=10):
        return self.proxy_status
    
    # 测试代理连接
    self.proxy_status = test_proxy_connection(proxy_url, timeout=15)
    self.last_proxy_check = datetime.now()
    return self.proxy_status
```

#### 10.2.2 CrawlerFactory（爬虫工厂）

**文件**: `crawlers/factory.py`

```python
class CrawlerFactory:
    """爬虫工厂类 - 智能代理版本"""
    
    _crawler_registry: Dict[str, Type[BaseCrawler]] = {}
    
    @classmethod
    def register_crawler(cls, name: str, crawler_class: Type[BaseCrawler]):
        """注册爬虫类"""
        cls._crawler_registry[name] = crawler_class
    
    @classmethod
    def create_crawler(cls, name: str, **kwargs) -> Optional[BaseCrawler]:
        """创建爬虫实例"""
        crawler_class = cls._crawler_registry.get(name)
        if crawler_class:
            return crawler_class(**kwargs)
        return None
```

**已注册爬虫**:
| 爬虫名称 | 类 | 分类 | 代理策略 |
|---------|-----|------|---------|
| 新华社 | XinhuaCrawler | domestic | 直连 |
| 人民日报 | PeopleCrawler | domestic | 直连 |
| NewsAPI | NewsAPICrawler | international | 代理 |

#### 10.2.3 XinhuaCrawler（新华社爬虫）

**文件**: `crawlers/xinhua.py`

**特性**:
- 抓取时政要闻: `https://www.xinhuanet.com/politics/`
- 抓取地方新闻: `https://www.xinhuanet.com/local/`
- 内容选择器优先级:
  ```python
  content_selectors = [
      "div#p-detail",      # 新华社特定
      "div.detail",
      "div.article",
      "div.content"
  ]
  ```

**URL过滤规则**:
```python
if ('/politics/202' in href or '/202' in href) and
   '.html' in href and 
   'index' not in href:
    # 有效新闻链接
```

#### 10.2.4 PeopleCrawler（人民日报爬虫）

**文件**: `crawlers/people.py`

**特性**:
- 编码处理: GB2312
- SSL忽略: `ignore_ssl = True`（人民日报有SSL证书问题）
- URL模式匹配:
  ```python
  url_patterns = [
      r'/n1/\d{4}/\d{4}/c\d+-\d+\.html',  # 标准页面
      r'/GB/\d+/\d+/\d+\.html',          # 旧版页面
      r'/paper/\d+/\d+/\d+\.html',       # 报纸页面
  ]
  ```

### 10.3 爬虫工作流

```
┌─────────────────────────────────────────────────────────────┐
│                     爬虫执行流程                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 创建爬虫实例                                             │
│     └── CrawlerFactory.create_crawler(name)                 │
│                                                             │
│  2. 智能代理配置                                             │
│     ├── 国内爬虫 → use_proxy = False                        │
│     └── 国际爬虫 → check_proxy_status()                     │
│                                                             │
│  3. 获取HTTP会话                                             │
│     └── get_session()                                       │
│         ├── 国内: 直连                                       │
│         └── 国际: 代理可用→代理, 不可用→直连                 │
│                                                             │
│  4. 抓取新闻列表                                             │
│     └── fetch_news_list()                                   │
│         ├── 请求页面                                         │
│         ├── BeautifulSoup解析                               │
│         └── 提取链接+标题                                    │
│                                                             │
│  5. 抓取新闻详情                                             │
│     └── fetch_news_detail(url)                              │
│         ├── 请求详情页                                       │
│         ├── 提取标题                                         │
│         ├── 提取内容（多选择器尝试）                          │
│         ├── 提取发布时间                                     │
│         └── 提取作者                                         │
│                                                             │
│  6. 保存新闻                                                 │
│     └── save_news(news_data)                                │
│         └── save_original_news()                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 10.4 兜底机制

| 场景 | 兜底策略 |
|------|---------|
| 代理不可用 | 自动切换到直连模式 |
| 内容提取失败 | 尝试通用p标签提取 |
| 编码检测失败 | 依次尝试UTF-8、GB2312 |
| 请求超时 | 指数退避重试(max_retries=3-5) |
| SSL证书错误 | 忽略SSL验证(ignore_ssl=True) |

---

## 11. 调度与CI/CD工作流

### 11.1 本地任务调度器

**文件**: `scheduler/task_scheduler.py`

#### 11.1.1 核心类

```python
@dataclass
class ScheduledTask:
    """定时任务"""
    name: str
    func: Callable
    interval_seconds: int
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    run_count: int = 0

class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._stop_event = threading.Event()
```

#### 11.1.2 任务类型

| 任务名称 | 间隔 | 功能 |
|---------|------|------|
| rss_incremental_crawl | 1800秒(30分钟) | RSS增量采集 |
| rss_daily_archive | 3600秒(1小时) | 每日归档检查 |

#### 11.1.3 调度器工作流

```
┌─────────────────────────────────────────────────────────────┐
│                    调度器运行流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  启动调度器                                                  │
│     └── scheduler.start()                                   │
│         └── 创建守护线程 _run_loop()                        │
│                                                             │
│  主循环 (每秒检查)                                           │
│     └── while not _stop_event.is_set():                     │
│         └── _check_and_run_tasks()                          │
│             └── 遍历所有任务                                 │
│                 └── if task.should_run():                   │
│                     └── task.func()                         │
│                     └── task.mark_run()                     │
│                                                             │
│  停止调度器                                                  │
│     └── scheduler.stop()                                    │
│         └── _stop_event.set()                               │
│         └── 等待线程结束(5秒超时)                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 11.2 GitHub Actions CI/CD

#### 11.2.1 采集工作流 (collect.yml)

**触发时间** (北京时间):
- 07:00 - 采集+报告（主任务）
- 15:00 - 补充采集
- 23:00 - 补充采集

**工作流程**:
```yaml
jobs:
  collect-and-report:  # 早7点任务
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - uses: actions/cache@v4  # 数据缓存
        with:
          path: data
          key: news-analyzer-data-${{ hashFiles('requirements.txt') }}
      - run: pip install -r requirements.txt
      - run: |
          # 配置环境变量（从Secrets获取）
          echo "ARK_API_KEY=${{ secrets.ARK_API_KEY }}" >> .env
          echo "SMTP_HOST=${{ secrets.SMTP_HOST }}" >> .env
          # ... 其他配置
      - run: python run_collect.py
      - run: python run_report.py --no-email
      - uses: actions/upload-artifact@v4  # 上传报告
        with:
          name: daily-report
          path: reports/
          retention-days: 1
```

#### 11.2.2 报告工作流 (report.yml)

**触发时间**: 北京时间 00:00 (UTC 16:00前一天)

**功能**: 生成每日报告（不发送邮件）

#### 11.2.3 邮件工作流 (send_email.yml)

**触发时间**: 北京时间 08:30 (UTC 00:30)

**工作流程**:
```yaml
jobs:
  send-email:
    steps:
      - uses: dawidd6/action-download-artifact@v3  # 下载报告
        with:
          name: daily-report
          workflow: report.yml
          path: reports/
      - run: python send_email.py
```

### 11.3 CI/CD 兜底机制

| 场景 | 兜底策略 |
|------|---------|
| 数据缓存失效 | 重新采集（可能丢失历史数据） |
| 报告生成失败 | upload-artifact条件判断`if: success()` |
| 邮件发送失败 | 邮件附件检查步骤 |
| API密钥缺失 | 从Secrets获取，缺失则任务失败 |
| 超时 | collect: 60分钟, report: 默认 |

---

## 12. 脚本工具工作流

### 12.1 脚本分类

| 目录 | 用途 | 关键脚本 |
|------|------|---------|
| `scripts/automation/` | Windows自动化 | setup_windows_tasks.ps1 |
| `scripts/database/` | 数据库操作 | backfill_embeddings.py, db_manager.py |
| `scripts/maintenance/` | 维护任务 | recheck_pending_news.py |
| `scripts/deployment/` | 部署相关 | auto_backup.py |
| `scripts/tools/` | 工具脚本 | init_knowledge_base.py, check_env.py |

### 12.2 关键脚本详解

#### 12.2.1 Windows任务计划设置 (setup_windows_tasks.ps1)

**功能**: 一键设置Windows定时任务

**任务时间表**:
| 时间 | 任务 | 命令 |
|------|------|------|
| 07:00 | 新闻采集 | run_collect_auto.bat |
| 07:05 | 报告生成 | run_report_auto.bat |
| 08:30 | 邮件发送 | run_send_email_auto.bat |
| 15:00 | 补充采集 | run_collect_auto.bat |
| 23:00 | 补充采集 | run_collect_auto.bat |

**PowerShell命令**:
```powershell
# 创建任务
$action = New-ScheduledTaskAction -Execute "$projectPath\run_collect_auto.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At "07:00"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
Register-ScheduledTask -TaskName "新闻采集-早上7点" -Action $action -Trigger $trigger -Settings $settings
```

#### 12.2.2 向量回填脚本 (backfill_embeddings.py)

**功能**: 为数据库中现有新闻计算BGE-M3向量

**使用方法**:
```bash
python scripts/database/backfill_embeddings.py [--batch-size 100] [--days 90] [--force]
```

**处理流程**:
```python
def preprocess(news):
    """预处理文本"""
    parts = []
    title = news.get('translated_title') or news.get('title', '')
    if title:
        parts.append(title)
    summary = news.get('summary', '')
    if summary:
        parts.append(summary[:300])
    for field in ['who', 'what', 'where_place']:
        value = news.get(field, '')
        if value:
            parts.append(str(value))
    return ' '.join(parts)

# 批量编码
embeddings = model.encode(
    texts,
    normalize_embeddings=True,
    show_progress_bar=False,
    convert_to_numpy=True
)
```

#### 12.2.3 新闻重新判断 (recheck_pending_news.py)

**功能**: 批量处理domain、score为空的新闻

**处理逻辑**:
```python
def _get_pending_news(self) -> List[Dict]:
    """获取需要重新判断的新闻"""
    cursor.execute("""
        SELECT id, title, content, source_name, link
        FROM news 
        WHERE domain IS NULL 
           OR domain = '' 
           OR domain = 'None'
           OR score IS NULL
           OR score = 0
        ORDER BY created_at DESC
    """)
```

**判断标准**:
- `is_factual=True` 且 `w5h1_score >= 3` → 通过
- 否则 → 拒绝

#### 12.2.4 数据库管理CLI (db_manager.py)

**命令列表**:
| 命令 | 功能 | 示例 |
|------|------|------|
| stats | 显示统计 | `python db_manager.py stats` |
| recent | 最近新闻 | `python db_manager.py recent --hours 24` |
| search | 搜索新闻 | `python db_manager.py search "关键词"` |
| detail | 新闻详情 | `python db_manager.py detail <news_id>` |
| quality | 质量检查 | `python db_manager.py quality` |
| export | 导出数据 | `python db_manager.py export output.json` |
| rejected | 拒绝统计 | `python db_manager.py rejected` |

#### 12.2.5 自动备份服务 (auto_backup.py)

**备份策略**:
- 每`BACKUP_INTERVAL`秒（默认3600秒=1小时）
- 每天凌晨 00:00
- 每天中午 12:00

**清理策略**:
```python
def cleanup_old_backups(max_age_days: int = 30, max_count: int = 100):
    """清理过期备份"""
    for i, backup in enumerate(backups):
        should_delete = False
        if i >= max_count:  # 保留最多100个
            should_delete = True
        if age.days > max_age_days:  # 保留30天
            should_delete = True
```

#### 12.2.6 知识库初始化 (init_knowledge_base.py)

**初始化流程**:
```
1. 检查依赖 (ChromaDB, Sentence-Transformers)
2. 初始化数据库连接
3. 初始化知识库组件
   ├── ChromaKnowledgeBase
   ├── EmbeddingService
   ├── HybridChunkingStrategy
   └── KnowledgePipeline
4. 批量索引新闻
5. 验证初始化结果
6. 测试搜索功能
```

---

## 13. 商业化模块工作流

### 13.1 模块概述

商业化模块提供Web界面、订阅管理和邮件服务，支持免费/付费订阅模式。

### 13.2 Web应用 (app.py)

**框架**: Flask

**路由列表**:
| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 首页 |
| `/subscribe` | GET/POST | 订阅页面 |
| `/unsubscribe` | GET/POST | 取消订阅 |
| `/admin` | GET | 管理后台（需admin权限）|
| `/api/stats` | GET | 获取统计 |
| `/api/subscribers` | GET | 订阅者列表（需admin）|
| `/api/subscribe` | POST | API订阅 |
| `/api/unsubscribe` | POST | API取消订阅 |
| `/api/check-content` | POST | 内容合规检测 |
| `/api/check-source` | POST | 信源检测 |
| `/api/map-field` | POST | 领域映射 |

**权限控制**:
```python
def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_admin = request.args.get('admin') == 'true'
        if not is_admin:
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function
```

### 13.3 订阅管理 (subscriber_manager.py)

**数据模型**:
```python
@dataclass
class Subscriber:
    email: str
    created_at: str
    is_active: bool = True
    subscription_type: str = "free"  # free/premium
    expires_at: Optional[str] = None
    metadata: Optional[Dict] = None
```

**数据库表结构**:
```sql
CREATE TABLE subscribers (
    email TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    subscription_type TEXT DEFAULT 'free',
    expires_at TEXT,
    metadata TEXT
);
```

**API方法**:
| 方法 | 功能 |
|------|------|
| add_subscriber() | 添加订阅者 |
| remove_subscriber() | 移除订阅者（软删除）|
| get_subscriber() | 获取订阅者信息 |
| get_active_subscribers() | 获取活跃订阅者列表 |
| get_subscriber_count() | 获取订阅者统计 |
| upgrade_to_premium() | 升级为付费订阅 |

### 13.4 内容合规过滤 (content_filter.py)

**敏感词匹配结果**:
```python
@dataclass
class SensitiveMatch:
    keyword: str
    category: str
    level: str      # high/medium/low
    action: str     # reject/review
    position: int = 0
```

**过滤动作**:
| 级别 | 动作 | 说明 |
|------|------|------|
| high | reject | 高危敏感词，直接拒绝 |
| medium | review | 需人工审核 |
| low | pass | 低风险，通过 |

**处理流程**:
```
1. 加载敏感词库 (keywords.yaml)
2. 正则匹配敏感词
3. 判断最高级别
4. 返回过滤结果
```

### 13.5 商业邮件服务 (email_service.py)

**付费链接配置**:
```python
PAYMENT_LINKS = {
    'afdian': 'https://afdian.net/a/your_account',
    'mianbaoduo': 'https://mianbaoduo.com/o/your_product'
}
```

**邮件内容模板**:
```python
def _prepare_email_content(self, content, subscriber, include_payment_link):
    footer = "\n\n" + "=" * 50 + "\n"
    
    if subscriber.subscription_type == 'free' and include_payment_link:
        footer += """
📌 升级为付费会员，解锁更多深度分析内容！

💎 付费会员权益：
  • 每日深度分析报告（完整版）
  • 历史数据回溯查询
  • 个性化定制推送
  • 专属客服支持

🔗 订阅链接：
  • 爱发电：{afdian}
  • 面包多：{mianbaoduo}
""".format(**self.PAYMENT_LINKS)
```

---

## 14. 测试模块工作流

### 14.1 测试配置 (conftest.py)

**测试标记**:
| 标记 | 说明 |
|------|------|
| @pytest.mark.unit | 单元测试（快速、隔离）|
| @pytest.mark.integration | 集成测试（需外部资源）|
| @pytest.mark.e2e | 端到端测试 |
| @pytest.mark.slow | 慢速测试（>5秒）|
| @pytest.mark.requires_api | 需要API密钥 |

**全局Fixtures**:
```python
@pytest.fixture
def isolated_db(temp_db_path):
    """完全隔离的数据库实例"""
    NewsDatabase._instance = None
    NewsDatabase._initialized = False
    
    db = NewsDatabase(temp_db_path)
    
    try:
        yield db
    finally:
        # 清理连接和文件
        db._NewsDatabase__conn.close()
        gc.collect()
        # 删除临时文件
        for ext in ['', '-wal', '-shm']:
            file_path = temp_db_path + ext
            if os.path.exists(file_path):
                os.unlink(file_path)
```

### 14.2 智能回溯测试 (test_smart_backtrack.py)

**测试场景**:
```python
test_cases = [
    ("路透社", 0.5, "短时间中断"),
    ("新华社", 3, "中等中断"),
    ("BBC News", 12, "较长时间中断"),
    ("纽约时报", 48, "长时间中断"),
    ("TechCrunch", 120, "超长时间中断")
]
```

### 14.3 遗漏驱动架构测试 (test_gap_driven_architecture.py)

**测试场景**:
| 场景 | 数据库最新 | RSS最早 | 预期结果 |
|------|-----------|---------|---------|
| 无遗漏 | now-6h | now-24h | has_gap=False |
| 存在遗漏 | now-48h | now-24h | has_gap=True |
| 首次采集 | None | now-24h | has_gap=False |

---

## 15. 基础设施与配置

### 15.1 Python依赖 (requirements.txt)

**核心依赖分类**:
| 类别 | 依赖 | 版本 |
|------|------|------|
| 配置与环境 | python-dotenv, PyYAML | >=1.0.0, >=6.0 |
| HTTP请求 | requests, httpx | >=2.28.0, >=0.24.0 |
| AI模型 | openai, volcengine-python-sdk | >=1.0.0, >=1.0.0 |
| 网页解析 | beautifulsoup4 | >=4.12.0 |
| PDF生成 | reportlab | >=4.0.0 |
| 图表生成 | plotly, kaleido | >=5.0.0, >=0.2.0 |
| 知识库 | chromadb, sentence-transformers, tiktoken | >=0.4.0, >=2.2.0, >=0.5.0 |
| 向量索引 | faiss-cpu | >=1.7.0 |

### 15.2 项目配置 (pyproject.toml)

**开发依赖**:
```toml
[project.optional-dependencies]
dev = [
    "mypy>=1.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pre-commit>=3.0.0",
]
```

**代码规范**:
- Black: line-length = 88
- isort: profile = "black"
- mypy: strict = true

### 15.3 Docker配置

**Dockerfile**:
```dockerfile
FROM python:3.9-slim

# 系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl

# Python依赖
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/app/data/news.db')" || exit 1

CMD ["python", "run_scheduler.py"]
```

**docker-compose.yml**:
```yaml
services:
  news_analyzer:
    build: .
    image: news-analyzer:latest
    restart: unless-stopped
    volumes:
      - news_db:/app/data
      - news_logs:/app/logs
      - news_backups:/app/backups
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import sqlite3; sqlite3.connect('/app/data/news.db')"]
      interval: 30s
      timeout: 10s
      retries: 3

  backup_service:
    image: news-analyzer:latest
    command: python scripts/auto_backup.py
    depends_on:
      news_analyzer:
        condition: service_healthy
```

### 15.4 环境变量 (.env.example)

**AI模型配置**:
```bash
# 深度分析模型
AI_ANALYSIS_PROVIDER=
AI_ANALYSIS_MODEL=
AI_ANALYSIS_KEY=
AI_ANALYSIS_BASE_URL=

# 快速筛选模型
AI_FILTER_PROVIDER=
AI_FILTER_MODEL=
AI_FILTER_KEY=
AI_FILTER_BASE_URL=

# 备用模型
AI_BACKUP_PROVIDER=
AI_BACKUP_MODEL=
AI_BACKUP_KEY=
AI_BACKUP_BASE_URL=
```

**代理配置**:
```bash
HTTP_PROXY=http://127.0.0.1:your-proxy-port
HTTPS_PROXY=http://127.0.0.1:your-proxy-port
NO_PROXY=.xinhuanet.com,.people.com.cn
```

**邮件配置**:
```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_auth_code
EMAIL_TO=recipient@example.com
```

---

## 16. 根目录工具脚本

### 16.1 实体字段检查 (check_entity_fields.py)

**功能**: 检查数据库中5W1H实体字段的填充情况

**检查字段**:
- who (何人)
- what (何事)
- where_place (何地)

**输出示例**:
```
=== 实体字段分析 ===
有得分的新闻总数: 1000
有who字段的新闻: 850 (85.0%)
有what字段的新闻: 920 (92.0%)
有where_place字段的新闻: 780 (78.0%)
有任意实体字段的新闻: 950 (95.0%)
```

---

## 17. 数据库脚本补充

### 17.1 嵌入向量迁移 (migrate_add_embedding.py)

**迁移内容**:
```sql
-- 添加embedding字段（存储BGE-M3向量）
ALTER TABLE news ADD COLUMN embedding BLOB;

-- 添加embedding_updated_at字段
ALTER TABLE news ADD COLUMN embedding_updated_at DATETIME;
```

### 17.2 向量回填 (backfill_embeddings.py)

**参数**:
| 参数 | 说明 | 默认值 |
|------|------|--------|
| --batch-size | 每批处理数量 | 100 |
| --days | 处理最近N天的新闻 | 90 |
| --force | 强制重新计算所有向量 | False |

---

## 附录：第三批文件清单

### 已审阅文件（47个）

**爬虫模块 (5个)**:
- crawlers/base.py
- crawlers/factory.py
- crawlers/xinhua.py
- crawlers/people.py
- crawlers/__init__.py

**调度器 (2个)**:
- scheduler/task_scheduler.py
- scheduler/__init__.py

**CI/CD (3个)**:
- .github/workflows/collect.yml
- .github/workflows/report.yml
- .github/workflows/send_email.yml

**商业化模块 (11个)**:
- commercial/web/app.py
- commercial/web/__init__.py
- commercial/subscription/subscriber_manager.py
- commercial/subscription/__init__.py
- commercial/compliance/content_filter.py
- commercial/compliance/source_filter.py
- commercial/compliance/field_mapper.py
- commercial/compliance/ai_sensitive_checker.py
- commercial/compliance/__init__.py
- commercial/services/email_service.py
- commercial/services/__init__.py

**测试模块 (15个)**:
- tests/conftest.py
- tests/test_gap_driven_architecture.py
- tests/test_smart_backtrack.py
- tests/unit/__init__.py
- tests/unit/test_utils.py
- tests/unit/test_database.py
- tests/unit/test_config.py
- tests/integration/__init__.py
- tests/integration/test_rss.py
- tests/integration/test_ai_processor.py
- tests/integration/test_report.py
- tests/integration/test_filters.py
- tests/integration/test_bge3_engine.py
- tests/fixtures/__init__.py
- tests/fixtures/sample_data.py

**脚本工具 (30个)**:
- scripts/automation/setup_windows_tasks.ps1
- scripts/automation/setup_windows_tasks.bat
- scripts/automation/run_collect_and_report.bat
- scripts/automation/run_collect_auto.bat
- scripts/automation/run_report_auto.bat
- scripts/automation/run_send_email_auto.bat
- scripts/database/backfill_embeddings.py
- scripts/database/migrate_add_embedding.py
- scripts/database/db_manager.py
- scripts/database/migrate_schema.py
- scripts/database/migrate_to_sqlite.py
- scripts/database/import_sql.py
- scripts/database/export_and_rebuild.py
- scripts/database/restore_backup.py
- scripts/database/restore_db_simple.py
- scripts/database/repair_db.py
- scripts/maintenance/recheck_pending_news.py
- scripts/maintenance/organize_charts.py
- scripts/maintenance/fix_domain_labels.py
- scripts/maintenance/domain_classifier.py
- scripts/maintenance/backfill_domain.py
- scripts/deployment/auto_backup.py
- scripts/deployment/health_check.py
- scripts/deployment/test_system.py
- scripts/deployment/test_persistence.py
- scripts/tools/init_knowledge_base.py
- scripts/tools/check_env.py
- scripts/tools/check_data.py
- scripts/tools/check_score.py
- scripts/tools/check_tags.py

**基础设施 (8个)**:
- requirements.txt
- requirements.lock
- pyproject.toml
- pytest.ini
- docker-compose.yml
- Dockerfile
- .env.example
- .pre-commit-config.yaml

**根目录脚本 (1个)**:
- check_entity_fields.py

---

**文档结束**

本批次完成了阶段10-17的审阅和文档编写，涵盖爬虫模块、调度与CI/CD、脚本工具、商业化模块、测试模块、基础设施和数据库脚本。
