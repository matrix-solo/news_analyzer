#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冗余去重器
第四步：避免重复内容，减少分析冗余
"""

import logging
import re
import sys
import hashlib
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.filters.source_validator import SourceValidator


@dataclass
class DedupResult:
    """去重结果"""
    is_duplicate: bool
    duplicate_of: str = ""
    kept_source: str = ""
    reason: str = ""


class DeduplicationFilter:
    """冗余去重器 - 第四步"""
    
    CONTENT_SIMILARITY_THRESHOLD = 0.8
    
    def __init__(self, source_validator: SourceValidator = None):
        self.logger = logging.getLogger("DeduplicationFilter")
        self.source_validator = source_validator or SourceValidator()
        
        self.seen_events: Dict[str, Dict] = {}
        self.seen_hashes: Set[str] = set()
        self.seen_titles: Dict[str, str] = {}
    
    def check_duplicate(
        self,
        title: str,
        content: str,
        source_name: str,
        event_keywords: List[str] = None
    ) -> DedupResult:
        """
        检查是否为重复内容
        
        Args:
            title: 新闻标题
            content: 新闻正文
            source_name: 信源名称
            event_keywords: 核心事件关键词
        
        Returns:
            DedupResult: 去重结果
        """
        title_normalized = self._normalize_title(title)
        
        if title_normalized in self.seen_titles:
            existing_source = self.seen_titles[title_normalized]
            kept_source = self._select_authority_source(existing_source, source_name)
            
            if kept_source == existing_source:
                return DedupResult(
                    is_duplicate=True,
                    duplicate_of=existing_source,
                    kept_source=existing_source,
                    reason="标题完全重复，保留高优先级信源"
                )
            else:
                self.seen_titles[title_normalized] = source_name
                return DedupResult(
                    is_duplicate=False,
                    reason="标题重复但当前信源优先级更高"
                )
        
        content_hash = self._generate_content_hash(title, content[:500])
        if content_hash in self.seen_hashes:
            return DedupResult(
                is_duplicate=True,
                duplicate_of="unknown",
                kept_source="",
                reason="内容哈希重复"
            )
        
        event_id = self._generate_event_id(title, event_keywords)
        if event_id and event_id in self.seen_events:
            existing = self.seen_events[event_id]
            
            similarity = self._calculate_similarity(content[:300], existing['content'][:300])
            
            if similarity >= self.CONTENT_SIMILARITY_THRESHOLD:
                kept_source = self._select_authority_source(existing['source'], source_name)
                
                if kept_source == existing['source']:
                    return DedupResult(
                        is_duplicate=True,
                        duplicate_of=existing['source'],
                        kept_source=existing['source'],
                        reason=f"事件重复，内容相似度{similarity:.0%}"
                    )
                else:
                    self.seen_events[event_id] = {
                        'source': source_name,
                        'content': content,
                        'title': title
                    }
                    return DedupResult(
                        is_duplicate=False,
                        reason="事件重复但当前信源优先级更高"
                    )
        
        self.seen_titles[title_normalized] = source_name
        self.seen_hashes.add(content_hash)
        if event_id:
            self.seen_events[event_id] = {
                'source': source_name,
                'content': content,
                'title': title
            }
        
        return DedupResult(is_duplicate=False)
    
    def _normalize_title(self, title: str) -> str:
        """标准化标题（去除标点和空格）"""
        normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', title)
        return normalized.lower()
    
    def _generate_content_hash(self, title: str, content: str) -> str:
        """生成内容哈希"""
        combined = f"{title}_{content}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def _generate_event_id(self, title: str, keywords: List[str] = None) -> Optional[str]:
        """生成事件ID"""
        if keywords and len(keywords) >= 3:
            return "_".join(sorted(keywords[:3]))
        
        title_keywords = self._extract_keywords(title)
        if len(title_keywords) >= 3:
            return "_".join(sorted(title_keywords[:3]))
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        stop_words = {'的', '了', '在', '是', '有', '和', '与', '或', '等', '对', '为', '以'}
        
        words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        
        keywords = [w for w in words if w not in stop_words]
        
        return list(set(keywords))
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _select_authority_source(self, source1: str, source2: str) -> str:
        """选择权威优先级更高的信源"""
        priority1 = self.source_validator.get_authority_priority(source1)
        priority2 = self.source_validator.get_authority_priority(source2)
        
        if priority1 <= priority2:
            return source1
        else:
            return source2
    
    def clear(self):
        """清空缓存"""
        self.seen_events.clear()
        self.seen_hashes.clear()
        self.seen_titles.clear()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'seen_events': len(self.seen_events),
            'seen_hashes': len(self.seen_hashes),
            'seen_titles': len(self.seen_titles)
        }
