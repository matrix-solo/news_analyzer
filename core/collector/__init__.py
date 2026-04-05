#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS采集模块

提供统一的RSS源新闻采集
"""

from .parser import RSSParser, RSSFeed, RSSItem
from .sources import RSSSourceManager, RSSSource
from .unified_collector import UnifiedRSSCollector, CachedNewsItem

__all__ = [
    'RSSParser',
    'RSSFeed',
    'RSSItem',
    'RSSSourceManager',
    'RSSSource',
    'UnifiedRSSCollector',
    'CachedNewsItem',
]
