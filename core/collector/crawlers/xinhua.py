# -*- coding: utf-8 -*-
"""
新华社爬虫 - 智能代理版本
抓取新华社（xinhuanet.com）的时政新闻
智能代理：国内新闻强制直连
"""

import sys
import os
from typing import List, Dict, Any, Optional
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

# 修复导入问题
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.collector.crawlers.base import BaseCrawler
import logging

logger = logging.getLogger(__name__)


class XinhuaCrawler(BaseCrawler):
    """新华社爬虫 - 智能代理版本"""
    
    def __init__(self):
        super().__init__()
        self.name = "新华社"
        self.base_url = "https://www.xinhuanet.com"
        self.category = "domestic"  # 明确设置为国内新闻
        self.use_proxy = False      # 国内新闻强制直连
        self.timeout = 40
        self.max_retries = 5
        self.news_count = 10  # 新华社新闻较多，可以多抓一些
        
        # 新华社特定配置
        self.politics_url = "https://www.xinhuanet.com/politics/"  # 时政要闻
        self.local_url = "https://www.xinhuanet.com/local/"  # 地方新闻
        self.world_url = "https://www.xinhuanet.com/world/"  # 国际新闻
        
        # 内容选择器（按优先级）
        self.content_selectors = [
            "div.article",
            "div.content",
            "div.detail",
            "div.main-content",
            "div.article-content",
            "div.txt",
            "div.text",
            "div.cnt_bd"
        ]
    
    def fetch_news_list(self) -> List[Dict[str, Any]]:
        """抓取新华社新闻列表"""
        news_list = []
        
        try:
            session = self.get_session()
            
            # 主要抓取时政要闻
            logger.info(f"📡 请求新华社时政要闻: {self.politics_url}")
            response = session.get(self.politics_url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 解析HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 多种方式查找新闻链接
            news_links = []
            
            # 方法1: 查找特定的链接模式
            for a in soup.find_all('a', href=True):
                href = a['href']
                title = a.get_text(strip=True)
                
                # 过滤规则
                if (href and title and len(title) >= 5 and 
                    ('/politics/202' in href or '/202' in href) and
                    '.html' in href and 'index' not in href):
                    
                    # 补全URL
                    if not href.startswith('http'):
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif href.startswith('/'):
                            href = self.base_url + href
                    
                    news_links.append({
                        "title": title,
                        "url": href,
                        "raw_title": title
                    })
            
            # 方法2: 查找特定class的链接
            for elem in soup.select('.news-item a, .list-item a, .tit a, .title a'):
                href = elem.get('href', '')
                title = elem.get_text(strip=True)
                
                if href and title and len(title) >= 5 and '.html' in href:
                    if not href.startswith('http'):
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif href.startswith('/'):
                            href = self.base_url + href
                    
                    # 避免重复
                    if not any(item['url'] == href for item in news_links):
                        news_links.append({
                            "title": title,
                            "url": href,
                            "raw_title": title
                        })
            
            # 去重
            unique_links = []
            seen_urls = set()
            
            for item in news_links:
                url = item['url']
                if url not in seen_urls and len(unique_links) < self.news_count * 2:
                    seen_urls.add(url)
                    unique_links.append(item)
            
            logger.info(f"📊 新华社找到{len(unique_links)}条新闻链接")
            
            # 转换为标准格式
            for item in unique_links[:self.news_count]:
                news_list.append({
                    "title": item["title"],
                    "url": item["url"],
                    "source": "新华社时政"
                })
            
            return news_list
            
        except Exception as e:
            logger.error(f"❌ 新华社列表抓取失败: {e}")
            return []
    
    def fetch_news_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """抓取新闻详情"""
        try:
            session = self.get_session()
            
            logger.debug(f"  详细抓取: {url[:80]}...")
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题（多种选择器）
            title = ""
            title_selectors = [
                'h1',
                '.h-title',
                '.title',
                'div.title h1',
                'h1.title',
                'head title'
            ]
            
            for selector in title_selectors:
                elem = soup.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)
                    if title and len(title) > 5:
                        break
            
            # 如果没有找到标题，使用原始标题或URL
            if not title or len(title) < 5:
                title = soup.title.get_text(strip=True) if soup.title else "新华社新闻"
            
            # 提取内容
            content = self.extract_content(response.text, self.content_selectors)
            
            # 如果提取失败，尝试通用方法
            if not content or len(content) < 100:
                # 尝试提取所有p标签
                all_paragraphs = soup.find_all('p')
                paragraphs = [p.get_text(strip=True) for p in all_paragraphs 
                             if len(p.get_text(strip=True)) > 30]
                content = "\n\n".join(paragraphs)
            
            # 提取发布时间
            publish_time = ""
            time_selectors = [
                '.h-time',
                '.time',
                '.pubtime',
                'span.time',
                'div.time',
                'meta[property="article:published_time"]',
                'meta[name="publishdate"]'
            ]
            
            for selector in time_selectors:
                if selector.startswith('meta'):
                    elem = soup.select_one(selector)
                    if elem and elem.get('content'):
                        publish_time = elem['content']
                        break
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        publish_time = elem.get_text(strip=True)
                        if publish_time:
                            break
            
            # 清理时间格式
            if publish_time:
                # 提取日期部分
                date_match = re.search(r'(\d{4})[-年](\d{1,2})[-月](\d{1,2})', publish_time)
                if date_match:
                    publish_time = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
            
            # 提取作者
            author = ""
            author_selectors = [
                '.author',
                '.source',
                'span.author',
                'div.author',
                'meta[name="author"]'
            ]
            
            for selector in author_selectors:
                if selector.startswith('meta'):
                    elem = soup.select_one(selector)
                    if elem and elem.get('content'):
                        author = elem['content']
                        break
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        author = elem.get_text(strip=True)
                        if author and '来源' in author:
                            author = author.replace('来源：', '').replace('来源:', '').strip()
                            break
            
            return {
                "title": title,
                "content": content,
                "publish_time": publish_time,
                "author": author,
                "source_url": url
            }
            
        except Exception as e:
            logger.error(f"❌ 新华社详情抓取失败 {url[:50]}...: {e}")
            return None
    
    def extract_content(self, html: str, selectors: List[str]) -> str:
        """新华社特定的内容提取方法"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # 首先尝试新华社特定的选择器
            xinhua_selectors = [
                'div#p-detail',
                'div.detail',
                'div.article',
                'div.content'
            ]
            
            for selector in xinhua_selectors:
                element = soup.select_one(selector)
                if element:
                    # 提取段落
                    paragraphs = element.find_all('p')
                    content_parts = []
                    
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        # 过滤短段落和广告
                        if len(text) > 20 and '广告' not in text:
                            content_parts.append(text)
                    
                    if content_parts:
                        return "\n\n".join(content_parts)
            
            # 如果特定选择器失败，使用基类方法
            return super().extract_content(html, selectors)
            
        except Exception as e:
            logger.error(f"❌ 新华社内容提取失败: {e}")
            return ""


# 测试函数
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("=" * 70)
    print("🧪 新华社爬虫测试 - 智能代理版本")
    print("=" * 70)
    
    try:
        # 创建爬虫
        crawler = XinhuaCrawler()
        print(f"✅ 创建爬虫: {crawler}")
        print(f"   名称: {crawler.name}")
        print(f"   分类: {crawler.category}")
        print(f"   代理设置: {crawler.use_proxy} (应显示: False)")
        print(f"   策略: {'✅ 直连' if crawler.use_proxy == False else '❌ 错误'}")
        print(f"   抓取数量: {crawler.news_count}")
        
        # 测试获取新闻列表
        print("\n📋 测试获取新闻列表...")
        news_list = crawler.fetch_news_list()
        print(f"   获取到{len(news_list)}条新闻链接")
        
        if news_list:
            for i, news in enumerate(news_list[:3]):
                print(f"     {i+1}. {news.get('title', '无标题')[:40]}...")
                print(f"        URL: {news.get('url', '无URL')[:60]}...")
        
        print("\n🎯 新华社爬虫测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()