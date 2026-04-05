# -*- coding: utf-8 -*-
"""
爬虫抽象基类模块 - 智能代理版本
定义所有爬虫必须实现的接口，支持智能代理切换
"""

import sys
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

# 修复导入问题：添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = Path(current_dir).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.config.loader import get_current_date, get_env
from core.storage.file_manager import save_original_news
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """爬虫抽象基类 - 智能代理版本
    
    所有具体爬虫必须继承此类并实现以下方法
    支持国内/国际网站自动切换代理
    """
    
    def __init__(self):
        self.name = ""  # 爬虫名称（如"新华社"）
        self.base_url = ""  # 基础URL
        self.category = ""  # 分类：domestic(国内)/international(国际)
        self.enabled = True  # 是否启用
        self.timeout = 30  # 请求超时时间
        self.max_retries = 3  # 最大重试次数
        self.news_count = 5  # 每次抓取的新闻数量
        self.session = None  # HTTP会话
        
        # ============ 新增：智能代理配置 ============
        self.use_proxy = None  # True:强制代理, False:强制直连, None:自动
        self.proxy_url = None  # 自定义代理URL
        self.ignore_ssl = False  # 是否忽略SSL验证
        
        # 日志
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 代理状态管理
        self.proxy_status = None  # 代理状态：None(未测试), True(可用), False(不可用)
        self.last_proxy_check = None  # 上次代理检查时间
    
    def __str__(self):
        return f"{self.name}爬虫({self.category})"
    
    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name} enabled={self.enabled}>"
    
    @abstractmethod
    def fetch_news_list(self) -> List[Dict[str, Any]]:
        """抓取新闻列表
        
        Returns:
            List[Dict]: 包含新闻基本信息（标题、URL等）的列表
        """
        pass
    
    @abstractmethod
    def fetch_news_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """抓取新闻详情
        
        Args:
            url: 新闻详情页URL
            
        Returns:
            Dict: 包含完整新闻信息的字典，None表示失败
        """
        pass
    
    def get_session(self):
        """获取HTTP会话（智能代理版本，带自检）"""
        if self.session is None:
            try:
                from core.utils.http_client import create_retry_session
                
                # 智能代理策略：根据爬虫类型自动决定
                force_proxy = self.use_proxy
                
                # 如果未明确指定，根据category自动判断
                if force_proxy is None:
                    if self.category == 'international':
                        # 国际新闻默认使用代理
                        force_proxy = True
                        self.logger.info(f"{self.name} 设置为国际新闻源，自动启用代理")
                    elif self.category == 'domestic':
                        # 国内新闻默认不使用代理
                        force_proxy = False
                        self.logger.info(f"{self.name} 设置为国内新闻源，自动直连")
                    else:
                        # 未指定category，使用自动模式
                        force_proxy = None
                        self.logger.info(f"{self.name} 使用智能代理模式")
                
                # 代理服务自检
                if force_proxy:
                    proxy_available = self.check_proxy_status()
                    if not proxy_available:
                        self.logger.warning(f"⚠️  代理服务不可用，自动切换到直连模式")
                        force_proxy = False
                
                # 创建会话
                self.session = create_retry_session(
                    timeout=self.timeout,
                    retries=self.max_retries,
                    ignore_ssl=self.ignore_ssl,
                    force_proxy=force_proxy,
                    proxy_url=self.proxy_url
                )
                
                self.logger.info(f"创建HTTP会话: 超时={self.timeout}s, 代理模式={force_proxy}")
                
            except ImportError as e:
                self.logger.error(f"无法导入http_client模块: {e}")
                # 回退到普通会话
                import requests
                self.session = requests.Session()
                self.session.timeout = self.timeout
                self.logger.warning("回退到普通会话，代理功能可能不可用")
        
        return self.session
    
    def set_proxy_config(self, use_proxy: bool = None, proxy_url: str = None):
        """
        设置爬虫的代理配置
        
        Args:
            use_proxy: True=使用代理, False=直连, None=自动
            proxy_url: 代理服务器URL
        """
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        
        # 重置会话，使新配置生效
        self.session = None
        
        # 重置代理状态
        self.proxy_status = None
        self.last_proxy_check = None
        
        config_type = "自动" if use_proxy is None else ("代理" if use_proxy else "直连")
        self.logger.info(f"代理配置更新: {config_type}, URL: {proxy_url or '默认'}")
    
    def check_proxy_status(self) -> bool:
        """
        检查代理状态
        
        Returns:
            bool: 代理是否可用
        """
        # 检查是否需要重新测试（10分钟内不重复测试）
        if self.last_proxy_check and (datetime.now() - self.last_proxy_check) < timedelta(minutes=10):
            self.logger.info(f"使用缓存的代理状态: {'可用' if self.proxy_status else '不可用'}")
            return self.proxy_status
        
        # 测试代理 - 优先使用爬虫的proxy_url，然后从.env文件读取
        proxy_url = self.proxy_url
        if not proxy_url:
            try:
                from core.utils.http_client import get_proxy_config
                proxy_config = get_proxy_config()
                proxy_url = proxy_config['http_proxy'] or proxy_config['https_proxy']
                if proxy_url:
                    self.logger.info(f"🔧 从配置获取代理URL: {proxy_url}")
            except ImportError as e:
                self.logger.warning(f"⚠️  无法导入get_proxy_config函数: {e}")
                # 回退到环境变量
                proxy_url = get_env("HTTP_PROXY") or get_env("HTTPS_PROXY")
                if proxy_url:
                    self.logger.info(f"🔧 从环境变量获取代理URL: {proxy_url}")
        
        if proxy_url:
            self.logger.info(f"🔍 检查代理状态: {proxy_url}")
            try:
                from core.utils.http_client import test_proxy_connection
                # 测试代理连接，使用较长的超时时间
                self.proxy_status = test_proxy_connection(proxy_url, timeout=15)
                self.last_proxy_check = datetime.now()
                
                if self.proxy_status:
                    self.logger.info(f"✅ 代理状态: 可用")
                    # 代理可用时，确保国际爬虫使用代理
                    if self.category == 'international':
                        self.use_proxy = True
                        self.logger.info(f"🔄 国际爬虫启用代理模式")
                else:
                    self.logger.warning(f"⚠️  代理状态: 不可用")
                    # 代理不可用时，切换到直连模式
                    self.use_proxy = False
                    self.logger.info(f"🔄 自动切换到直连模式")
            except ImportError as e:
                self.logger.warning(f"⚠️  无法导入test_proxy_connection函数: {e}")
                self.proxy_status = False
            except Exception as e:
                self.logger.error(f"❌ 代理状态检查失败: {e}")
                self.proxy_status = False
        else:
            self.proxy_status = False
            self.logger.info("⚠️  未配置代理URL")
            # 未配置代理时，使用直连模式
            self.use_proxy = False
        
        return self.proxy_status
    
    def save_news(self, news_data: Dict[str, Any]) -> Optional[str]:
        """保存新闻到文件
        
        Args:
            news_data: 新闻数据字典
            
        Returns:
            str: 保存的文件路径，None表示失败
        """
        try:
            # 提取必要字段
            title = news_data.get("title", "未命名")
            content = news_data.get("content", "")
            url = news_data.get("url", "")
            
            if not content or len(content.strip()) < 50:
                self.logger.warning(f"⚠️  内容过短，跳过保存: {title[:30]}...")
                return None
            
            # 保存到文件
            filepath = save_original_news(
                media_name=self.name,
                title=title,
                content=content,
                url=url
            )
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"❌ 保存新闻失败 {title[:30]}...: {e}")
            return None
    
    def extract_content(self, html: str, selectors: List[str]) -> str:
        """从HTML中提取内容（通用方法）
        
        Args:
            html: HTML文本
            selectors: 选择器列表，按优先级尝试
            
        Returns:
            str: 提取的文本内容
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            content_parts = []
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    # 提取段落
                    paragraphs = element.find_all('p')
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if len(text) > 20:  # 过滤短段落
                            content_parts.append(text)
                
                if content_parts:
                    break  # 找到内容就停止
            
            # 如果选择器都没找到内容，尝试通用方法
            if not content_parts:
                all_paragraphs = soup.find_all('p')
                for p in all_paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 50:
                        content_parts.append(text)
            
            return "\n\n".join(content_parts)
            
        except Exception as e:
            self.logger.error(f"❌ 内容提取失败: {e}")
            return ""
    
    def cleanup(self):
        """清理资源"""
        if self.session:
            self.session.close()
            self.session = None
    
    def run(self) -> List[Dict[str, Any]]:
        """运行爬虫（主流程）
        
        Returns:
            List[Dict]: 抓取到的新闻列表
        """
        if not self.enabled:
            self.logger.info(f"⏸️  {self.name}爬虫已禁用，跳过")
            return []
        
        self.logger.info(f"🚀 开始抓取: {self.name}")
        
        try:
            # 1. 获取新闻列表
            news_list = self.fetch_news_list()
            if not news_list:
                self.logger.warning(f"⚠️  {self.name}没有获取到新闻列表")
                return []
            
            self.logger.info(f"📋 {self.name}获取到{len(news_list)}条新闻链接")
            
            # 2. 抓取每条新闻的详情
            results = []
            for i, news_item in enumerate(news_list[:self.news_count]):
                url = news_item.get("url", "")
                if not url:
                    continue
                
                self.logger.info(f"  [{i+1}/{min(len(news_list), self.news_count)}] 处理: {url[:80]}...")
                
                # 抓取详情
                detail = self.fetch_news_detail(url)
                if not detail:
                    self.logger.warning(f"    ⚠️  详情抓取失败，跳过")
                    continue
                
                # 合并信息
                news_data = {**news_item, **detail}
                news_data["media"] = self.name
                news_data["category"] = self.category
                news_data["crawled_at"] = get_current_date()
                
                # 保存文件
                filepath = self.save_news(news_data)
                if filepath:
                    news_data["filepath"] = filepath
                    results.append(news_data)
                    self.logger.info(f"    ✅ 处理完成: {news_data.get('title', '')[:50]}...")
                else:
                    self.logger.warning(f"    ⚠️  保存失败，跳过")
            
            self.logger.info(f"✅ {self.name}抓取完成: {len(results)}条成功")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ {self.name}爬虫运行失败: {e}", exc_info=True)
            return []
        finally:
            self.cleanup()


class NewsAPICrawler(BaseCrawler):
    """NewsAPI爬虫（智能代理版本）"""
    
    def __init__(self, source_ids: List[str]):
        super().__init__()
        self.name = "NewsAPI"
        self.category = "international"  # 明确设置为国际新闻
        self.use_proxy = True  # 国际新闻默认使用代理
        self.timeout = 45  # 国际访问可能较慢
        self.source_ids = source_ids
        self.api_key = get_env("NEWS_API_KEY")
        self.api_url = "https://newsapi.org/v2/top-headlines"
        self._articles_cache = {}  # 缓存文章内容，用于fetch_news_detail
    
    def fetch_news_list(self) -> List[Dict[str, Any]]:
        """通过NewsAPI获取新闻列表"""
        if not self.api_key:
            self.logger.error("❌ NewsAPI密钥未配置")
            return []
        
        import requests
        
        # 禁用压缩，让服务器返回未压缩的内容
        headers = {
            "Accept-Encoding": "identity"  # 不接受压缩
        }
        
        params = {
            "sources": ",".join(self.source_ids),
            "apiKey": self.api_key,
            "pageSize": self.news_count,
            "language": "en"
        }
        
        try:
            # 使用智能会话，会自动应用代理
            session = self.get_session()
            response = session.get(self.api_url, params=params, headers=headers, timeout=self.timeout)
            
            # 添加详细的调试信息
            self.logger.info(f"📡 NewsAPI响应状态码: {response.status_code}")
            self.logger.info(f"📡 NewsAPI响应头部: {dict(response.headers)}")
            
            # 尝试获取响应内容
            content = response.text
            self.logger.info(f"📡 NewsAPI响应内容长度: {len(content)} 字符")
            if content:
                self.logger.info(f"📡 NewsAPI响应内容前200字符: {content[:200]}...")
            
            response.raise_for_status()
            data = response.json()
            
            news_list = []
            for article in data.get("articles", []):
                # 提取content字段（NewsAPI返回的content字段，截断到200字符）
                content = article.get("content", "") or ""
                # 如果content为空或太短，使用description作为备用
                if len(content) < 50:
                    content = article.get("description", "") or ""
                
                url = article.get("url", "")
                news_item = {
                    "title": article.get("title", ""),
                    "url": url,
                    "description": article.get("description", ""),
                    "content": content,  # 添加content字段
                    "published_at": article.get("publishedAt", "").split("T")[0],
                    "source": article.get("source", {}).get("name", "")
                }
                
                # 缓存文章内容，用于fetch_news_detail
                if url:
                    self._articles_cache[url] = content
                
                news_list.append(news_item)
            
            self.logger.info(f"✅ NewsAPI获取到{len(news_list)}条新闻")
            return news_list
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"❌ NewsAPI HTTP错误: {e}")
            self.logger.error(f"  状态码: {response.status_code if 'response' in locals() else '未知'}")
            if 'content' in locals():
                self.logger.error(f"  响应内容: {content[:300]}...")
            return []
        except ValueError as e:
            self.logger.error(f"❌ NewsAPI JSON解析错误: {e}")
            self.logger.error(f"  响应内容: {content[:300]}..." if 'content' in locals() else "  响应内容为空")
            return []
        except Exception as e:
            self.logger.error(f"❌ NewsAPI请求失败: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                try:
                    self.logger.error(f"  响应内容: {response.text[:300]}...")
                except (AttributeError, TypeError):
                    pass
            return []
    
    def fetch_news_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """NewsAPI不需要单独的详情抓取，数据已经在列表中"""
        # 从缓存中获取文章内容
        content = self._articles_cache.get(url, "")
        if content:
            self.logger.info(f"📝 使用缓存的content，长度: {len(content)}字符")
        else:
            self.logger.warning(f"⚠️  缓存中未找到content，URL: {url[:50]}...")
        return {"content": content}


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("🧪 爬虫基类测试 - 智能代理版本")
    print("=" * 60)
    
    # 测试抽象基类
    print("✅ BaseCrawler类定义成功")
    print(f"   名称: {BaseCrawler.__name__}")
    print(f"   代理配置属性: use_proxy, proxy_url, category")
    
    # 测试NewsAPICrawler
    print("\n📡 NewsAPICrawler测试:")
    try:
        crawler = NewsAPICrawler(["bbc-news"])
        print(f"   ✅ 创建成功: {crawler}")
        print(f"   名称: {crawler.name}")
        print(f"   分类: {crawler.category}")
        print(f"   代理设置: {crawler.use_proxy} (应显示: True)")
        print(f"   策略: {'✅ 使用代理' if crawler.use_proxy == True else '❌ 错误'}")
    except Exception as e:
        print(f"   ❌ 创建失败: {e}")
    
    print("\n🎯 爬虫基类模块加载成功！")