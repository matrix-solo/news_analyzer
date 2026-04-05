#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型定义
使用dataclass定义结构化的数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class NewsItem:
    """新闻条目模型"""
    title: str
    date: str
    official_source: str
    official_url: Optional[str] = None
    official_content: Optional[str] = None
    domain: str = "general"
    summary: Optional[str] = None
    report_path: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    pub_date: Optional[datetime] = None
    
    tags: List[str] = field(default_factory=list)
    third_party_contents: List['ThirdPartyContent'] = field(default_factory=list)
    
    is_official: bool = True
    report_markdown: Optional[str] = None
    core_tags: List[str] = field(default_factory=list)
    conclusion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'date': self.date,
            'domain': self.domain,
            'official_source': self.official_source,
            'official_url': self.official_url,
            'official_content': self.official_content,
            'summary': self.summary,
            'report_path': self.report_path,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'pub_date': self.pub_date.isoformat() if self.pub_date else None,
            'tags': self.tags,
            'is_official': self.is_official,
            'core_tags': self.core_tags,
            'conclusion': self.conclusion,
            'third_party_contents': [tpc.to_dict() for tpc in self.third_party_contents]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NewsItem':
        """从字典创建"""
        pub_date = None
        if data.get('pub_date'):
            try:
                pub_date = datetime.fromisoformat(data['pub_date'])
            except (ValueError, TypeError):
                pass
        
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            date=data.get('date', ''),
            domain=data.get('domain', 'general'),
            official_source=data.get('official_source', ''),
            official_url=data.get('official_url'),
            official_content=data.get('official_content'),
            summary=data.get('summary'),
            report_path=data.get('report_path'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            pub_date=pub_date,
            is_official=data.get('is_official', True),
            core_tags=data.get('core_tags', []),
            conclusion=data.get('conclusion')
        )


@dataclass
class ThirdPartyContent:
    """第三方内容模型"""
    source: str
    news_id: Optional[int] = None
    title: Optional[str] = None
    url: Optional[str] = None
    content: Optional[str] = None
    added_value: Optional[str] = None
    similarity_score: float = 0.0
    id: Optional[int] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'news_id': self.news_id,
            'source': self.source,
            'title': self.title,
            'url': self.url,
            'content': self.content,
            'added_value': self.added_value,
            'similarity_score': self.similarity_score,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThirdPartyContent':
        """从字典创建"""
        return cls(
            id=data.get('id'),
            news_id=data.get('news_id'),
            source=data.get('source', ''),
            title=data.get('title'),
            url=data.get('url'),
            content=data.get('content'),
            added_value=data.get('added_value'),
            similarity_score=data.get('similarity_score', 0.0),
            created_at=data.get('created_at')
        )


@dataclass
class Tag:
    """标签模型"""
    name: str
    category: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'created_at': self.created_at
        }


@dataclass
class Event:
    """事件追踪模型"""
    name: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = "ongoing"
    id: Optional[int] = None
    created_at: Optional[str] = None
    
    # 关联的新闻ID列表
    news_ids: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'status': self.status,
            'created_at': self.created_at,
            'news_ids': self.news_ids
        }


@dataclass
class NewsReport:
    """新闻报告模型"""
    title: str
    date: str
    domain: str
    core_tags: List[str]
    official_content: str
    official_source: str
    official_url: Optional[str] = None
    third_party_contents: List[Dict[str, Any]] = field(default_factory=list)
    conclusion: Optional[str] = None
    
    def to_markdown(self) -> str:
        """生成Markdown格式报告"""
        lines = []
        
        # 标题
        lines.append(f"# 【{self.date} {self.domain}】{self.title}")
        lines.append("")
        
        # 核心标签
        if self.core_tags:
            tags_str = " ".join([f"`{tag}`" for tag in self.core_tags])
            lines.append(f"## 核心标签")
            lines.append(tags_str)
            lines.append("")
        
        # 官媒核心内容
        lines.append(f"## 官媒核心内容")
        lines.append("")
        lines.append(f"**{self.official_source}报道**：")
        lines.append("")
        lines.append(self.official_content)
        lines.append("")
        if self.official_url:
            lines.append(f"*原文链接：[{self.official_source}]({self.official_url})*")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 第三方补充视角
        if self.third_party_contents:
            lines.append(f"## 第三方补充视角")
            lines.append("")
            for i, tpc in enumerate(self.third_party_contents, 1):
                lines.append(f"*{i}. **{tpc.get('source', '未知来源')}报道**：*")
                if tpc.get('content'):
                    content = tpc.get('content')
                    if len(content) > 500:
                        content = content[:500] + "..."
                    lines.append(f"> {content}")
                lines.append("")
                lines.append(f"- **来源**：{tpc.get('source', '未知')}")
                if tpc.get('added_value'):
                    lines.append(f"- **新增信息**：{tpc.get('added_value')}")
                if tpc.get('url'):
                    lines.append(f"- *原文链接：[{tpc.get('source')}]({tpc.get('url')})*")
                lines.append("")
        
        # 整合结论
        if self.conclusion:
            lines.append("---")
            lines.append("")
            lines.append(f"## 整合结论")
            lines.append("")
            lines.append(self.conclusion)
        
        return "\n".join(lines)


@dataclass
class CrawlerResult:
    """爬虫结果模型"""
    source: str
    source_type: str  # 'official' 或 'third_party'
    category: str  # 'domestic' 或 'international'
    success: bool
    news_count: int = 0
    news_items: List[NewsItem] = field(default_factory=list)
    error_message: Optional[str] = None
    crawl_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'source': self.source,
            'source_type': self.source_type,
            'category': self.category,
            'success': self.success,
            'news_count': self.news_count,
            'news_items': [item.to_dict() for item in self.news_items],
            'error_message': self.error_message,
            'crawl_time': self.crawl_time
        }


@dataclass
class AIAnalysisResult:
    """AI分析结果模型"""
    news_id: int
    analysis_type: str  # 'value_judgment' 或 'report_generation'
    success: bool
    result: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    added_value: Optional[str] = None
    should_keep: bool = True  # 用于价值判断，是否保留
    error_message: Optional[str] = None
    analysis_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'news_id': self.news_id,
            'analysis_type': self.analysis_type,
            'success': self.success,
            'result': self.result,
            'tags': self.tags,
            'added_value': self.added_value,
            'should_keep': self.should_keep,
            'error_message': self.error_message,
            'analysis_time': self.analysis_time
        }


# 领域定义（统一为8类）
DOMAINS = {
    'politics': '政治',
    'economy': '经济',
    'technology': '科技',
    'military': '军事',
    'society': '社会',
    'culture': '文化',
    'sports': '体育',
    'entertainment': '娱乐'
}

# 新闻来源类型
SOURCE_TYPES = {
    'official': '官媒',
    'third_party': '第三方'
}

# 新闻分类
CATEGORIES = {
    'domestic': '国内',
    'international': '国际'
}
