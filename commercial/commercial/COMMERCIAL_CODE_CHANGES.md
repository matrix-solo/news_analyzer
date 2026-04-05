# 代码改造清单

**版本**: 1.0.0  
**日期**: 2026-03-13  
**关联文档**: [COMMERCIAL_DESIGN.md](./COMMERCIAL_DESIGN.md)

---

## 目录

1. [核心引擎改造](#一核心引擎改造)
2. [商业化项目新建](#二商业化项目新建)
3. [修改优先级说明](#三修改优先级说明)

---

## 一、核心引擎改造

### 1.1 新增文件

| 文件路径 | 说明 | 优先级 |
|----------|------|--------|
| `core/__init__.py` | 核心接口层入口 | P0 |
| `core/interfaces.py` | 基类接口定义 | P0 |
| `core/hooks.py` | 钩子机制实现 | P0 |
| `core/engine.py` | 引擎封装类 | P0 |

### 1.2 修改文件

#### 1.2.1 pyproject.toml

**文件**: `pyproject.toml`

**修改点**:

```diff
[project]
- name = "news-analyzer"
+ name = "news-analyzer-core"
- version = "1.0.0"
+ version = "3.14.0"
- description = "新闻分析与报告生成系统"
+ description = "News analysis core engine - for personal use and commercial packaging"

[project.optional-dependencies]
dev = [
    # ... 现有配置 ...
]
+ commercial = [
+     "fastapi>=0.100.0",
+     "uvicorn>=0.23.0",
+     "python-jose>=3.3.0",
+     "passlib>=1.7.4",
+ ]
```

**工作量**: 0.5天

---

#### 1.2.2 config/manager.py

**文件**: `config/manager.py`

**修改点**:

1. 支持外部配置注入
2. 支持配置覆盖
3. 添加配置合并方法

```diff
class ConfigManager:
    """统一配置管理器"""

-   def __init__(self, project_root: Optional[Path] = None):
+   def __init__(
+       self,
+       project_root: Optional[Path] = None,
+       config_override: Optional[Dict[str, Any]] = None,
+   ):
        self.project_root = project_root or Path(__file__).parent.parent
        self._configs: Dict[str, Any] = {}
        self._loaded = False
+       
+       if config_override:
+           self._configs.update(config_override)

+   def merge_config(self, key: str, value: Any) -> None:
+       """合并配置项"""
+       if key in self._configs and isinstance(self._configs[key], dict) and isinstance(value, dict):
+           self._configs[key].update(value)
+       else:
+           self._configs[key] = value

+   def set_config(self, key: str, value: Any) -> None:
+       """设置配置项"""
+       self._configs[key] = value
```

**工作量**: 0.5天

---

#### 1.2.3 rss/collector.py

**文件**: `rss/collector.py`

**修改点**:

1. 支持外部信源配置注入
2. 添加采集后钩子调用点

```diff
class RSSCollector:
    """RSS采集器"""
    
-   def __init__(self, source_manager: RSSSourceManager = None, config_path: str = None):
+   def __init__(
+       self,
+       source_manager: RSSSourceManager = None,
+       config_path: str = None,
+       source_filter: Optional[Callable] = None,
+   ):
        self.logger = logging.getLogger("RSSCollector")
        self.parser = RSSParser()
        self.source_manager = source_manager or RSSSourceManager(config_path)
        self.health_monitor = get_health_monitor()
        self.session = requests.Session()
+       self.source_filter = source_filter
        
        # ... 现有代码 ...

+   def set_source_filter(self, filter_func: Callable) -> None:
+       """设置信源过滤器"""
+       self.source_filter = filter_func

+   def _apply_source_filter(self, news_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
+       """应用信源过滤器"""
+       if self.source_filter is None:
+           return news_item
+       return self.source_filter(news_item)
```

**工作量**: 1天

---

#### 1.2.4 filters/ai_filter_agent.py

**文件**: `filters/ai_filter_agent.py`

**修改点**:

1. 支持合规提示词注入
2. 添加领域映射配置

```diff
@dataclass
class AIFactCheckResult:
    """AI事实判断结果"""
    # ... 现有字段 ...
+   compliance_status: str = "passed"  # passed/pending_review/blocked
+   compliance_notes: str = ""

class AIFilterAgent:
    """AI判断器"""
    
-   def __init__(self):
+   def __init__(
+       self,
+       compliance_prompts: Optional[Dict[str, str]] = None,
+       domain_mapping: Optional[Dict[str, str]] = None,
+   ):
        self.ai_processor = AIProcessor()
+       self.compliance_prompts = compliance_prompts or {}
+       self.domain_mapping = domain_mapping or {}
        
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
+       if "system" in self.compliance_prompts:
+           return self.compliance_prompts["system"]
        return _FACT_CHECK_SYSTEM

+   def _map_domain(self, domain: str) -> str:
+       """领域映射"""
+       return self.domain_mapping.get(domain, domain)
```

**工作量**: 1天

---

#### 1.2.5 processors/ai_processor.py

**文件**: `processors/ai_processor.py`

**修改点**:

1. 支持合规提示词注入
2. 添加分析结果过滤钩子

```diff
class AIProcessor:
    """AI处理模块"""
    
-   def __init__(self):
+   def __init__(
+       self,
+       compliance_prompts: Optional[Dict[str, str]] = None,
+   ):
        # ... 现有初始化代码 ...
+       self.compliance_prompts = compliance_prompts or {}

+   def set_compliance_prompts(self, prompts: Dict[str, str]) -> None:
+       """设置合规提示词"""
+       self.compliance_prompts = prompts

+   def _get_compliance_prompt(self, prompt_type: str) -> Optional[str]:
+       """获取合规提示词"""
+       return self.compliance_prompts.get(prompt_type)
```

**工作量**: 0.5天

---

#### 1.2.6 generators/report_generator.py

**文件**: `generators/report_generator.py`

**修改点**:

1. 支持输出内容重构
2. 添加免责声明
3. 弱化原文链接展示

```diff
class ReportGenerator:
    """报告生成器"""
    
-   def __init__(self, template_name: str = None, enable_rag: bool = True):
+   def __init__(
+       self,
+       template_name: str = None,
+       enable_rag: bool = True,
+       output_filter: Optional[Callable] = None,
+       compliance_config: Optional[Dict[str, Any]] = None,
+   ):
        # ... 现有初始化代码 ...
+       self.output_filter = output_filter
+       self.compliance_config = compliance_config or {}

+   def _apply_output_filter(self, news: Dict[str, Any]) -> Optional[Dict[str, Any]]:
+       """应用输出过滤器"""
+       if self.output_filter is None:
+           return news
+       return self.output_filter(news)

+   def _add_disclaimer(self, lines: List[str]) -> List[str]:
+       """添加免责声明"""
+       if not self.compliance_config.get("disclaimer", {}).get("enabled", False):
+           return lines
+       
+       disclaimer_text = self.compliance_config.get("disclaimer", {}).get(
+           "text",
+           "本产品为AI分析工具，内容仅供参考。"
+       )
+       lines.extend([
+           "",
+           "---",
+           f"*{disclaimer_text}*",
+       ])
+       return lines

    def _format_brief_news(self, index: int, news: Dict) -> List[str]:
        """格式化简要摘要新闻"""
        # ... 现有代码 ...
        
        # 弱化原文链接展示
        if url:
-           lines.append(f"- **原文链接**：[点击查看]({url})")
+           lines.append(f"- *参考来源：[{source}]({url})*")
```

**工作量**: 1天

---

#### 1.2.7 storage/database.py

**文件**: `storage/database.py`

**修改点**:

1. 新增合规相关字段
2. 支持合规状态查询

```diff
@dataclass
class NewsData:
    """新闻数据结构"""
    # ... 现有字段 ...
+   compliance_status: Optional[str] = None  # passed/pending_review/blocked
+   compliance_notes: Optional[str] = None
+   insight_only: bool = False  # 是否仅输出分析结果

class NewsDatabase:
    """新闻数据库管理器"""
    
    INSERT_NEWS_SQL = """
        INSERT INTO news (
            id, title, translated_title, link, source, source_name,
            pub_date, content, summary,
            who, what, when_time, where_place, why, how,
            domain, tags, keywords,
            score, score_timeliness, score_importance, score_credibility, score_impact,
-           source_reliability_score, extraction_method, raw_item_json, access_time
+           source_reliability_score, extraction_method, raw_item_json, access_time,
+           compliance_status, compliance_notes, insight_only
        ) VALUES (
            :news_id, :title, :translated_title, :link, :source, :source_name,
            :pub_date, :content, :summary,
            :who, :what, :when_time, :where_place, :why, :how,
            :domain, :tags, :keywords,
            :score, :score_timeliness, :score_importance, :score_credibility, :score_impact,
-           :source_reliability_score, :extraction_method, :raw_item_json, :access_time
+           :source_reliability_score, :extraction_method, :raw_item_json, :access_time,
+           :compliance_status, :compliance_notes, :insight_only
        )
    """

+   def _init_database(self):
+       """初始化数据库 - 添加合规字段"""
+       # ... 现有代码 ...
+       
+       # 添加合规字段（如果不存在）
+       try:
+           self._execute_with_retry(
+               conn,
+               "ALTER TABLE news ADD COLUMN compliance_status TEXT DEFAULT 'passed'"
+           )
+           self._execute_with_retry(
+               conn,
+               "ALTER TABLE news ADD COLUMN compliance_notes TEXT"
+           )
+           self._execute_with_retry(
+               conn,
+               "ALTER TABLE news ADD COLUMN insight_only INTEGER DEFAULT 0"
+           )
+       except sqlite3.OperationalError:
+           pass  # 字段已存在

+   def get_news_by_compliance_status(
+       self,
+       status: str,
+       limit: int = 100,
+   ) -> List[Dict[str, Any]]:
+       """按合规状态查询新闻"""
+       # 实现查询逻辑
+       pass
```

**工作量**: 1天

---

## 二、商业化项目新建

### 2.1 项目结构

```
insight_hub/
├── core/
│   ├── __init__.py
│   └── engine.py              # CommercialEngine
├── compliance/
│   ├── __init__.py
│   ├── source_filter.py
│   ├── content_filter.py
│   ├── output_filter.py
│   ├── keywords.yaml
│   └── prompts.py
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── reports.py
│   │   ├── events.py
│   │   ├── subscriptions.py
│   │   └── user.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py
│   │   └── dependencies.py
│   └── middleware/
│       ├── __init__.py
│       └── rate_limit.py
├── subscription/
│   ├── __init__.py
│   ├── manager.py
│   ├── email_service.py
│   └── templates/
│       ├── welcome.html
│       ├── daily_report.html
│       └── expiry_reminder.html
├── users/
│   ├── __init__.py
│   ├── models.py
│   └── service.py
├── storage/
│   ├── __init__.py
│   └── database.py
├── config/
│   ├── sources.yaml
│   ├── compliance.yaml
│   └── subscription.yaml
├── data/
│   └── insight_hub.db
├── tests/
│   ├── __init__.py
│   ├── test_compliance.py
│   ├── test_api.py
│   └── test_subscription.py
├── scheduler/
│   ├── __init__.py
│   └── run.py
├── pyproject.toml
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### 2.2 新建文件清单

| 文件路径 | 说明 | 优先级 | 工作量 |
|----------|------|--------|--------|
| `core/__init__.py` | 核心模块入口 | P0 | 0.1天 |
| `core/engine.py` | CommercialEngine封装 | P0 | 1天 |
| `compliance/__init__.py` | 合规模块入口 | P0 | 0.1天 |
| `compliance/source_filter.py` | 信源过滤器 | P0 | 0.5天 |
| `compliance/content_filter.py` | 内容过滤器 | P0 | 0.5天 |
| `compliance/output_filter.py` | 输出过滤器 | P0 | 0.5天 |
| `compliance/keywords.yaml` | 敏感词库 | P0 | 0.5天 |
| `compliance/prompts.py` | 合规提示词 | P0 | 0.2天 |
| `users/__init__.py` | 用户模块入口 | P1 | 0.1天 |
| `users/models.py` | 用户模型 | P1 | 0.5天 |
| `users/service.py` | 用户服务 | P1 | 0.5天 |
| `subscription/__init__.py` | 订阅模块入口 | P1 | 0.1天 |
| `subscription/manager.py` | 订阅管理器 | P1 | 0.5天 |
| `subscription/email_service.py` | 邮件服务 | P1 | 0.5天 |
| `subscription/templates/*.html` | 邮件模板 | P2 | 0.5天 |
| `storage/__init__.py` | 存储模块入口 | P1 | 0.1天 |
| `storage/database.py` | 商业化数据库 | P1 | 1天 |
| `api/__init__.py` | API模块入口 | P2 | 0.1天 |
| `api/main.py` | FastAPI入口 | P2 | 0.5天 |
| `api/routes/*.py` | API路由 | P2 | 1天 |
| `api/auth/*.py` | 认证模块 | P2 | 0.5天 |
| `api/middleware/*.py` | 中间件 | P2 | 0.5天 |
| `config/sources.yaml` | 商业化信源配置 | P0 | 0.5天 |
| `config/compliance.yaml` | 合规配置 | P0 | 0.2天 |
| `config/subscription.yaml` | 订阅配置 | P1 | 0.2天 |
| `scheduler/run.py` | 调度运行器 | P1 | 0.5天 |
| `tests/*.py` | 测试文件 | P2 | 1天 |
| `pyproject.toml` | 项目配置 | P0 | 0.2天 |
| `requirements.txt` | 依赖列表 | P0 | 0.1天 |
| `.env.example` | 环境变量示例 | P0 | 0.1天 |
| `Dockerfile` | Docker配置 | P2 | 0.2天 |
| `docker-compose.yml` | Docker编排 | P2 | 0.2天 |
| `README.md` | 项目说明 | P2 | 0.5天 |

### 2.3 关键文件详细说明

#### 2.3.1 core/engine.py

**功能**: 封装核心引擎，注入合规逻辑

**关键代码**:

```python
from news_analyzer import NewsAnalyzerEngine, HookManager, HookPoint, FilterHook
from compliance.source_filter import SourceFilter
from compliance.content_filter import ContentFilter
from compliance.output_filter import OutputFilter


class CommercialEngine:
    """商业化引擎"""
    
    def __init__(self, config_path: str = None):
        self.engine = NewsAnalyzerEngine(config_path=config_path)
        self.hook_manager = self.engine.hook_manager
        
        self._inject_compliance_filters()
    
    def _inject_compliance_filters(self):
        """注入合规过滤器"""
        source_filter = SourceFilter("config/sources.yaml")
        content_filter = ContentFilter("compliance/keywords.yaml")
        output_filter = OutputFilter("compliance/keywords.yaml")
        
        self.hook_manager.register(FilterHook(
            name="source_filter",
            hook_point=HookPoint.POST_COLLECT,
            filter_func=source_filter.filter,
            priority=10,
        ))
        
        self.hook_manager.register(FilterHook(
            name="content_filter",
            hook_point=HookPoint.PRE_PROCESS,
            filter_func=content_filter.filter,
            priority=20,
        ))
        
        self.hook_manager.register(FilterHook(
            name="output_filter",
            hook_point=HookPoint.PRE_GENERATE,
            filter_func=output_filter.filter,
            priority=30,
        ))
    
    def run_pipeline(self):
        """运行流水线"""
        return self.engine.run_pipeline()
```

---

## 三、修改优先级说明

### 3.1 优先级定义

| 优先级 | 说明 | 时间要求 |
|--------|------|----------|
| P0 | 必须完成，阻塞后续工作 | 第1周 |
| P1 | 重要，影响核心功能 | 第2周 |
| P2 | 可延后，不影响核心流程 | 第3-4周 |

### 3.2 阶段一（MVP）必须完成的修改

**核心引擎改造**:

| 文件 | 修改类型 | 优先级 | 工作量 |
|------|----------|--------|--------|
| `core/__init__.py` | 新增 | P0 | 0.1天 |
| `core/interfaces.py` | 新增 | P0 | 0.5天 |
| `core/hooks.py` | 新增 | P0 | 0.5天 |
| `core/engine.py` | 新增 | P0 | 1天 |
| `pyproject.toml` | 修改 | P0 | 0.5天 |
| `config/manager.py` | 修改 | P0 | 0.5天 |

**商业化项目新建**:

| 文件 | 优先级 | 工作量 |
|------|--------|--------|
| `core/engine.py` | P0 | 1天 |
| `compliance/source_filter.py` | P0 | 0.5天 |
| `compliance/content_filter.py` | P0 | 0.5天 |
| `compliance/output_filter.py` | P0 | 0.5天 |
| `compliance/keywords.yaml` | P0 | 0.5天 |
| `compliance/prompts.py` | P0 | 0.2天 |
| `config/sources.yaml` | P0 | 0.5天 |
| `config/compliance.yaml` | P0 | 0.2天 |
| `pyproject.toml` | P0 | 0.2天 |
| `requirements.txt` | P0 | 0.1天 |
| `.env.example` | P0 | 0.1天 |

**阶段一总工作量**: 约8天

---

### 3.3 阶段二（产品化）需要完成的修改

**核心引擎改造**:

| 文件 | 修改类型 | 优先级 | 工作量 |
|------|----------|--------|--------|
| `rss/collector.py` | 修改 | P1 | 1天 |
| `filters/ai_filter_agent.py` | 修改 | P1 | 1天 |
| `processors/ai_processor.py` | 修改 | P1 | 0.5天 |
| `generators/report_generator.py` | 修改 | P1 | 1天 |
| `storage/database.py` | 修改 | P1 | 1天 |

**商业化项目新建**:

| 文件 | 优先级 | 工作量 |
|------|--------|--------|
| `users/models.py` | P1 | 0.5天 |
| `users/service.py` | P1 | 0.5天 |
| `subscription/manager.py` | P1 | 0.5天 |
| `subscription/email_service.py` | P1 | 0.5天 |
| `storage/database.py` | P1 | 1天 |
| `config/subscription.yaml` | P1 | 0.2天 |
| `scheduler/run.py` | P1 | 0.5天 |

**阶段二总工作量**: 约7天

---

### 3.4 阶段三（API服务）需要完成的修改

**商业化项目新建**:

| 文件 | 优先级 | 工作量 |
|------|--------|--------|
| `api/main.py` | P2 | 0.5天 |
| `api/routes/*.py` | P2 | 1天 |
| `api/auth/*.py` | P2 | 0.5天 |
| `api/middleware/*.py` | P2 | 0.5天 |
| `subscription/templates/*.html` | P2 | 0.5天 |
| `tests/*.py` | P2 | 1天 |
| `Dockerfile` | P2 | 0.2天 |
| `docker-compose.yml` | P2 | 0.2天 |
| `README.md` | P2 | 0.5天 |

**阶段三总工作量**: 约5天

---

## 四、风险与注意事项

### 4.1 核心引擎改造风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 改造影响现有功能 | 高 | 保持向后兼容，增加单元测试 |
| 钩子机制性能开销 | 中 | 按需注册钩子，避免过度使用 |
| 配置注入复杂度 | 中 | 提供默认配置，简化使用方式 |

### 4.2 商业化项目风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 敏感词库不完整 | 高 | 持续更新，用户反馈机制 |
| 合规判断误杀 | 中 | 二级审核机制，人工复核 |
| 用户数据安全 | 高 | 密码加密，敏感信息脱敏 |

### 4.3 注意事项

1. **保持向后兼容**: 核心引擎改造不能破坏现有功能
2. **增量开发**: 每个阶段独立验证，确保可回滚
3. **测试覆盖**: 关键模块必须有单元测试
4. **文档同步**: 代码修改后同步更新文档

---

## 五、总结

本清单详细列出了商业化改造所需的所有文件修改点，包括：

- **核心引擎改造**: 6个新增文件，6个修改文件
- **商业化项目新建**: 约35个新文件

**总工作量估算**:
- 阶段一（MVP）: 约8天
- 阶段二（产品化）: 约7天
- 阶段三（API服务）: 约5天
- **合计**: 约20天（1个月）

下一步：根据本清单制定详细的实施计划。
