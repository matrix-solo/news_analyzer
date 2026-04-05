# 商业化项目技术设计文档

**版本**: 1.0.0  
**日期**: 2026-03-13  
**状态**: 设计阶段

---

## 目录

1. [项目概述](#一项目概述)
2. [架构设计](#二架构设计)
3. [核心引擎改造](#三核心引擎改造)
4. [合规模块设计](#四合规模块设计)
5. [API层设计](#五api层设计)
6. [订阅管理设计](#六订阅管理设计)
7. [数据库设计](#七数据库设计)
8. [配置设计](#八配置设计)
9. [部署设计](#九部署设计)

---

## 一、项目概述

### 1.1 项目目标

将现有 `news_analyzer` 项目作为核心引擎，构建一个独立的商业化项目 `insight_hub`，实现：

- **合规性**：符合国内法规要求，避免新闻传播资质问题
- **商业化**：支持订阅付费，实现可持续收入
- **可扩展**：支持API服务、企业版等增值服务

### 1.2 核心原则

| 原则 | 说明 |
|------|------|
| **职责分离** | 核心引擎与商业化包装层分离 |
| **风险隔离** | 商业化问题不影响个人项目 |
| **配置驱动** | 行为差异通过配置控制，而非代码分支 |
| **渐进式** | 分阶段实施，每阶段可独立验证 |

### 1.3 项目结构

```
news_analyzer/              # 核心引擎（现有项目，小幅改造）
├── rss/                    # RSS采集模块
├── filters/                # 过滤模块
├── processors/             # 处理模块
├── generators/             # 报告生成模块
├── storage/                # 存储模块
├── knowledge/              # 知识库模块
├── analysts/               # 分析模块
├── utils/                  # 工具模块
├── config/                 # 配置模块
├── core/                   # [新增] 核心接口层
│   ├── __init__.py
│   ├── engine.py           # 引擎封装
│   ├── hooks.py            # 钩子机制
│   └── interfaces.py       # 接口定义
└── pyproject.toml          # [修改] 打包配置

insight_hub/                # 商业化项目（新建）
├── core/                   # 核心引擎引用
│   └── engine.py           # 包装核心引擎
├── compliance/             # 合规模块
│   ├── __init__.py
│   ├── source_filter.py    # 信源过滤
│   ├── content_filter.py   # 内容过滤
│   ├── output_filter.py    # 输出过滤
│   └── keywords.yaml       # 敏感词库
├── api/                    # API层
│   ├── __init__.py
│   ├── main.py             # FastAPI入口
│   ├── routes/             # 路由
│   ├── auth/               # 认证
│   └── middleware/         # 中间件
├── subscription/           # 订阅模块
│   ├── __init__.py
│   ├── manager.py          # 订阅管理
│   └── email_service.py    # 邮件服务
├── users/                  # 用户模块
│   ├── __init__.py
│   ├── models.py           # 用户模型
│   └── service.py          # 用户服务
├── config/                 # 配置
│   ├── sources.yaml        # 商业化信源配置
│   ├── compliance.yaml     # 合规配置
│   └── subscription.yaml   # 订阅配置
├── data/                   # 数据目录
│   └── insight_hub.db      # 商业化数据库
├── tests/                  # 测试
├── pyproject.toml          # 项目配置
└── README.md               # 项目说明
```

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              insight_hub（商业化层）                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   API层     │  │  订阅模块   │  │  用户模块   │  │  合规模块   │        │
│  │  (FastAPI)  │  │ (邮件推送)  │  │  (认证)     │  │  (过滤)     │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
│         └────────────────┴────────────────┴────────────────┘               │
│                                   │                                         │
│                         ┌─────────▼─────────┐                               │
│                         │   CommercialEngine │                               │
│                         │   (合规包装层)      │                               │
│                         └─────────┬─────────┘                               │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    │ pip install / 本地引用
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          news_analyzer（核心引擎）                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  RSS采集    │  │  AI处理     │  │  报告生成   │  │  知识库     │        │
│  │  (rss/)     │  │(processors/)│  │(generators/)│  │(knowledge/) │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  过滤器     │  │  存储层     │  │  配置管理   │  │  核心接口   │        │
│  │ (filters/)  │  │ (storage/)  │  │ (config/)   │  │ (core/)     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           商业化数据流（五层防护）                            │
└─────────────────────────────────────────────────────────────────────────────┘

RSS采集
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 第一层：源头过滤层 (SourceFilter)                                            │
│   - 信源白名单：仅国内合规信源                                                │
│   - 领域限制：国际信源仅允许经济/科技                                         │
│   - 配置驱动：sources_commercial.yaml                                        │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 第二层：内容解析层 (ContentParser + 领域映射)                                │
│   - 领域重定向：政治 → 宏观动态                                              │
│   - 规则优先：YAML规则库驱动                                                 │
│   - AI兜底：启用合规提示词                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 第三层：AI分析层 (AIProcessor + 合规指令)                                    │
│   - 提示词约束：聚焦影响，避免立场                                            │
│   - 自动降级：敏感事件标记"暂无分析"                                          │
│   - 领域限制：政治类仅输出客观事实                                            │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 第四层：输出过滤层 (OutputFilter)                                            │
│   - 关键词拦截：一级敏感词直接删除                                            │
│   - 二级审核：二级敏感词标记人工审核                                          │
│   - 内容重构：移除原文，仅保留分析                                            │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 第五层：报告生成层 (ReportGenerator + 合规输出)                              │
│   - 内容重构：事件概述、影响分析、趋势预判                                    │
│   - 弱化原文：参考来源小字展示                                                │
│   - 免责声明：每份报告附带声明                                                │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
存储/推送/展示
```

### 2.3 模块依赖关系

```
insight_hub/
│
├── core/engine.py
│   └── 依赖: news_analyzer (核心引擎)
│
├── compliance/
│   ├── source_filter.py
│   │   └── 依赖: config/sources_commercial.yaml
│   ├── content_filter.py
│   │   └── 依赖: config/compliance.yaml
│   └── output_filter.py
│       └── 依赖: compliance/keywords.yaml
│
├── api/
│   ├── main.py
│   │   └── 依赖: core/engine.py, api/routes/, api/auth/
│   ├── routes/
│   │   └── 依赖: core/engine.py, users/service.py
│   └── auth/
│       └── 依赖: users/models.py
│
├── subscription/
│   └── 依赖: core/engine.py, users/service.py
│
└── users/
    └── 依赖: storage/database.py
```

---

## 三、核心引擎改造

### 3.1 改造目标

将 `news_analyzer` 改造为可被外部项目引用的核心引擎包，支持：

- 通过 pip 安装或本地引用
- 配置外部注入
- 钩子机制（外部注入过滤器）

### 3.2 新增核心接口层

**文件**: `news_analyzer/core/__init__.py`

```python
"""
核心引擎接口层

提供统一的引擎封装，支持外部项目引用。
"""

from .engine import NewsAnalyzerEngine
from .hooks import HookManager, FilterHook
from .interfaces import (
    BaseFilter,
    BaseCollector,
    BaseProcessor,
    BaseGenerator,
)

__all__ = [
    "NewsAnalyzerEngine",
    "HookManager",
    "FilterHook",
    "BaseFilter",
    "BaseCollector",
    "BaseProcessor",
    "BaseGenerator",
]
```

**文件**: `news_analyzer/core/interfaces.py`

```python
"""
核心接口定义

定义过滤器、采集器、处理器、生成器的基类接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseFilter(ABC):
    """过滤器基类"""
    
    @abstractmethod
    def filter(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        过滤数据
        
        Args:
            data: 待过滤的数据
        
        Returns:
            过滤后的数据，返回None表示丢弃
        """
        pass
    
    @property
    def name(self) -> str:
        """过滤器名称"""
        return self.__class__.__name__


class BaseCollector(ABC):
    """采集器基类"""
    
    @abstractmethod
    def collect(self, sources: List[str], **kwargs) -> List[Dict[str, Any]]:
        """采集数据"""
        pass


class BaseProcessor(ABC):
    """处理器基类"""
    
    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据"""
        pass


class BaseGenerator(ABC):
    """生成器基类"""
    
    @abstractmethod
    def generate(self, data: List[Dict[str, Any]], **kwargs) -> str:
        """生成输出"""
        pass
```

**文件**: `news_analyzer/core/hooks.py`

```python
"""
钩子机制

支持外部注入过滤器，实现行为扩展。
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class HookPoint(Enum):
    """钩子挂载点"""
    PRE_COLLECT = "pre_collect"           # 采集前
    POST_COLLECT = "post_collect"         # 采集后
    PRE_FILTER = "pre_filter"             # 过滤前
    POST_FILTER = "post_filter"           # 过滤后
    PRE_PROCESS = "pre_process"           # 处理前
    POST_PROCESS = "post_process"         # 处理后
    PRE_GENERATE = "pre_generate"         # 生成前
    POST_GENERATE = "post_generate"       # 生成后


@dataclass
class FilterHook:
    """过滤器钩子"""
    name: str
    hook_point: HookPoint
    filter_func: Callable[[Any], Optional[Any]]
    priority: int = 100  # 数值越小优先级越高
    enabled: bool = True


class HookManager:
    """钩子管理器"""
    
    def __init__(self):
        self._hooks: Dict[HookPoint, List[FilterHook]] = {
            point: [] for point in HookPoint
        }
    
    def register(self, hook: FilterHook) -> None:
        """注册钩子"""
        self._hooks[hook.hook_point].append(hook)
        self._hooks[hook.hook_point].sort(key=lambda h: h.priority)
    
    def unregister(self, name: str) -> bool:
        """注销钩子"""
        for point in HookPoint:
            for i, hook in enumerate(self._hooks[point]):
                if hook.name == name:
                    self._hooks[point].pop(i)
                    return True
        return False
    
    def execute(self, hook_point: HookPoint, data: Any) -> Any:
        """执行钩子"""
        hooks = self._hooks[hook_point]
        result = data
        
        for hook in hooks:
            if not hook.enabled:
                continue
            
            result = hook.filter_func(result)
            
            if result is None:
                return None
        
        return result
    
    def get_hooks(self, hook_point: HookPoint) -> List[FilterHook]:
        """获取指定点的钩子列表"""
        return self._hooks[hook_point]
```

**文件**: `news_analyzer/core/engine.py`

```python
"""
新闻分析引擎封装

提供统一的引擎接口，支持外部项目引用。
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from .hooks import HookManager, HookPoint, FilterHook
from config.manager import ConfigManager


class NewsAnalyzerEngine:
    """
    新闻分析引擎
    
    封装核心功能，支持：
    - 配置外部注入
    - 钩子机制
    - 模块化调用
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化引擎
        
        Args:
            config_path: 配置文件路径（覆盖默认）
            config_override: 配置覆盖项
        """
        self.config = ConfigManager(
            project_root=Path(config_path).parent if config_path else None
        )
        
        if config_override:
            self._apply_config_override(config_override)
        
        self.hook_manager = HookManager()
        
        self._collector = None
        self._filter_agent = None
        self._processor = None
        self._generator = None
    
    def _apply_config_override(self, override: Dict[str, Any]) -> None:
        """应用配置覆盖"""
        for key, value in override.items():
            self.config._configs[key] = value
    
    def register_hook(self, hook: FilterHook) -> None:
        """注册钩子"""
        self.hook_manager.register(hook)
    
    def unregister_hook(self, name: str) -> bool:
        """注销钩子"""
        return self.hook_manager.unregister(name)
    
    @property
    def collector(self):
        """延迟加载采集器"""
        if self._collector is None:
            from rss.collector import RSSCollector
            from rss.sources import RSSSourceManager
            
            source_manager = RSSSourceManager()
            self._collector = RSSCollector(source_manager)
        return self._collector
    
    @property
    def filter_agent(self):
        """延迟加载过滤器"""
        if self._filter_agent is None:
            from filters.ai_filter_agent import AIFilterAgent
            self._filter_agent = AIFilterAgent()
        return self._filter_agent
    
    @property
    def processor(self):
        """延迟加载处理器"""
        if self._processor is None:
            from processors.ai_processor import AIProcessor
            self._processor = AIProcessor()
        return self._processor
    
    @property
    def generator(self):
        """延迟加载生成器"""
        if self._generator is None:
            from generators.report_generator import ReportGenerator
            self._generator = ReportGenerator()
        return self._generator
    
    def collect(self, sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        采集新闻
        
        Args:
            sources: 指定信源列表，None表示全部
        
        Returns:
            采集到的新闻列表
        """
        self.hook_manager.execute(HookPoint.PRE_COLLECT, sources)
        
        result = self.collector.collect_all(sources)
        
        result = self.hook_manager.execute(HookPoint.POST_COLLECT, result)
        
        return result or []
    
    def filter_news(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤新闻
        
        Args:
            news_list: 新闻列表
        
        Returns:
            过滤后的新闻列表
        """
        result = []
        
        for news in news_list:
            processed = self.hook_manager.execute(HookPoint.PRE_FILTER, news)
            if processed is None:
                continue
            
            filtered = self.filter_agent.filter(processed)
            if filtered is None:
                continue
            
            filtered = self.hook_manager.execute(HookPoint.POST_FILTER, filtered)
            if filtered is not None:
                result.append(filtered)
        
        return result
    
    def process(self, news: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理新闻
        
        Args:
            news: 新闻数据
        
        Returns:
            处理后的数据
        """
        processed = self.hook_manager.execute(HookPoint.PRE_PROCESS, news)
        if processed is None:
            return news
        
        result = self.processor.process(processed)
        
        result = self.hook_manager.execute(HookPoint.POST_PROCESS, result)
        
        return result or news
    
    def generate_report(
        self,
        news_list: List[Dict[str, Any]],
        report_type: str = "brief",
        **kwargs,
    ) -> str:
        """
        生成报告
        
        Args:
            news_list: 新闻列表
            report_type: 报告类型 (brief/depth)
        
        Returns:
            报告文件路径
        """
        processed = self.hook_manager.execute(HookPoint.PRE_GENERATE, news_list)
        if processed is None:
            processed = news_list
        
        if report_type == "brief":
            result = self.generator.generate_brief_report(processed, **kwargs)
        else:
            result = self.generator.generate_depth_reports(processed, **kwargs)
        
        result = self.hook_manager.execute(HookPoint.POST_GENERATE, result)
        
        return result
    
    def run_pipeline(self, sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        运行完整流水线
        
        Args:
            sources: 指定信源列表
        
        Returns:
            执行结果统计
        """
        stats = {
            "collected": 0,
            "filtered": 0,
            "processed": 0,
            "reports_generated": 0,
        }
        
        news_list = self.collect(sources)
        stats["collected"] = len(news_list)
        
        filtered = self.filter_news(news_list)
        stats["filtered"] = len(filtered)
        
        processed = [self.process(n) for n in filtered]
        stats["processed"] = len(processed)
        
        self.generate_report(processed)
        stats["reports_generated"] = 1
        
        return stats
```

### 3.3 pyproject.toml 改造

```toml
[project]
name = "news-analyzer-core"
version = "3.14.0"
description = "News analysis core engine - for personal use and commercial packaging"
readme = "README.md"
requires-python = ">=3.9"

# ... 其他配置保持不变 ...

[project.optional-dependencies]
commercial = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "python-jose>=3.3.0",
    "passlib>=1.7.4",
]
```

---

## 四、合规模块设计

### 4.1 模块结构

```
insight_hub/compliance/
├── __init__.py
├── source_filter.py      # 信源过滤器
├── content_filter.py     # 内容过滤器
├── output_filter.py      # 输出过滤器
├── keywords.yaml         # 敏感词库
└── prompts.py            # 合规提示词
```

### 4.2 信源过滤器

**文件**: `insight_hub/compliance/source_filter.py`

```python
"""
信源过滤器

在采集阶段过滤不符合合规要求的信源。
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
import yaml
from pathlib import Path


@dataclass
class SourceRule:
    """信源规则"""
    name: str
    enabled: bool
    allowed_domains: List[str]
    blocked: bool
    block_reason: Optional[str] = None


class SourceFilter:
    """
    信源过滤器
    
    功能：
    - 白名单机制：仅允许配置的信源
    - 领域限制：限制信源可采集的领域
    - 黑名单机制：直接屏蔽特定信源
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.rules: Dict[str, SourceRule] = {}
        self.default_allowed_domains: Set[str] = {"经济", "科技", "社会"}
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> None:
        """加载信源配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        self._parse_config(config)
    
    def _parse_config(self, config: Dict[str, Any]) -> None:
        """解析配置"""
        for category, sources in config.items():
            if category in ["collection_strategy", "health_monitor_rules"]:
                continue
            
            if isinstance(sources, dict):
                for sub_category, source_list in sources.items():
                    if isinstance(source_list, list):
                        for source in source_list:
                            self._add_source_rule(source)
            elif isinstance(sources, list):
                for source in sources:
                    self._add_source_rule(source)
    
    def _add_source_rule(self, source: Dict[str, Any]) -> None:
        """添加信源规则"""
        name = source.get("name", "")
        if not name:
            return
        
        compliance = source.get("compliance", {})
        
        rule = SourceRule(
            name=name,
            enabled=source.get("enabled", True),
            allowed_domains=compliance.get("allowed_domains", list(self.default_allowed_domains)),
            blocked=compliance.get("blocked", False),
            block_reason=compliance.get("block_reason"),
        )
        
        self.rules[name] = rule
    
    def is_source_allowed(self, source_name: str) -> bool:
        """检查信源是否被允许"""
        rule = self.rules.get(source_name)
        
        if rule is None:
            return False
        
        if rule.blocked:
            return False
        
        return rule.enabled
    
    def is_domain_allowed(self, source_name: str, domain: str) -> bool:
        """检查信源是否允许采集指定领域"""
        rule = self.rules.get(source_name)
        
        if rule is None:
            return False
        
        if rule.blocked or not rule.enabled:
            return False
        
        if not rule.allowed_domains:
            return True
        
        return domain in rule.allowed_domains
    
    def filter(self, news: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        过滤新闻
        
        Args:
            news: 新闻数据
        
        Returns:
            过滤后的数据，返回None表示丢弃
        """
        source_name = news.get("source_name", "")
        domain = news.get("domain", "")
        
        if not self.is_source_allowed(source_name):
            return None
        
        if domain and not self.is_domain_allowed(source_name, domain):
            return None
        
        return news
    
    def get_allowed_sources(self) -> List[str]:
        """获取允许的信源列表"""
        return [
            name for name, rule in self.rules.items()
            if rule.enabled and not rule.blocked
        ]
    
    def get_blocked_sources(self) -> List[Dict[str, Any]]:
        """获取被屏蔽的信源列表"""
        return [
            {"name": name, "reason": rule.block_reason}
            for name, rule in self.rules.items()
            if rule.blocked
        ]
```

### 4.3 内容过滤器

**文件**: `insight_hub/compliance/content_filter.py`

```python
"""
内容过滤器

在AI分析前过滤敏感内容。
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import re
import yaml
from pathlib import Path


@dataclass
class FilterResult:
    """过滤结果"""
    passed: bool
    reason: Optional[str] = None
    matched_keywords: List[str] = None
    
    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []


class ContentFilter:
    """
    内容过滤器
    
    功能：
    - 敏感词检测
    - 领域重定向
    - 自动降级标记
    """
    
    def __init__(self, keywords_path: Optional[str] = None):
        self.level1_keywords: List[str] = []  # 直接拦截
        self.level2_keywords: List[str] = []  # 人工审核
        self.domain_mapping: Dict[str, str] = {
            "政治": "宏观动态",
            "时政": "公共事务",
        }
        
        if keywords_path:
            self.load_keywords(keywords_path)
    
    def load_keywords(self, keywords_path: str) -> None:
        """加载敏感词库"""
        with open(keywords_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        self.level1_keywords = config.get("level_1_block", {}).get("political_sensitive", [])
        self.level2_keywords = config.get("level_2_review", {}).get("political_related", [])
    
    def check_keywords(self, text: str) -> FilterResult:
        """
        检查文本中的敏感词
        
        Args:
            text: 待检查文本
        
        Returns:
            过滤结果
        """
        if not text:
            return FilterResult(passed=True)
        
        matched_l1 = []
        matched_l2 = []
        
        for keyword in self.level1_keywords:
            if keyword in text:
                matched_l1.append(keyword)
        
        if matched_l1:
            return FilterResult(
                passed=False,
                reason=f"命中一级敏感词: {matched_l1}",
                matched_keywords=matched_l1,
            )
        
        for keyword in self.level2_keywords:
            if keyword in text:
                matched_l2.append(keyword)
        
        if matched_l2:
            return FilterResult(
                passed=True,
                reason=f"命中二级敏感词，需人工审核: {matched_l2}",
                matched_keywords=matched_l2,
            )
        
        return FilterResult(passed=True)
    
    def map_domain(self, domain: str) -> str:
        """
        领域映射
        
        Args:
            domain: 原始领域
        
        Returns:
            映射后的领域
        """
        return self.domain_mapping.get(domain, domain)
    
    def should_skip_analysis(self, news: Dict[str, Any]) -> bool:
        """
        判断是否应该跳过分析
        
        Args:
            news: 新闻数据
        
        Returns:
            是否跳过
        """
        title = news.get("title", "")
        summary = news.get("summary", "")
        domain = news.get("domain", "")
        
        result = self.check_keywords(f"{title} {summary}")
        
        if not result.passed:
            return True
        
        if domain in ["政治", "时政"]:
            return True
        
        return False
    
    def filter(self, news: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        过滤新闻
        
        Args:
            news: 新闻数据
        
        Returns:
            过滤后的数据，返回None表示丢弃
        """
        title = news.get("title", "")
        content = news.get("content", "")
        summary = news.get("summary", "")
        
        result = self.check_keywords(f"{title} {content} {summary}")
        
        if not result.passed:
            return None
        
        news["compliance_status"] = "passed"
        if result.matched_keywords:
            news["compliance_status"] = "pending_review"
            news["compliance_notes"] = result.reason
        
        news["domain"] = self.map_domain(news.get("domain", ""))
        
        if self.should_skip_analysis(news):
            news["skip_analysis"] = True
            news["analysis_result"] = "暂无分析"
        
        return news
```

### 4.4 输出过滤器

**文件**: `insight_hub/compliance/output_filter.py`

```python
"""
输出过滤器

在报告生成前过滤敏感内容。
"""

from typing import Any, Dict, List, Optional
import re


class OutputFilter:
    """
    输出过滤器
    
    功能：
    - 移除原文内容
    - 敏感词二次检测
    - 内容重构
    """
    
    def __init__(self, keywords_path: Optional[str] = None):
        from .content_filter import ContentFilter
        self.content_filter = ContentFilter(keywords_path)
    
    def remove_original_content(self, news: Dict[str, Any]) -> Dict[str, Any]:
        """
        移除原文内容，仅保留分析结果
        
        Args:
            news: 新闻数据
        
        Returns:
            处理后的数据
        """
        result = news.copy()
        
        content = result.get("content", "")
        if content:
            result["content_preview"] = content[:200] + "..." if len(content) > 200 else content
            del result["content"]
        
        result["insight_only"] = True
        
        return result
    
    def filter_analysis_result(self, analysis: str) -> str:
        """
        过滤分析结果中的敏感内容
        
        Args:
            analysis: 分析文本
        
        Returns:
            过滤后的文本
        """
        result = self.content_filter.check_keywords(analysis)
        
        if not result.passed:
            return "暂无分析"
        
        if result.matched_keywords:
            for keyword in result.matched_keywords:
                analysis = analysis.replace(keyword, "***")
        
        return analysis
    
    def filter(self, news: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        过滤新闻
        
        Args:
            news: 新闻数据
        
        Returns:
            过滤后的数据
        """
        result = self.remove_original_content(news)
        
        for key in ["insight", "analysis", "depth_insight"]:
            if key in result:
                result[key] = self.filter_analysis_result(result[key])
        
        return result
```

### 4.5 敏感词库

**文件**: `insight_hub/compliance/keywords.yaml`

```yaml
# 敏感词库配置
# 
# 分级说明：
# - level_1_block: 直接拦截，不进入分析流程
# - level_2_review: 标记为人工审核，但允许进入流程

# 一级敏感词（直接拦截）
level_1_block:
  political_sensitive:
    - "台独"
    - "藏独"
    - "疆独"
    - "法轮功"
    - "六四"
    - "天安门事件"
    # ... 更多敏感词
  
  illegal_content:
    - "暴力"
    - "恐怖主义"
    - "邪教"
    # ... 更多敏感词

# 二级敏感词（人工审核）
level_2_review:
  political_related:
    - "政治改革"
    - "民主运动"
    - "维权"
    # ... 更多敏感词
  
  sensitive_topics:
    - "腐败"
    - "拆迁"
    # ... 更多敏感词

# 领域映射配置
domain_mapping:
  "政治": "宏观动态"
  "时政": "公共事务"
  "国际政治": "国际动态"
```

### 4.6 合规提示词

**文件**: `insight_hub/compliance/prompts.py`

```python
"""
合规提示词

用于AI分析的合规约束提示词。
"""

COMPLIANCE_SYSTEM_PROMPT = """
你是一个专业的信息分析专家。请对以下事件进行客观分析。

## 分析原则（重要）

1. **聚焦影响**：分析事件对经济、社会、行业的影响
2. **避免立场**：不评价政治立场、不讨论政治是非
3. **趋势预判**：基于事实预判可能的发展趋势
4. **风险提示**：客观提示可能的风险点

## 禁止内容

1. 不讨论政治立场、意识形态
2. 不评价政策对错
3. 不涉及敏感政治话题
4. 不输出主观政治评论

## 输出格式

### 事件概述
[客观描述事件本身，不涉及立场评价]

### 影响分析
- 经济影响：...
- 行业影响：...
- 社会影响：...

### 趋势预判
[基于事实的趋势分析]

### 风险提示
[客观的风险提示]
"""

DOMAIN_CLASSIFICATION_PROMPT = """
## 新闻领域分类

请判断新闻所属领域：
- **宏观动态**：政策动向、宏观经济、国际关系
- **经济**：财经、金融、产业、市场
- **科技**：技术创新、互联网、AI、半导体
- **社会**：民生、教育、医疗、环境
- **文化**：文化、艺术、娱乐
- **其他**：不属于以上领域

注意：
1. "政治"领域已重命名为"宏观动态"
2. 分析时聚焦事件影响，不涉及政治立场
"""

def get_compliance_prompt(prompt_type: str) -> str:
    """获取合规提示词"""
    prompts = {
        "system": COMPLIANCE_SYSTEM_PROMPT,
        "domain": DOMAIN_CLASSIFICATION_PROMPT,
    }
    return prompts.get(prompt_type, "")
```

---

## 五、API层设计

### 5.1 技术选型

| 组件 | 技术选择 | 理由 |
|------|----------|------|
| Web框架 | FastAPI | 高性能、自动文档、类型提示 |
| 认证 | JWT | 无状态、易扩展 |
| 数据库 | SQLite → PostgreSQL | 初期SQLite，后期迁移 |
| 缓存 | 内存缓存 | 简单场景足够 |

### 5.2 API路由设计

```
/api/v1/
├── /auth
│   ├── POST /register          # 用户注册
│   ├── POST /login             # 用户登录
│   └── POST /refresh           # 刷新Token
│
├── /reports
│   ├── GET /daily              # 获取每日报告
│   ├── GET /{report_id}        # 获取报告详情
│   ├── GET /history            # 获取历史报告
│   └── GET /search             # 搜索报告
│
├── /events
│   ├── GET /{event_id}         # 获取事件详情
│   └── GET /{event_id}/history # 获取事件历史关联
│
├── /subscriptions
│   ├── GET /                   # 获取订阅信息
│   ├── POST /                  # 创建订阅
│   └── DELETE /{sub_id}        # 取消订阅
│
└── /user
    ├── GET /profile            # 获取用户信息
    └── PUT /preferences        # 更新用户偏好
```

### 5.3 API实现示例

**文件**: `insight_hub/api/main.py`

```python
"""
FastAPI入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth, reports, events, subscriptions, user
from api.middleware.rate_limit import RateLimitMiddleware

app = FastAPI(
    title="Insight Hub API",
    description="智能信息洞察平台API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["报告"])
app.include_router(events.router, prefix="/api/v1/events", tags=["事件"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["订阅"])
app.include_router(user.router, prefix="/api/v1/user", tags=["用户"])


@app.get("/")
async def root():
    return {"message": "Insight Hub API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**文件**: `insight_hub/api/routes/reports.py`

```python
"""
报告路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import date

from api.auth.dependencies import get_current_user, get_optional_user
from users.models import User
from core.engine import CommercialEngine

router = APIRouter()
engine = CommercialEngine()


@router.get("/daily")
async def get_daily_report(
    report_date: Optional[date] = Query(None, description="报告日期"),
    domain: Optional[str] = Query(None, description="领域过滤"),
    user: Optional[User] = Depends(get_optional_user),
):
    """
    获取每日报告
    
    - 免费用户：简要摘要（5条）
    - 付费用户：完整报告
    """
    if report_date is None:
        report_date = date.today()
    
    is_paid = user and user.is_paid_user
    
    if is_paid:
        return engine.get_full_report(report_date, domain)
    else:
        return engine.get_brief_report(report_date, limit=5)


@router.get("/{report_id}")
async def get_report_detail(
    report_id: str,
    user: User = Depends(get_current_user),
):
    """
    获取报告详情
    
    需要登录，付费用户可查看完整内容。
    """
    if not user.is_paid_user:
        raise HTTPException(status_code=403, detail="需要订阅才能查看完整报告")
    
    return engine.get_report_by_id(report_id)


@router.get("/history")
async def get_history_reports(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    domain: Optional[str] = Query(None, description="领域过滤"),
    user: User = Depends(get_current_user),
):
    """
    获取历史报告
    
    需要登录，付费用户可用。
    """
    if not user.is_paid_user:
        raise HTTPException(status_code=403, detail="需要订阅才能查看历史报告")
    
    return engine.get_history_reports(start_date, end_date, domain)
```

---

## 六、订阅管理设计

### 6.1 订阅模型

```python
# insight_hub/users/models.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class SubscriptionPlan(Enum):
    """订阅套餐"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(Enum):
    """订阅状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


@dataclass
class User:
    """用户模型"""
    user_id: str
    email: str
    phone: Optional[str]
    created_at: datetime
    status: str = "active"
    
    @property
    def is_paid_user(self) -> bool:
        """是否为付费用户"""
        return self.subscription and self.subscription.is_active


@dataclass
class Subscription:
    """订阅模型"""
    sub_id: str
    user_id: str
    plan: SubscriptionPlan
    started_at: datetime
    expires_at: datetime
    status: SubscriptionStatus
    
    @property
    def is_active(self) -> bool:
        """是否有效"""
        return (
            self.status == SubscriptionStatus.ACTIVE 
            and self.expires_at > datetime.now()
        )


@dataclass
class UserPreference:
    """用户偏好"""
    user_id: str
    domains: list  # 关注领域
    email_enabled: bool  # 是否接收邮件
    email_frequency: str  # daily/weekly
```

### 6.2 订阅管理器

**文件**: `insight_hub/subscription/manager.py`

```python
"""
订阅管理器
"""

from typing import List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid

from users.models import User, Subscription, SubscriptionPlan, SubscriptionStatus
from storage.database import get_db


class SubscriptionManager:
    """订阅管理器"""
    
    PLAN_PRICES = {
        SubscriptionPlan.FREE: 0,
        SubscriptionPlan.BASIC: 9,
        SubscriptionPlan.PRO: 29,
        SubscriptionPlan.ENTERPRISE: 199,
    }
    
    PLAN_FEATURES = {
        SubscriptionPlan.FREE: {
            "daily_limit": 5,
            "history_access": False,
            "pdf_download": False,
            "custom_report": False,
        },
        SubscriptionPlan.BASIC: {
            "daily_limit": None,
            "history_access": True,
            "pdf_download": True,
            "custom_report": False,
        },
        SubscriptionPlan.PRO: {
            "daily_limit": None,
            "history_access": True,
            "pdf_download": True,
            "custom_report": True,
            "priority_push": True,
        },
        SubscriptionPlan.ENTERPRISE: {
            "daily_limit": None,
            "history_access": True,
            "pdf_download": True,
            "custom_report": True,
            "priority_push": True,
            "api_access": True,
            "dedicated_support": True,
        },
    }
    
    def __init__(self):
        self.db = get_db()
    
    def create_subscription(
        self,
        user_id: str,
        plan: SubscriptionPlan,
        duration_months: int = 1,
    ) -> Subscription:
        """创建订阅"""
        now = datetime.now()
        expires_at = now + timedelta(days=30 * duration_months)
        
        subscription = Subscription(
            sub_id=str(uuid.uuid4()),
            user_id=user_id,
            plan=plan,
            started_at=now,
            expires_at=expires_at,
            status=SubscriptionStatus.ACTIVE,
        )
        
        self.db.save_subscription(subscription)
        
        return subscription
    
    def get_subscription(self, user_id: str) -> Optional[Subscription]:
        """获取用户订阅"""
        return self.db.get_subscription_by_user(user_id)
    
    def cancel_subscription(self, sub_id: str) -> bool:
        """取消订阅"""
        subscription = self.db.get_subscription(sub_id)
        if not subscription:
            return False
        
        subscription.status = SubscriptionStatus.CANCELLED
        self.db.update_subscription(subscription)
        
        return True
    
    def renew_subscription(
        self,
        sub_id: str,
        duration_months: int = 1,
    ) -> Optional[Subscription]:
        """续订"""
        subscription = self.db.get_subscription(sub_id)
        if not subscription:
            return None
        
        subscription.expires_at += timedelta(days=30 * duration_months)
        subscription.status = SubscriptionStatus.ACTIVE
        self.db.update_subscription(subscription)
        
        return subscription
    
    def get_expiring_soon(self, days: int = 7) -> List[Subscription]:
        """获取即将过期的订阅"""
        threshold = datetime.now() + timedelta(days=days)
        return self.db.get_subscriptions_expiring_before(threshold)
    
    def get_plan_features(self, plan: SubscriptionPlan) -> dict:
        """获取套餐功能"""
        return self.PLAN_FEATURES.get(plan, {})
```

### 6.3 邮件服务

**文件**: `insight_hub/subscription/email_service.py`

```python
"""
邮件服务

扩展现有邮件功能，支持订阅管理。
"""

from typing import List, Optional
from datetime import date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from users.models import User, SubscriptionPlan
from core.engine import CommercialEngine


class EmailService:
    """邮件服务"""
    
    def __init__(self, smtp_config: dict):
        self.smtp_host = smtp_config.get("host", "smtp.qq.com")
        self.smtp_port = smtp_config.get("port", 587)
        self.smtp_user = smtp_config.get("user")
        self.smtp_password = smtp_config.get("password")
        self.engine = CommercialEngine()
    
    def send_daily_report(
        self,
        user: User,
        report_date: date,
        is_paid: bool = False,
    ) -> bool:
        """发送每日报告"""
        if is_paid:
            report = self.engine.get_full_report(report_date)
            subject = f"【深度洞察】{report_date} 信息分析报告"
        else:
            report = self.engine.get_brief_report(report_date, limit=5)
            subject = f"【简要洞察】{report_date} 信息摘要"
        
        return self._send_email(
            to=user.email,
            subject=subject,
            body=report,
            is_html=True,
        )
    
    def send_welcome_email(self, user: User) -> bool:
        """发送欢迎邮件"""
        template = self._load_template("welcome.html")
        body = template.format(email=user.email)
        
        return self._send_email(
            to=user.email,
            subject="欢迎订阅 Insight Hub",
            body=body,
            is_html=True,
        )
    
    def send_expiry_reminder(
        self,
        user: User,
        days_left: int,
    ) -> bool:
        """发送过期提醒"""
        template = self._load_template("expiry_reminder.html")
        body = template.format(
            email=user.email,
            days_left=days_left,
        )
        
        return self._send_email(
            to=user.email,
            subject=f"您的订阅即将过期（剩余{days_left}天）",
            body=body,
            is_html=True,
        )
    
    def _send_email(
        self,
        to: str,
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> bool:
        """发送邮件"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = to
            msg["Subject"] = subject
            
            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
    
    def _load_template(self, template_name: str) -> str:
        """加载邮件模板"""
        template_path = Path(__file__).parent / "templates" / template_name
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        return ""
```

---

## 七、数据库设计

### 7.1 表结构

```sql
-- 用户表
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active'  -- active/suspended/deleted
);

-- 订阅表
CREATE TABLE subscriptions (
    sub_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    plan TEXT NOT NULL,  -- free/basic/pro/enterprise
    started_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'active',  -- active/expired/cancelled/pending
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 用户偏好表
CREATE TABLE user_preferences (
    user_id TEXT PRIMARY KEY,
    domains TEXT,  -- JSON数组：关注领域
    email_enabled INTEGER DEFAULT 1,
    email_frequency TEXT DEFAULT 'daily',  -- daily/weekly
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 支付记录表
CREATE TABLE payments (
    payment_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    sub_id TEXT,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'CNY',
    payment_method TEXT,  -- wechat/alipay/other
    status TEXT DEFAULT 'pending',  -- pending/completed/failed/refunded
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (sub_id) REFERENCES subscriptions(sub_id)
);

-- 报告存储表
CREATE TABLE reports (
    report_id TEXT PRIMARY KEY,
    report_date DATE NOT NULL,
    report_type TEXT NOT NULL,  -- brief/depth
    domain TEXT,
    content TEXT NOT NULL,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 合规审核表
CREATE TABLE compliance_reviews (
    review_id TEXT PRIMARY KEY,
    news_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending/approved/rejected
    matched_keywords TEXT,  -- JSON数组
    reviewer TEXT,
    reviewed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_expires ON subscriptions(expires_at);
CREATE INDEX idx_reports_date ON reports(report_date);
CREATE INDEX idx_compliance_status ON compliance_reviews(status);
```

### 7.2 数据库管理器

**文件**: `insight_hub/storage/database.py`

```python
"""
数据库管理器
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass

from users.models import User, Subscription, UserPreference, SubscriptionPlan, SubscriptionStatus


class CommercialDatabase:
    """商业化数据库管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "insight_hub.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self._get_schema())
    
    def _get_schema(self) -> str:
        """获取数据库schema"""
        return """
        -- 用户表
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        );
        
        -- 订阅表
        CREATE TABLE IF NOT EXISTS subscriptions (
            sub_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            plan TEXT NOT NULL,
            started_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        
        -- 用户偏好表
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            domains TEXT,
            email_enabled INTEGER DEFAULT 1,
            email_frequency TEXT DEFAULT 'daily',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        
        -- 支付记录表
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            sub_id TEXT,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'CNY',
            payment_method TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (sub_id) REFERENCES subscriptions(sub_id)
        );
        
        -- 报告存储表
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            report_date DATE NOT NULL,
            report_type TEXT NOT NULL,
            domain TEXT,
            content TEXT NOT NULL,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 合规审核表
        CREATE TABLE IF NOT EXISTS compliance_reviews (
            review_id TEXT PRIMARY KEY,
            news_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            matched_keywords TEXT,
            reviewer TEXT,
            reviewed_at TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 索引
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_expires ON subscriptions(expires_at);
        CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(report_date);
        CREATE INDEX IF NOT EXISTS idx_compliance_status ON compliance_reviews(status);
        """
    
    # 用户相关方法
    def save_user(self, user: User) -> None:
        """保存用户"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO users (user_id, email, phone, password_hash, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user.user_id, user.email, user.phone, user.password_hash, user.created_at, user.status))
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return User(**dict(row))
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row:
                return User(**dict(row))
        return None
    
    # 订阅相关方法
    def save_subscription(self, subscription: Subscription) -> None:
        """保存订阅"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO subscriptions (sub_id, user_id, plan, started_at, expires_at, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (subscription.sub_id, subscription.user_id, subscription.plan.value, 
                  subscription.started_at, subscription.expires_at, subscription.status.value))
    
    def get_subscription(self, sub_id: str) -> Optional[Subscription]:
        """获取订阅"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM subscriptions WHERE sub_id = ?", (sub_id,)).fetchone()
            if row:
                data = dict(row)
                data['plan'] = SubscriptionPlan(data['plan'])
                data['status'] = SubscriptionStatus(data['status'])
                return Subscription(**data)
        return None
    
    def get_subscription_by_user(self, user_id: str) -> Optional[Subscription]:
        """获取用户订阅"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            ).fetchone()
            if row:
                data = dict(row)
                data['plan'] = SubscriptionPlan(data['plan'])
                data['status'] = SubscriptionStatus(data['status'])
                return Subscription(**data)
        return None
    
    # ... 其他方法 ...
```

---

## 八、配置设计

### 8.1 商业化信源配置

**文件**: `insight_hub/config/sources.yaml`

```yaml
# 商业化信源配置
# 仅包含国内合规信源及经济/科技相关的国际信源

domestic:
  central:
    - name: 新华社
      enabled: true
      compliance:
        allowed_domains: ["宏观动态", "经济", "科技", "社会"]
    
    - name: 人民日报
      enabled: true
      compliance:
        allowed_domains: ["宏观动态", "经济", "社会"]
    
    - name: 中国日报
      enabled: true
      compliance:
        allowed_domains: ["经济", "科技", "国际动态"]
    
    - name: 中央广播电视总台
      enabled: true
      compliance:
        allowed_domains: ["宏观动态", "经济", "社会"]
  
  market_professional:
    - name: 财新传媒
      enabled: true
      compliance:
        allowed_domains: ["经济", "社会"]
    
    - name: 第一财经
      enabled: true
      compliance:
        allowed_domains: ["经济"]
    
    - name: 财经杂志
      enabled: true
      compliance:
        allowed_domains: ["经济"]
    
    - name: 界面新闻
      enabled: true
      compliance:
        allowed_domains: ["经济", "科技"]
  
  technology:
    - name: 36氪
      enabled: true
      compliance:
        allowed_domains: ["科技", "经济"]
    
    - name: 钛媒体
      enabled: true
      compliance:
        allowed_domains: ["科技", "经济"]

international:
  finance:
    - name: CNBC
      enabled: true
      compliance:
        allowed_domains: ["经济"]
    
    - name: 日经亚洲
      enabled: true
      compliance:
        allowed_domains: ["经济", "科技"]
  
  technology:
    - name: TechCrunch
      enabled: true
      compliance:
        allowed_domains: ["科技"]
    
    - name: The Verge
      enabled: true
      compliance:
        allowed_domains: ["科技"]

# 禁用的信源
blocked:
  - name: 路透社
    reason: "政治敏感"
  
  - name: BBC News
    reason: "政治敏感"
  
  - name: 纽约时报
    reason: "政治敏感"
  
  # ... 更多禁用信源 ...
```

### 8.2 合规配置

**文件**: `insight_hub/config/compliance.yaml`

```yaml
# 合规配置

# 领域映射
domain_mapping:
  "政治": "宏观动态"
  "时政": "公共事务"
  "国际政治": "国际动态"

# 敏感词库路径
keywords_path: "compliance/keywords.yaml"

# 自动降级规则
auto_downgrade:
  # 命中以下领域时自动跳过分析
  skip_analysis_domains:
    - "政治"
    - "时政"
  
  # 命中以下关键词时自动跳过分析
  skip_analysis_keywords:
    - "政治改革"
    - "民主运动"

# 输出控制
output_control:
  # 是否移除原文内容
  remove_original_content: true
  
  # 原文预览长度
  content_preview_length: 200
  
  # 是否显示参考来源
  show_source_link: true
  
  # 参考来源显示方式
  source_link_style: "small"  # small/normal/hidden

# 免责声明
disclaimer:
  enabled: true
  text: "本产品为AI分析工具，内容仅供参考，不构成任何投资或决策建议。"
```

### 8.3 订阅配置

**文件**: `insight_hub/config/subscription.yaml`

```yaml
# 订阅配置

# 套餐定义
plans:
  free:
    name: "免费版"
    price: 0
    duration_days: null
    features:
      daily_limit: 5
      history_access: false
      pdf_download: false
      custom_report: false
  
  basic:
    name: "基础版"
    price: 9
    duration_days: 30
    features:
      daily_limit: null
      history_access: true
      pdf_download: true
      custom_report: false
  
  pro:
    name: "专业版"
    price: 29
    duration_days: 30
    features:
      daily_limit: null
      history_access: true
      pdf_download: true
      custom_report: true
      priority_push: true
      custom_report_monthly: 1
  
  enterprise:
    name: "企业版"
    price: 199
    duration_days: 30
    features:
      daily_limit: null
      history_access: true
      pdf_download: true
      custom_report: true
      priority_push: true
      api_access: true
      dedicated_support: true

# 邮件配置
email:
  daily_send_time: "08:00"
  weekly_send_day: "monday"
  weekly_send_time: "09:00"
  
  # 过期提醒
  expiry_reminder_days: [7, 3, 1]

# 支付配置
payment:
  methods:
    - wechat
    - alipay
  
  # 第三方平台（初期）
  third_party:
    - name: "爱发电"
      url: "https://afdian.net"
    - name: "面包多"
      url: "https://mianbaoduo.com"
```

---

## 九、部署设计

### 9.1 部署架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              部署架构                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│   FastAPI   │────▶│   SQLite    │
│  (反向代理)  │     │   (API)     │     │  (数据库)   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           │ 引用
                           ▼
                    ┌─────────────┐
                    │news_analyzer│
                    │ (核心引擎)   │
                    └─────────────┘
```

### 9.2 Docker部署

**文件**: `insight_hub/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装核心引擎
COPY news_analyzer /app/news_analyzer
RUN pip install /app/news_analyzer

# 复制商业化项目
COPY insight_hub /app/insight_hub
WORKDIR /app/insight_hub

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**文件**: `insight_hub/docker-compose.yml`

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/insight_hub/data
      - ./config:/app/insight_hub/config
    environment:
      - DATABASE_URL=sqlite:///data/insight_hub.db
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
    restart: unless-stopped
  
  scheduler:
    build: .
    command: python scheduler/run.py
    volumes:
      - ./data:/app/insight_hub/data
      - ./config:/app/insight_hub/config
    environment:
      - DATABASE_URL=sqlite:///data/insight_hub.db
    restart: unless-stopped
```

### 9.3 GitHub Actions部署

**文件**: `insight_hub/.github/workflows/deploy.yml`

```yaml
name: Deploy Insight Hub

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 23 * * *'  # 每天7点(北京时间)采集

jobs:
  collect-and-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e ./news_analyzer
          pip install -r insight_hub/requirements.txt
      
      - name: Run collection
        env:
          AI_ANALYSIS_KEY: ${{ secrets.AI_ANALYSIS_KEY }}
          AI_FILTER_KEY: ${{ secrets.AI_FILTER_KEY }}
        run: |
          cd insight_hub
          python -m core.run_pipeline
      
      - name: Send reports
        env:
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
        run: |
          cd insight_hub
          python -m subscription.send_reports
```

---

## 十、总结

本技术设计文档详细描述了商业化项目的架构设计、核心引擎改造、合规模块设计、API层设计、订阅管理设计、数据库设计和配置设计。

关键设计决策：

1. **混合架构**：核心引擎与商业化包装层分离，实现职责分离和风险隔离
2. **五层防护**：源头过滤、内容过滤、AI分析约束、输出过滤、报告重构
3. **配置驱动**：行为差异通过配置控制，而非代码分支
4. **渐进式实施**：分阶段实施，每阶段可独立验证

下一步：根据本文档生成具体的代码改造清单和实施计划。
