# -*- coding: utf-8 -*-
"""
人民日报爬虫 - 智能代理版本
抓取人民日报（people.com.cn）的新闻
智能代理：国内新闻强制直连
特别注意：人民日报有SSL证书问题
"""

import sys
import os
from typing import List, Dict, Any, Optional
import re
from datetime import datetime
from urllib.parse import urljoin

# 修复导入问题
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.collector.crawlers.base import BaseCrawler
import logging

logger = logging.getLogger(__name__)


class PeopleCrawler(BaseCrawler):
    """人民日报爬虫 - 智能代理版本"""
    
    def __init__(self):
        super().__init__()
        self.name = "人民日报"
        self.base_url = "https://www.people.com.cn"
        self.category = "domestic"  # 明确设置为国内新闻
        self.use_proxy = False      # 国内新闻强制直连
        self.timeout = 45  # 人民日报较慢，增加超时
        self.max_retries = 5
        self.news_count = 8
        self.ignore_ssl = True  # 人民日报有SSL证书问题
        
        # 人民日报URL
        self.home_url = "https://www.people.com.cn/"
        self.politics_url = "https://politics.people.com.cn/"  # 时政
        self.opinion_url = "https://opinion.people.com.cn/"  # 观点
        
        # 内容选择器
        self.content_selectors = [
            "div.rm_txt_con",
            "div.show_text",
            "div.text",
            "div.content",
            "div.article",
            "div.txt"
        ]
        
        # 人民日报特定的页面模式
        self.url_patterns = [
            r'/n1/\d{4}/\d{4}/c\d+-\d+\.html',  # 标准新闻页面
            r'/GB/\d+/\d+/\d+\.html',  # 旧版页面
            r'/paper/\d+/\d+/\d+\.html',  # 报纸页面
        ]
    
    def is_valid_people_url(self, url: str) -> bool:
        """检查是否是有效的人民日报URL"""
        if not url or 'people.com.cn' not in url:
            return False
        
        # 检查是否匹配已知模式
        for pattern in self.url_patterns:
            if re.search(pattern, url):
                return True
        
        # 排除非新闻页面
        excluded_keywords = [
            'index', 'javascript:', 'mailto:', '#',
            'download', 'video', 'photo', 'pic',
            'special', 'subject', 'topic'
        ]
        
        for keyword in excluded_keywords:
            if keyword in url.lower():
                return False
        
        return '.html' in url or '.shtml' in url
    
    def fetch_news_list(self) -> List[Dict[str, Any]]:
        """抓取人民日报新闻列表"""
        news_list = []
        
        try:
            session = self.get_session()
            
            # 抓取首页
            logger.info(f"📡 请求人民日报首页: {self.home_url}")
            response = session.get(self.home_url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'gb2312'  # 人民日报使用GB2312编码
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 多种方式查找新闻链接
            all_links = []
            
            # 方法1: 查找所有a标签
            for a in soup.find_all('a', href=True):
                href = a['href']
                title = a.get_text(strip=True)
                
                if href and title and len(title) >= 4:
                    # 补全URL
                    if not href.startswith('http'):
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif href.startswith('/'):
                            href = self.base_url + href
                        else:
                            # 相对路径
                            href = urljoin(self.home_url, href)
                    
                    all_links.append({
                        "title": title,
                        "url": href,
                        "raw_title": title
                    })
            
            # 方法2: 查找特定区域的链接
            for selector in ['.news-list a', '.list a', '.tit a', 'h3 a', 'h4 a']:
                for elem in soup.select(selector):
                    href = elem.get('href', '')
                    title = elem.get_text(strip=True)
                    
                    if href and title and len(title) >= 4:
                        if not href.startswith('http'):
                            if href.startswith('//'):
                                href = 'https:' + href
                            elif href.startswith('/'):
                                href = self.base_url + href
                            else:
                                href = urljoin(self.home_url, href)
                        
                        all_links.append({
                            "title": title,
                            "url": href,
                            "raw_title": title
                        })
            
            # 过滤和去重
            seen_urls = set()
            filtered_links = []
            
            for item in all_links:
                url = item['url']
                
                # 过滤条件
                if (url not in seen_urls and 
                    self.is_valid_people_url(url) and
                    len(filtered_links) < self.news_count * 3):
                    
                    seen_urls.add(url)
                    filtered_links.append(item)
            
            logger.info(f"📊 人民日报找到{len(filtered_links)}条有效链接")
            
            # 转换为标准格式
            for item in filtered_links[:self.news_count]:
                news_list.append({
                    "title": item["title"],
                    "url": item["url"],
                    "source": "人民日报"
                })
            
            return news_list
            
        except Exception as e:
            logger.error(f"❌ 人民日报列表抓取失败: {e}")
            return []
    
    def fetch_news_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """抓取新闻详情"""
        try:
            session = self.get_session()
            
            logger.debug(f"  详细抓取: {url[:80]}...")
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 检测编码
            if 'charset=gb' in response.text.lower() or 'charset=gb' in response.headers.get('content-type', '').lower():
                response.encoding = 'gb2312'
            else:
                response.encoding = 'utf-8'
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            title = ""
            title_selectors = [
                'h1',
                '.text_title h1',
                '.title h1',
                'div.title h1',
                'head title'
            ]
            
            for selector in title_selectors:
                elem = soup.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)
                    if title and len(title) > 5:
                        break
            
            # 清理标题
            if title:
                # 移除可能的网站名
                title = re.sub(r'[-—_]?人民网$|[-—_]?人民日报$', '', title).strip()
            
            # 提取内容
            content = ""
            
            # 先尝试人民日报特定的选择器
            people_selectors = [
                'div.rm_txt_con',
                'div.show_text',
                'div.text_con'
            ]
            
            for selector in people_selectors:
                element = soup.select_one(selector)
                if element:
                    # 提取段落
                    paragraphs = element.find_all('p')
                    content_parts = []
                    
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        # 过滤短段落、广告、相关阅读等
                        if (len(text) > 20 and 
                            '广告' not in text and 
                            '相关阅读' not in text and
                            '推荐阅读' not in text):
                            content_parts.append(text)
                    
                    if content_parts:
                        content = "\n\n".join(content_parts)
                        break
            
            # 如果特定选择器失败，使用通用方法
            if not content or len(content) < 100:
                content = self.extract_content(response.text, self.content_selectors)
            
            # 提取发布时间
            publish_time = ""
            time_selectors = [
                '.sou',
                '.origin',
                '.time',
                'div.sou',
                'span.sou'
            ]
            
            for selector in time_selectors:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    # 提取日期
                    date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
                    if date_match:
                        publish_time = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
                        break
            
            # 提取作者/来源
            author = "人民日报"
            source_selectors = ['.sou', '.origin']
            
            for selector in source_selectors:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if '来源：' in text:
                        author = text.split('来源：')[-1].split()[0]
                        break
                    elif '来源:' in text:
                        author = text.split('来源:')[-1].split()[0]
                        break
            
            return {
                "title": title if title else "人民日报新闻",
                "content": content,
                "publish_time": publish_time,
                "author": author,
                "source_url": url
            }
            
        except Exception as e:
            logger.error(f"❌ 人民日报详情抓取失败 {url[:50]}...: {e}")
            return None


# 测试函数
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("=" * 70)
    print("🧪 人民日报爬虫测试 - 智能代理版本")
    print("=" * 70)
    
    try:
        # 创建爬虫
        crawler = PeopleCrawler()
        print(f"✅ 创建爬虫: {crawler}")
        print(f"   名称: {crawler.name}")
        print(f"   分类: {crawler.category}")
        print(f"   代理设置: {crawler.use_proxy} (应显示: False)")
        print(f"   策略: {'✅ 直连' if crawler.use_proxy == False else '❌ 错误'}")
        print(f"   忽略SSL: {crawler.ignore_ssl}")
        print(f"   抓取数量: {crawler.news_count}")
        
        # 测试URL验证
        print("\n🔗 URL验证测试:")
        test_urls = [
            "https://www.people.com.cn/n1/2024/1231/c1234-12345678.html",
            "https://www.people.com.cn/GB/123/456/789.html",
            "https://www.people.com.cn/paper/123/456/789.html",
            "https://www.people.com.cn/index.html"
        ]
        
        for url in test_urls:
            is_valid = crawler.is_valid_people_url(url)
            print(f"   {url[:40]}...: {'✅ 有效' if is_valid else '❌ 无效'}")
        
        # 测试获取新闻列表
        print("\n📋 测试获取新闻列表...")
        news_list = crawler.fetch_news_list()
        print(f"   获取到{len(news_list)}条新闻链接")
        
        if news_list:
            for i, news in enumerate(news_list[:3]):
                print(f"     {i+1}. {news.get('title', '无标题')[:40]}...")
                print(f"        URL: {news.get('url', '无URL')[:60]}...")
        
        print("\n🎯 人民日报爬虫测试完成！")
        print("💡 注意: 人民日报网站可能较慢，且有SSL证书问题")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()