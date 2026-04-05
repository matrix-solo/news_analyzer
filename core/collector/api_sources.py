#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API源采集模块
支持NewsAPI、GNews等API源
与RSS源统一接口，支持混合采集
"""

import os
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class APINewsItem:
    """API新闻条目"""
    title: str
    content: str
    link: str
    source_name: str
    pub_date: datetime
    author: Optional[str] = None
    image_url: Optional[str] = None


class NewsAPISource:
    """NewsAPI源"""
    
    BASE_URL = "https://newsapi.org/v2"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('NEWS_API_KEY')
        if not self.api_key:
            raise ValueError("NewsAPI key not found")
    
    def search(
        self,
        query: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: str = 'zh',
        page_size: int = 20,
        sort_by: str = 'relevancy'
    ) -> List[APINewsItem]:
        """
        搜索新闻
        
        Args:
            query: 搜索关键词
            from_date: 开始日期 (YYYY-MM-DD)
            to_date: 结束日期 (YYYY-MM-DD)
            language: 语言代码
            page_size: 每页数量
            sort_by: 排序方式 (relevancy, popularity, publishedAt)
        """
        url = f"{self.BASE_URL}/everything"
        
        params = {
            'q': query,
            'apiKey': self.api_key,
            'language': language,
            'pageSize': page_size,
            'sortBy': sort_by
        }
        
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.error(f"NewsAPI error: {data.get('message')}")
                return []
            
            articles = data.get('articles', [])
            return self._parse_articles(articles)
            
        except Exception as e:
            logger.error(f"NewsAPI request failed: {e}")
            return []
    
    def get_top_headlines(
        self,
        category: Optional[str] = None,
        country: str = 'cn',
        page_size: int = 20
    ) -> List[APINewsItem]:
        """获取头条新闻"""
        url = f"{self.BASE_URL}/top-headlines"
        
        params = {
            'apiKey': self.api_key,
            'country': country,
            'pageSize': page_size
        }
        
        if category:
            params['category'] = category
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'ok':
                return []
            
            return self._parse_articles(data.get('articles', []))
            
        except Exception as e:
            logger.error(f"NewsAPI headlines failed: {e}")
            return []
    
    def _parse_articles(self, articles: List[Dict]) -> List[APINewsItem]:
        """解析文章列表"""
        items = []
        
        for article in articles:
            try:
                # 解析日期
                pub_date_str = article.get('publishedAt', '')
                if pub_date_str:
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                else:
                    pub_date = datetime.now()
                
                item = APINewsItem(
                    title=article.get('title', ''),
                    content=article.get('content') or article.get('description', ''),
                    link=article.get('url', ''),
                    source_name=article.get('source', {}).get('name', 'NewsAPI'),
                    pub_date=pub_date,
                    author=article.get('author'),
                    image_url=article.get('urlToImage')
                )
                items.append(item)
                
            except Exception as e:
                logger.warning(f"Parse article failed: {e}")
                continue
        
        return items


class GNewsSource:
    """GNews API源"""
    
    BASE_URL = "https://gnews.io/api/v4"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GNEWS_API_KEY')
        if not self.api_key:
            raise ValueError("GNews API key not found")
    
    def search(
        self,
        query: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: str = 'zh',
        max_results: int = 20
    ) -> List[APINewsItem]:
        """搜索新闻"""
        url = f"{self.BASE_URL}/search"
        
        params = {
            'q': query,
            'apikey': self.api_key,
            'lang': language,
            'max': max_results
        }
        
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            articles = data.get('articles', [])
            return self._parse_articles(articles)
            
        except Exception as e:
            logger.error(f"GNews request failed: {e}")
            return []


class APISourceManager:
    """API源管理器"""
    
    SOURCES = {
        'newsapi': NewsAPISource,
        'gnews': GNewsSource
    }
    
    def __init__(self):
        self.sources = {}
    
    def register_source(self, name: str, source_class):
        """注册新的API源"""
        self.SOURCES[name] = source_class
    
    def get_source(self, name: str) -> Optional[object]:
        """获取API源实例"""
        if name not in self.sources:
            if name in self.SOURCES:
                try:
                    self.sources[name] = self.SOURCES[name]()
                except ValueError as e:
                    logger.warning(f"Failed to init {name}: {e}")
                    return None
        return self.sources.get(name)
    
    def search_all(
        self,
        query: str,
        from_date: Optional[str] = None,
        max_results: int = 20
    ) -> Dict[str, List[APINewsItem]]:
        """
        从所有可用API源搜索
        
        Returns:
            {'newsapi': [...], 'gnews': [...]}
        """
        results = {}
        
        for name in self.SOURCES:
            source = self.get_source(name)
            if source:
                try:
                    items = source.search(query, from_date=from_date, page_size=max_results)
                    if items:
                        results[name] = items
                        logger.info(f"{name}: found {len(items)} articles")
                except Exception as e:
                    logger.error(f"{name} search failed: {e}")
        
        return results


# 与RSS统一接口的适配器
class APIToRSSAdapter:
    """API源转RSS格式适配器"""
    
    @staticmethod
    def adapt(api_item: APINewsItem) -> Dict:
        """将API新闻项转换为RSS格式"""
        return {
            'title': api_item.title,
            'link': api_item.link,
            'content': api_item.content,
            'source_name': api_item.source_name,
            'source_type': 'api',
            'category': '未分类',
            'credibility': '中高',
            'pub_date': api_item.pub_date.isoformat() if api_item.pub_date else '',
            'author': api_item.author,
            'image_url': api_item.image_url
        }
