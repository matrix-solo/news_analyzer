#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻基准库
用于存储历史新闻，支持相似度匹配和事件追踪
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class BaselineNews:
    """基准新闻条目"""
    id: str
    title: str
    content: str
    source: str
    date: str
    url: str
    domain: str = "general"
    event_id: Optional[str] = None
    created_at: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BaselineNews':
        return cls(**data)


class NewsBaseline:
    """新闻基准库"""
    
    SIMILARITY_THRESHOLD = 0.45
    MAX_BASELINE_DAYS = 30
    
    def __init__(self, storage_dir: str = None):
        self.logger = logging.getLogger("NewsBaseline")
        
        if storage_dir is None:
            project_root = Path(__file__).parent.parent
            storage_dir = project_root / "data" / "baseline"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.baseline_file = self.storage_dir / "baseline_news.json"
        self.events_file = self.storage_dir / "events.json"
        
        self.news_list: List[BaselineNews] = []
        self.events: Dict[str, Dict] = {}
        
        self._load()
    
    def _generate_id(self, title: str, source: str, date: str) -> str:
        """生成唯一ID"""
        content = f"{title}_{source}_{date}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
    
    def _load(self):
        """加载基准库"""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.news_list = [BaselineNews.from_dict(item) for item in data.get('news', [])]
                self.logger.info(f"加载基准库: {len(self.news_list)} 条新闻")
            except Exception as e:
                self.logger.error(f"加载基准库失败: {e}")
        
        if self.events_file.exists():
            try:
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    self.events = json.load(f)
                self.logger.info(f"加载事件库: {len(self.events)} 个事件")
            except Exception as e:
                self.logger.error(f"加载事件库失败: {e}")
    
    def _save(self):
        """保存基准库"""
        try:
            data = {
                'updated_at': datetime.now().isoformat(),
                'count': len(self.news_list),
                'news': [n.to_dict() for n in self.news_list]
            }
            with open(self.baseline_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"保存基准库: {len(self.news_list)} 条新闻")
        except Exception as e:
            self.logger.error(f"保存基准库失败: {e}")
    
    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """计算标题相似度（支持中英文）"""
        if not title1 or not title2:
            return 0.0
        
        title1 = title1.lower()
        title2 = title2.lower()
        
        chars1 = set(title1)
        chars2 = set(title2)
        
        intersection = chars1 & chars2
        union = chars1 | chars2
        
        char_sim = len(intersection) / len(union) if union else 0.0
        
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if words1 and words2:
            word_intersection = words1 & words2
            word_union = words1 | words2
            word_sim = len(word_intersection) / len(word_union) if word_union else 0.0
        else:
            word_sim = 0.0
        
        return char_sim * 0.7 + word_sim * 0.3
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """计算内容相似度（支持中英文）"""
        if not content1 or not content2:
            return 0.0
        
        content1 = content1.lower()[:500]
        content2 = content2.lower()[:500]
        
        chars1 = set(content1)
        chars2 = set(content2)
        
        intersection = chars1 & chars2
        union = chars1 | chars2
        
        return len(intersection) / len(union) if union else 0.0
    
    def add_news(self, title: str, content: str, source: str, 
                 date: str, url: str, domain: str = "general") -> Tuple[str, bool]:
        """
        添加新闻到基准库
        
        Returns:
            (news_id, is_new_event) - 新闻ID和是否是新事件
        """
        news_id = self._generate_id(title, source, date)
        
        for existing in self.news_list:
            if existing.id == news_id:
                return news_id, False
        
        event_id = None
        is_new_event = True
        
        for existing in self.news_list:
            title_sim = self._calculate_similarity(title, existing.title)
            content_sim = self._calculate_content_similarity(
                content[:500] if content else "", 
                existing.content[:500] if existing.content else ""
            )
            
            combined_sim = title_sim * 0.6 + content_sim * 0.4
            
            if combined_sim >= self.SIMILARITY_THRESHOLD:
                event_id = existing.event_id
                is_new_event = False
                self.logger.info(f"发现相似新闻: '{title[:30]}...' -> 事件 {event_id}")
                break
        
        if is_new_event:
            event_id = f"evt_{datetime.now().strftime('%Y%m%d')}_{len(self.events) + 1}"
            self.events[event_id] = {
                'id': event_id,
                'first_seen': date,
                'first_source': source,
                'title': title,
                'news_count': 0,
                'sources': []
            }
        
        news = BaselineNews(
            id=news_id,
            title=title,
            content=content or "",
            source=source,
            date=date,
            url=url,
            domain=domain,
            event_id=event_id,
            created_at=datetime.now().isoformat()
        )
        
        self.news_list.append(news)
        
        if event_id and event_id in self.events:
            self.events[event_id]['news_count'] += 1
            if source not in self.events[event_id]['sources']:
                self.events[event_id]['sources'].append(source)
        
        self._save()
        
        return news_id, is_new_event
    
    def find_similar(self, title: str, content: str = "", 
                     threshold: float = None) -> List[Tuple[BaselineNews, float]]:
        """查找相似新闻"""
        threshold = threshold or self.SIMILARITY_THRESHOLD
        results = []
        
        for news in self.news_list:
            title_sim = self._calculate_similarity(title, news.title)
            
            if content and news.content:
                content_sim = self._calculate_content_similarity(content[:500], news.content[:500])
                combined_sim = title_sim * 0.6 + content_sim * 0.4
            else:
                combined_sim = title_sim
            
            if combined_sim >= threshold:
                results.append((news, combined_sim))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def get_event_news(self, event_id: str) -> List[BaselineNews]:
        """获取同一事件的所有新闻"""
        return [n for n in self.news_list if n.event_id == event_id]
    
    def get_recent_news(self, days: int = 7) -> List[BaselineNews]:
        """获取最近N天的新闻"""
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.strftime('%Y-%m-%d')
        
        return [n for n in self.news_list if n.date >= cutoff_str]
    
    def cleanup_old(self, days: int = None) -> int:
        """清理过期新闻"""
        days = days or self.MAX_BASELINE_DAYS
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.strftime('%Y-%m-%d')
        
        old_count = len(self.news_list)
        self.news_list = [n for n in self.news_list if n.date >= cutoff_str]
        new_count = len(self.news_list)
        
        removed = old_count - new_count
        if removed > 0:
            self.logger.info(f"清理过期新闻: {removed} 条")
            self._save()
        
        return removed
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        sources = {}
        domains = {}
        dates = {}
        
        for news in self.news_list:
            sources[news.source] = sources.get(news.source, 0) + 1
            domains[news.domain] = domains.get(news.domain, 0) + 1
            dates[news.date] = dates.get(news.date, 0) + 1
        
        return {
            'total_news': len(self.news_list),
            'total_events': len(self.events),
            'by_source': sources,
            'by_domain': domains,
            'by_date': sorted(dates.items(), reverse=True)[:7]
        }


_baseline_instance = None

def get_baseline() -> NewsBaseline:
    """获取基准库单例"""
    global _baseline_instance
    if _baseline_instance is None:
        _baseline_instance = NewsBaseline()
    return _baseline_instance
