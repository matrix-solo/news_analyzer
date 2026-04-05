# MVP技术设计文档

**项目名称**: Insight Hub - 智能信息洞察平台  
**版本**: 1.0.0  
**日期**: 2026-03-13  
**状态**: 草案

---

## 目录

1. [设计原则](#一设计原则)
2. [架构设计](#二架构设计)
3. [合规模块设计](#三合规模块设计)
4. [订阅模块设计](#四订阅模块设计)
5. [数据设计](#五数据设计)
6. [部署设计](#六部署设计)

---

## 一、设计原则

### 1.1 核心原则

| 原则 | 说明 | 实践 |
|------|------|------|
| **MVP优先** | 最小可行产品，验证付费意愿 | 仅实现核心功能 |
| **YAGNI** | 不做暂时不需要的功能 | 无API、无前端、无用户系统 |
| **复用优先** | 复用现有代码，最小改动 | 仅新增合规过滤，复用报告生成 |
| **配置驱动** | 行为差异通过配置控制 | 信源配置、敏感词配置 |

### 1.2 设计约束

| 约束 | 说明 |
|------|------|
| 时间约束 | MVP在1周内完成 |
| 成本约束 | 月运营成本 < 50元 |
| 人力约束 | 个人开发者，兼职开发 |
| 合规约束 | 必须符合法规要求 |

### 1.3 不做的事

| 功能 | 原因 | 计划 |
|------|------|------|
| 用户系统 | MVP不需要 | Phase 2 |
| API服务 | MVP不需要 | Phase 3 |
| Web前端 | MVP仅邮件交付 | Phase 3 |
| 自动支付 | 手动收款即可 | Phase 2 |
| 数据库 | 文件存储足够 | Phase 2 |

---

## 二、架构设计

### 2.1 MVP架构

```
┌─────────────────────────────────────────────────────────────┐
│                      MVP架构（极简）                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  RSS采集    │────▶│  合规过滤   │────▶│  报告生成   │
│ (现有)      │     │ (新增)      │     │ (现有)      │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  邮件发送   │
                                        │ (现有)      │
                                        └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  用户邮箱   │
                                        │ (文件存储)  │
                                        └─────────────┘

外部服务：
┌─────────────┐     ┌─────────────┐
│  爱发电     │     │  面包多     │
│ (付费入口)  │     │ (付费入口)  │
└─────────────┘     └─────────────┘
```

### 2.2 与原架构对比

| 维度 | 原架构 | MVP架构 |
|------|--------|---------|
| 新增模块 | - | 合规过滤 |
| 修改模块 | - | 信源配置、报告生成 |
| 新增文件 | - | 3个文件 |
| 代码改动量 | - | 约200行 |

### 2.3 数据流

```
RSS采集
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 合规过滤层（新增）                                           │
│                                                              │
│ 1. 信源过滤：仅保留国内合规信源                               │
│ 2. 敏感词检测：过滤政治敏感内容                               │
│ 3. 领域映射：政治 → 宏观动态                                 │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
AI分析（现有）
    │
    ▼
报告生成（现有 + 小修改）
    │
    ▼
邮件发送（现有）
```

---

## 三、合规模块设计

### 3.1 模块结构

```
news_analyzer/
├── compliance/               # 新增目录
│   ├── __init__.py
│   ├── source_filter.py      # 信源过滤
│   ├── content_filter.py     # 内容过滤
│   └── keywords.yaml         # 敏感词库
└── config/
    └── sources_commercial.yaml  # 商业化信源配置
```

### 3.2 信源过滤

**文件**: `compliance/source_filter.py`

```python
"""
信源过滤器

功能：
- 仅保留国内合规信源
- 过滤国外信源
"""

from typing import Dict, List, Optional, Set
import yaml
from pathlib import Path


class SourceFilter:
    """信源过滤器"""
    
    ALLOWED_SOURCES: Set[str] = {
        "新华社", "人民日报", "中国日报", "中央广播电视总台",
        "财新传媒", "第一财经", "财经杂志", "界面新闻",
        "36氪", "钛媒体", "虎嗅",
    }
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> None:
        """加载信源配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        allowed = set()
        for category, sources in config.get("domestic", {}).items():
            if isinstance(sources, dict):
                for sub_cat, source_list in sources.items():
                    for source in source_list:
                        if source.get("enabled", True):
                            allowed.add(source.get("name"))
            elif isinstance(sources, list):
                for source in sources:
                    if source.get("enabled", True):
                        allowed.add(source.get("name"))
        
        if allowed:
            self.ALLOWED_SOURCES = allowed
    
    def is_allowed(self, source_name: str) -> bool:
        """检查信源是否被允许"""
        return source_name in self.ALLOWED_SOURCES
    
    def filter(self, news_list: List[Dict]) -> List[Dict]:
        """过滤新闻列表"""
        return [n for n in news_list if self.is_allowed(n.get("source_name", ""))]
```

### 3.3 内容过滤

**文件**: `compliance/content_filter.py`

```python
"""
内容过滤器

功能：
- 敏感词检测
- 领域映射
"""

from typing import Dict, List, Optional, Set
import yaml
from pathlib import Path


class ContentFilter:
    """内容过滤器"""
    
    DOMAIN_MAPPING = {
        "政治": "宏观动态",
        "时政": "公共事务",
    }
    
    def __init__(self, keywords_path: Optional[str] = None):
        self.blocked_keywords: Set[str] = set()
        
        if keywords_path:
            self.load_keywords(keywords_path)
    
    def load_keywords(self, keywords_path: str) -> None:
        """加载敏感词库"""
        with open(keywords_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        blocked = config.get("blocked", [])
        self.blocked_keywords = set(blocked)
    
    def contains_blocked_keyword(self, text: str) -> bool:
        """检查是否包含敏感词"""
        if not text:
            return False
        return any(kw in text for kw in self.blocked_keywords)
    
    def map_domain(self, domain: str) -> str:
        """领域映射"""
        return self.DOMAIN_MAPPING.get(domain, domain)
    
    def filter(self, news: Dict) -> Optional[Dict]:
        """过滤新闻"""
        title = news.get("title", "")
        summary = news.get("summary", "")
        content = news.get("content", "")
        
        if self.contains_blocked_keyword(f"{title} {summary} {content}"):
            return None
        
        if "domain" in news:
            news["domain"] = self.map_domain(news["domain"])
        
        return news
    
    def filter_list(self, news_list: List[Dict]) -> List[Dict]:
        """过滤新闻列表"""
        result = []
        for news in news_list:
            filtered = self.filter(news)
            if filtered:
                result.append(filtered)
        return result
```

### 3.4 敏感词库

**文件**: `compliance/keywords.yaml`

```yaml
# 敏感词库
# 包含需要过滤的关键词

blocked:
  - "台独"
  - "藏独"
  - "疆独"
  - "法轮功"
  - "六四"
  - "天安门事件"
  - "暴力"
  - "恐怖主义"
  - "邪教"
```

### 3.5 信源配置

**文件**: `config/sources_commercial.yaml`

```yaml
# 商业化信源配置
# 仅包含国内合规信源

domestic:
  central:
    - name: 新华社
      enabled: true
    - name: 人民日报
      enabled: true
    - name: 中国日报
      enabled: true
    - name: 中央广播电视总台
      enabled: true
  
  market_professional:
    - name: 财新传媒
      enabled: true
    - name: 第一财经
      enabled: true
    - name: 财经杂志
      enabled: true
    - name: 界面新闻
      enabled: true
  
  technology:
    - name: 36氪
      enabled: true
    - name: 钛媒体
      enabled: true
    - name: 虎嗅
      enabled: true
```

---

## 四、订阅模块设计

### 4.1 订阅流程

```
用户发现 → 提交邮箱 → 收到免费报告 → 付费 → 收到深度报告
    │           │             │           │           │
    ▼           ▼             ▼           ▼           ▼
 社区推广    静态页面      自动发送    爱发电链接   手动开通
```

### 4.2 邮箱收集

**方式**：静态HTML页面 + 邮件列表文件

**文件**: `subscription/index.html`（可选，也可用第三方表单）

```html
<!DOCTYPE html>
<html>
<head>
    <title>Insight Hub - 智能信息洞察</title>
</head>
<body>
    <h1>Insight Hub</h1>
    <p>每日精选信息洞察，助你快速了解重要事件</p>
    
    <form action="mailto:your@email.com" method="post">
        <input type="email" name="email" placeholder="输入您的邮箱" required>
        <button type="submit">订阅</button>
    </form>
    
    <p>免费版：每日简要洞察（5条）</p>
    <p>付费版：深度分析 + 历史查询（9元/月）</p>
    
    <a href="https://afdian.net/your-link">付费订阅</a>
</body>
</html>
```

### 4.3 邮箱存储

**方式**：简单文本文件

**文件**: `data/subscribers.txt`

```
# 格式：邮箱,订阅类型,订阅日期
user1@example.com,free,2026-03-13
user2@example.com,paid,2026-03-14
```

### 4.4 付费流程

```
用户点击付费链接 → 爱发电/面包多付款 → 手动确认 → 开通权限
                                          │
                                          ▼
                                   更新subscribers.txt
                                   paid: true
```

---

## 五、数据设计

### 5.1 MVP数据存储

| 数据类型 | 存储方式 | 文件 |
|----------|----------|------|
| 用户邮箱 | 文本文件 | `data/subscribers.txt` |
| 付费状态 | 文本文件 | `data/subscribers.txt` |
| 报告文件 | Markdown/PDF | `reports/` |
| 敏感词库 | YAML | `compliance/keywords.yaml` |
| 信源配置 | YAML | `config/sources_commercial.yaml` |

### 5.2 数据格式

#### subscribers.txt

```
# 邮箱,类型,日期,付费到期日
user1@example.com,free,2026-03-13,
user2@example.com,paid,2026-03-14,2026-04-14
```

### 5.3 数据迁移计划

MVP验证成功后，Phase 2 迁移到数据库：

| 阶段 | 存储方式 | 说明 |
|------|----------|------|
| MVP | 文本文件 | 简单、够用 |
| Phase 2 | SQLite | 支持查询、统计 |
| Phase 3 | PostgreSQL | 支持高并发 |

---

## 六、部署设计

### 6.1 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    MVP部署架构                               │
└─────────────────────────────────────────────────────────────┘

GitHub Actions（定时任务）
    │
    ├── 每日7:00触发
    │
    ▼
┌─────────────┐
│ 采集+过滤   │
│ +报告生成   │
└─────────────┘
    │
    ▼
┌─────────────┐
│ 邮件发送    │
│ (SMTP)      │
└─────────────┘
    │
    ▼
用户邮箱

外部服务：
├── 爱发电（付费入口）
└── 静态页面（订阅入口，可选）
```

### 6.2 GitHub Actions配置

**文件**: `.github/workflows/mvp_daily.yml`

```yaml
name: MVP Daily Report

on:
  schedule:
    - cron: '0 23 * * *'  # 每日7:00(北京时间)
  workflow_dispatch:

jobs:
  daily-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run pipeline
        env:
          AI_ANALYSIS_KEY: ${{ secrets.AI_ANALYSIS_KEY }}
          AI_FILTER_KEY: ${{ secrets.AI_FILTER_KEY }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
        run: |
          python scripts/run_mvp_pipeline.py
      
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: daily-reports
          path: reports/
```

### 6.3 运行脚本

**文件**: `scripts/run_mvp_pipeline.py`

```python
"""
MVP流水线运行脚本

功能：
1. 采集新闻（仅国内信源）
2. 合规过滤
3. 生成报告
4. 发送邮件
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rss.collector import RSSCollector
from compliance.source_filter import SourceFilter
from compliance.content_filter import ContentFilter
from generators.report_generator import ReportGenerator
from utils.email_sender import EmailSender


def run_mvp_pipeline():
    """运行MVP流水线"""
    
    # 1. 采集新闻
    print("Step 1: 采集新闻...")
    collector = RSSCollector()
    news_list = collector.collect_all()
    print(f"  采集到 {len(news_list)} 条新闻")
    
    # 2. 信源过滤
    print("Step 2: 信源过滤...")
    source_filter = SourceFilter("config/sources_commercial.yaml")
    news_list = source_filter.filter(news_list)
    print(f"  过滤后剩余 {len(news_list)} 条新闻")
    
    # 3. 内容过滤
    print("Step 3: 内容过滤...")
    content_filter = ContentFilter("compliance/keywords.yaml")
    news_list = content_filter.filter_list(news_list)
    print(f"  过滤后剩余 {len(news_list)} 条新闻")
    
    # 4. 生成报告
    print("Step 4: 生成报告...")
    generator = ReportGenerator()
    report_path = generator.generate_brief_report(news_list)
    print(f"  报告已生成: {report_path}")
    
    # 5. 发送邮件
    print("Step 5: 发送邮件...")
    sender = EmailSender()
    
    subscribers = load_subscribers("data/subscribers.txt")
    
    for email, sub_type in subscribers:
        if sub_type == "paid":
            sender.send_full_report(email, report_path)
        else:
            sender.send_brief_report(email, report_path)
    
    print(f"  已发送 {len(subscribers)} 封邮件")
    print("完成!")


def load_subscribers(file_path: str) -> list:
    """加载订阅者列表"""
    subscribers = []
    path = Path(file_path)
    
    if not path.exists():
        return subscribers
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split(',')
            if len(parts) >= 2:
                email = parts[0]
                sub_type = parts[1]
                subscribers.append((email, sub_type))
    
    return subscribers


if __name__ == "__main__":
    run_mvp_pipeline()
```

---

## 七、修改清单

### 7.1 新增文件

| 文件 | 说明 | 代码量 |
|------|------|--------|
| `compliance/__init__.py` | 模块入口 | 5行 |
| `compliance/source_filter.py` | 信源过滤 | 50行 |
| `compliance/content_filter.py` | 内容过滤 | 60行 |
| `compliance/keywords.yaml` | 敏感词库 | 20行 |
| `config/sources_commercial.yaml` | 信源配置 | 50行 |
| `scripts/run_mvp_pipeline.py` | 运行脚本 | 80行 |

**总计**：约265行代码

### 7.2 修改文件

| 文件 | 修改点 | 代码量 |
|------|--------|--------|
| `generators/report_generator.py` | 添加免责声明、弱化原文链接 | 10行 |

**总计**：约10行代码

### 7.3 总改动量

**约275行代码**，相比原设计（约2000行）减少86%。

---

## 八、总结

本技术设计遵循MVP原则，实现了：

1. **极简架构**：仅新增合规过滤模块，复用现有功能
2. **最小改动**：约275行代码，1周内可完成
3. **配置驱动**：信源和敏感词通过配置文件控制
4. **快速验证**：支持邮件订阅付费意愿验证

**下一步**：根据本设计输出MVP实施计划。
