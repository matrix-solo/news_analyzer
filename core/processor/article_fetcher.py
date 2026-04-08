#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻原文获取器

职责：
- 解析Google RSS重定向链接
- 使用代理获取网页正文
- 提取高质量正文内容
- 降级处理（失败时回退到摘要）
"""

import logging
import os
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PROXY_URL = os.getenv('RSS_HTTP_PROXY', '')

CONTENT_SELECTORS = [
    'article',
    'main',
    '[role="main"]',
    '.article-content',
    '.post-content',
    '.entry-content',
    '.news-content',
    '.content',
    '#article-body',
    '#content',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


class ArticleFetcher:
    """新闻原文获取器"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch(self, news: Dict) -> Optional[str]:
        """
        获取单条新闻原文

        Args:
            news: 新闻字典，需包含 link 字段

        Returns:
            原文文本，获取失败返回None
        """
        url = news.get('link') or news.get('url')
        if not url:
            logger.warning(f"新闻缺少URL: {news.get('news_id', 'unknown')}")
            return None

        url = self._parse_google_rss(url)

        try:
            html = self._fetch_html(url)
            if not html:
                return None

            content = self._extract_content(html)
            if content and len(content) > 100:
                logger.info(f"成功获取原文: {news.get('news_id', 'unknown')} ({len(content)} chars)")
                return content

            logger.warning(f"原文内容过短或提取失败: {news.get('news_id', 'unknown')}")
            return None

        except Exception as e:
            logger.error(f"获取原文失败: {news.get('news_id', 'unknown')} - {e}")
            return None

    def fetch_batch(self, news_list: List[Dict], max_workers: int = 10) -> Dict[str, str]:
        """
        批量并行获取新闻原文

        Args:
            news_list: 新闻列表
            max_workers: 最大并发数（默认10）

        Returns:
            {news_id: original_article} 字典
        """
        results = {}
        failed_ids = []

        def fetch_one(news: Dict) -> tuple:
            news_id = news.get('news_id', 'unknown')
            try:
                article = self.fetch(news)
                return (news_id, article) if article else (news_id, None)
            except Exception as e:
                logger.warning(f"获取原文异常: {news_id} - {e}")
                return (news_id, None)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_one, news): news for news in news_list}
            for future in as_completed(futures):
                news_id, article = future.result()
                if article:
                    results[news_id] = article
                else:
                    failed_ids.append(news_id)

        logger.info(f"批量获取原文完成: {len(results)}/{len(news_list)} 成功, {len(failed_ids)} 失败")
        return results

    def _parse_google_rss(self, url: str) -> str:
        """
        解析Google RSS重定向链接，提取真实URL

        Args:
            url: Google RSS URL

        Returns:
            真实URL
        """
        if 'news.google.com' not in url:
            return url

        try:
            parsed = urlparse(url)
            if '/articles/' in url:
                match = re.search(r'url=([^&]+)', url)
                if match:
                    from urllib.parse import unquote
                    real_url = unquote(match.group(1))
                    logger.debug(f"Google RSS解析: {url[:50]}... -> {real_url[:50]}...")
                    return real_url

                match = re.search(r'q=([^&]+)', url)
                if match:
                    from urllib.parse import unquote
                    real_url = unquote(match.group(1))
                    return real_url

            if parsed.query:
                params = parse_qs(parsed.query)
                if 'url' in params:
                    from urllib.parse import unquote
                    return unquote(params['url'][0])

        except Exception as e:
            logger.debug(f"Google RSS解析失败: {e}")

        return url

    def _fetch_html(self, url: str) -> Optional[str]:
        """
        获取网页HTML（可选代理）

        Args:
            url: 目标URL

        Returns:
            HTML文本，失败返回None
        """
        proxies = {'http': PROXY_URL, 'https': PROXY_URL} if PROXY_URL else None

        try:
            response = self.session.get(url, proxies=proxies, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text

        except requests.exceptions.Timeout:
            logger.warning(f"获取超时: {url[:60]}...")
            return None

        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP错误 {e.response.status_code}: {url[:60]}...")
            return None

        except Exception as e:
            logger.error(f"获取失败: {url[:60]}... - {e}")
            return None

    def _extract_content(self, html: str) -> Optional[str]:
        """
        从HTML中提取正文内容

        Args:
            html: HTML文本

        Returns:
            纯文本内容
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
                tag.decompose()

            content = None

            for selector in CONTENT_SELECTORS:
                elements = soup.select(selector)
                for element in elements:
                    paragraphs = element.find_all('p')
                    if paragraphs:
                        text_parts = []
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if len(text) > 20:
                                text_parts.append(text)
                        if text_parts:
                            content = '\n\n'.join(text_parts)
                            break
                if content:
                    break

            if not content:
                all_paragraphs = soup.find_all('p')
                text_parts = []
                for p in all_paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 50:
                        text_parts.append(text)
                content = '\n\n'.join(text_parts)

            if content:
                content = ' '.join(content.split())
                return content[:10000]

            return None

        except Exception as e:
            logger.error(f"内容提取失败: {e}")
            return None

    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()


def fetch_original_article(news: Dict, timeout: int = 10) -> Optional[str]:
    """
    便捷函数：获取单条新闻原文

    Args:
        news: 新闻字典
        timeout: 超时时间（秒）

    Returns:
        原文文本，失败返回None
    """
    fetcher = ArticleFetcher(timeout=timeout)
    try:
        return fetcher.fetch(news)
    finally:
        fetcher.close()


def fetch_original_articles(news_list: List[Dict], timeout: int = 10) -> Dict[str, str]:
    """
    便捷函数：批量获取新闻原文

    Args:
        news_list: 新闻列表
        timeout: 超时时间（秒）

    Returns:
        {news_id: original_article} 字典
    """
    fetcher = ArticleFetcher(timeout=timeout)
    try:
        return fetcher.fetch_batch(news_list)
    finally:
        fetcher.close()