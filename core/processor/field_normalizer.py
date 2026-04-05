#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段标准化模块 - 将不同来源的 RSS 字段统一到标准模式

功能：
1. 多源字段映射（RSS/Atom/Dublin Core）
2. 日期格式标准化（支持相对时间）
"""

import re
import logging
from typing import Any, Dict, Optional
from datetime import datetime
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

_FIELD_MAPPING = {
    "title": ["title", "headline", "subject", "atom:title"],
    "link": ["link", "url", "guid", "atom:link", "atom:href"],
    "description": ["description", "summary", "abstract", "atom:summary"],
    "pub_date": [
        "pub_date", "published", "date", "pubdate", "updated",
        "dc:date", "atom:published", "atom:updated"
    ],
    "author": [
        "author", "creator", "by", "dc:creator", "dc:author",
        "atom:author", "atom:name"
    ],
    "category": ["category", "tags", "topic", "section", "dc:subject"],
    "guid": ["guid", "id", "uuid", "atom:id"],
    "source": ["source", "from", "origin", "feed_title"],
    "content": [
        "content", "fulltext", "body", "content:encoded",
        "atom:content"
    ],
}

_DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT",
    "%a, %d %b %Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d %b %Y %H:%M:%S %z",
    "%d %b %Y %H:%M:%S",
    "%Y年%m月%d日 %H:%M:%S",
    "%Y年%m月%d日",
]

_RELATIVE_TIME_PATTERNS = [
    (r"(\d+)\s*seconds?\s*ago", "seconds"),
    (r"(\d+)\s*minutes?\s*ago", "minutes"),
    (r"(\d+)\s*hours?\s*ago", "hours"),
    (r"(\d+)\s*days?\s*ago", "days"),
    (r"(\d+)\s*weeks?\s*ago", "weeks"),
    (r"(\d+)\s*months?\s*ago", "months"),
    (r"just now", "now"),
    (r"刚刚", "now"),
    (r"(\d+)\s*秒前", "seconds"),
    (r"(\d+)\s*分钟前", "minutes"),
    (r"(\d+)\s*小时前", "hours"),
    (r"(\d+)\s*天前", "days"),
]


class FieldNormalizer:
    """字段标准化器"""
    
    def normalize_fields(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化字段
        
        Args:
            item: 原始字段字典
        
        Returns:
            标准化后的字段字典
        """
        normalized: Dict[str, Any] = {}
        
        for std_field, candidates in _FIELD_MAPPING.items():
            value = None
            for src_field in candidates:
                v = item.get(src_field)
                if v is not None and str(v).strip():
                    value = v
                    break
            normalized[std_field] = value
        
        if normalized.get("pub_date"):
            normalized["pub_date"] = self._normalize_date(str(normalized["pub_date"]))
        
        if not normalized.get("guid") and normalized.get("link"):
            normalized["guid"] = normalized["link"]
        
        if not normalized.get("link") and normalized.get("guid"):
            normalized["link"] = normalized["guid"]
        
        if not normalized.get("content") and normalized.get("description"):
            normalized["content"] = normalized["description"]
        
        for k, v in item.items():
            if k not in normalized:
                normalized[k] = v
        
        return normalized
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        标准化日期字符串
        
        解析优先级：
        1. ISO 8601 格式（含时区）
        2. 相对时间（如 "2 hours ago"）
        3. 预定义格式列表
        4. dateutil.parser 通用解析
        
        Args:
            date_str: 原始日期字符串
        
        Returns:
            标准化后的日期字符串（YYYY-MM-DD HH:MM:SS），解析失败返回 None
        """
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        if re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", date_str):
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        
        relative_dt = self._parse_relative_time(date_str)
        if relative_dt:
            return relative_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        for fmt in _DATE_FORMATS:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                continue
        
        try:
            dt = date_parser.parse(date_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            logger.debug(f"日期解析失败: {date_str}")
            return None
    
    def _parse_relative_time(self, date_str: str) -> Optional[datetime]:
        """
        解析相对时间
        
        支持格式：
        - 英文：2 hours ago, 3 days ago, just now
        - 中文：2小时前, 3天前, 刚刚
        
        Args:
            date_str: 相对时间字符串
        
        Returns:
            对应的绝对时间
        """
        date_lower = date_str.lower()
        
        for pattern, unit in _RELATIVE_TIME_PATTERNS:
            match = re.match(pattern, date_lower)
            if match:
                if unit == "now":
                    return datetime.now()
                
                try:
                    value = int(match.group(1))
                    kwargs = {unit: -value}
                    return datetime.now() + relativedelta(**kwargs)
                except (ValueError, IndexError):
                    continue
        
        return None
