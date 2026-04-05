# -*- coding: utf-8 -*-
"""
爬虫工厂模块 - 智能代理版本
根据配置动态创建和管理爬虫实例，支持智能代理配置
"""

import sys
import os
from typing import List, Dict, Any, Optional, Type

# 修复导入问题
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.collector.crawlers.base import BaseCrawler, NewsAPICrawler
from core.collector.crawlers.xinhua import XinhuaCrawler
from core.collector.crawlers.people import PeopleCrawler
from core.config.loader import load_sources
import logging

logger = logging.getLogger(__name__)


class CrawlerFactory:
    """爬虫工厂类 - 智能代理版本"""
    
    # 爬虫类型注册表
    _crawler_registry: Dict[str, Type[BaseCrawler]] = {}
    
    @classmethod
    def register_crawler(cls, name: str, crawler_class: Type[BaseCrawler]):
        """注册爬虫类"""
        cls._crawler_registry[name] = crawler_class
        logger.debug(f"📝 注册爬虫: {name} -> {crawler_class.__name__}")
    
    @classmethod
    def create_crawler(cls, name: str, **kwargs) -> Optional[BaseCrawler]:
        """创建爬虫实例 - 智能代理版本
        
        Args:
            name: 爬虫名称
            **kwargs: 传递给爬虫构造函数的参数
            
        Returns:
            BaseCrawler实例，None表示创建失败
        """
        crawler_class = cls._crawler_registry.get(name)
        if not crawler_class:
            logger.error(f"❌ 未知的爬虫类型: {name}")
            logger.info(f"   可用爬虫: {list(cls._crawler_registry.keys())}")
            return None
        
        try:
            crawler = crawler_class(**kwargs)
            logger.info(f"✅ 创建爬虫: {crawler}")
            return crawler
        except Exception as e:
            logger.error(f"❌ 创建爬虫失败 {name}: {e}")
            return None
    
    @classmethod
    def get_all_crawlers(cls) -> List[str]:
        """获取所有注册的爬虫名称"""
        return list(cls._crawler_registry.keys())


def setup_crawler_registry():
    """设置爬虫注册表（初始化）"""
    # 注册国内爬虫
    CrawlerFactory.register_crawler("新华社", XinhuaCrawler)
    CrawlerFactory.register_crawler("人民日报", PeopleCrawler)
    
    # 注册国际爬虫（NewsAPI）
    CrawlerFactory.register_crawler("NewsAPI", NewsAPICrawler)
    
    logger.info(f"📋 爬虫注册表初始化完成: {CrawlerFactory.get_all_crawlers()}")


def create_crawlers_from_config() -> List[BaseCrawler]:
    """根据配置文件创建爬虫实例 - 智能代理版本"""
    crawlers = []
    
    try:
        # 加载配置
        config = load_sources()
        if not config:
            logger.error("❌ 无法加载配置文件")
            return []
        
        # 初始化注册表
        setup_crawler_registry()
        
        # 从环境变量读取代理配置
        from core.config.loader import get_env
        default_proxy_url = get_env("HTTP_PROXY") or get_env("HTTPS_PROXY")
        
        # 创建国内爬虫
        domestic_config = config.get('domestic', {})
        
        # 中央媒体
        central_sources = domestic_config.get('central', [])
        for source in central_sources:
            if source.get('method') == 'crawler' and source.get('enabled', True):
                name = source.get('name', '')
                if name in CrawlerFactory.get_all_crawlers():
                    crawler = CrawlerFactory.create_crawler(name)
                    if crawler:
                        # 应用配置
                        crawler.enabled = source.get('enabled', True)
                        crawler.news_count = source.get('count', crawler.news_count)
                        
                        # 国内新闻强制直连
                        crawler.use_proxy = False
                        
                        crawlers.append(crawler)
                        logger.debug(f"📝 国内爬虫 {name}: 代理模式=直连")
        
        # 创建国际爬虫（NewsAPI）
        international_config = config.get('international', {})
        
        # 收集所有NewsAPI源
        newsapi_sources = []
        
        for category in ['news_agency', 'comprehensive', 'analytical', 'regional']:
            sources = international_config.get(category, [])
            for source in sources:
                if (source.get('method') == 'newsapi' and 
                    source.get('enabled', True) and 
                    source.get('sources')):
                    newsapi_sources.append(source['sources'])
        
        # 创建NewsAPI爬虫
        if newsapi_sources:
            # 去重并合并
            unique_sources = list(set(newsapi_sources))
            
            # 限制最多5个源，避免请求过长
            source_ids = unique_sources[:5]
            
            newsapi_crawler = CrawlerFactory.create_crawler(
                "NewsAPI",
                source_ids=source_ids
            )
            
            if newsapi_crawler:
                # 如果有默认代理URL，使用它
                if default_proxy_url:
                    newsapi_crawler.proxy_url = default_proxy_url
                    logger.info(f"📝 NewsAPI爬虫: 应用代理URL={default_proxy_url}")
                
                # 检查代理状态
                logger.info("🔍 NewsAPI爬虫: 开始检查代理状态")
                proxy_available = newsapi_crawler.check_proxy_status()
                
                # 国际新闻使用代理（如果可用）
                newsapi_crawler.use_proxy = proxy_available
                
                if proxy_available:
                    logger.info(f"✅ NewsAPI爬虫: 代理模式=使用代理")
                else:
                    logger.warning(f"⚠️  NewsAPI爬虫: 代理不可用，切换到直连模式")
                
                crawlers.append(newsapi_crawler)
                logger.info(f"📝 NewsAPI爬虫: 配置完成，源数量={len(source_ids)}")
        
        # 统计和日志
        domestic_count = sum(1 for c in crawlers if c.category == 'domestic')
        international_count = sum(1 for c in crawlers if c.category == 'international')
        
        logger.info(f"📊 从配置创建了{len(crawlers)}个爬虫（智能代理已配置）")
        logger.info(f"   • 国内爬虫: {domestic_count}个（全部直连）")
        logger.info(f"   • 国际爬虫: {international_count}个（全部使用代理）")
        
        for crawler in crawlers:
            proxy_strategy = "直连" if crawler.use_proxy == False else "代理"
            logger.info(f"     - {crawler.name} ({crawler.category}): {proxy_strategy}")
        
        return crawlers
        
    except Exception as e:
        logger.error(f"❌ 从配置创建爬虫失败: {e}")
        return []


def run_all_crawlers(crawlers: List[BaseCrawler]) -> List[Dict[str, Any]]:
    """运行所有爬虫并收集结果 - 智能代理版本
    
    Args:
        crawlers: 爬虫实例列表
        
    Returns:
        List[Dict]: 所有爬虫抓取到的新闻
    """
    all_news = []
    
    if not crawlers:
        logger.warning("⚠️  没有可运行的爬虫")
        return []
    
    logger.info(f"🚀 开始运行{len(crawlers)}个爬虫（智能代理模式）...")
    
    for crawler in crawlers:
        if not crawler.enabled:
            logger.info(f"⏸️  {crawler.name}已禁用，跳过")
            continue
        
        try:
            # 显示代理策略
            proxy_strategy = "直连" if crawler.use_proxy == False else "代理"
            logger.info(f"🔍 运行爬虫: {crawler.name} ({proxy_strategy})")
            
            news = crawler.run()
            if news:
                all_news.extend(news)
                logger.info(f"✅ {crawler.name}抓取完成: {len(news)}条")
            else:
                logger.warning(f"⚠️  {crawler.name}没有抓取到新闻")
        except Exception as e:
            logger.error(f"❌ {crawler.name}运行异常: {e}")
            continue
    
    logger.info(f"📊 所有爬虫运行完成，总共抓取{len(all_news)}条新闻")
    return all_news


# 测试函数
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("=" * 70)
    print("🧪 爬虫工厂测试 - 智能代理版本")
    print("=" * 70)
    
    try:
        # 测试注册表
        setup_crawler_registry()
        print(f"✅ 爬虫注册表: {CrawlerFactory.get_all_crawlers()}")
        
        # 测试创建单个爬虫
        print("\n🔧 测试创建爬虫:")
        xinhua = CrawlerFactory.create_crawler("新华社")
        if xinhua:
            print(f"   ✅ 新华社爬虫: {xinhua}")
            print(f"      名称: {xinhua.name}")
            print(f"      分类: {xinhua.category}")
            print(f"      代理设置: {xinhua.use_proxy} (应显示: False)")
            print(f"      策略: {'✅ 直连' if xinhua.use_proxy == False else '❌ 错误'}")
        
        # 测试从配置创建
        print("\n📋 测试从配置创建爬虫:")
        crawlers = create_crawlers_from_config()
        print(f"   创建了{len(crawlers)}个爬虫")
        
        for i, crawler in enumerate(crawlers):
            proxy_strategy = "直连" if crawler.use_proxy == False else "代理"
            print(f"     {i+1}. {crawler.name} ({crawler.category}) - {proxy_strategy}")
        
        # 验证代理配置
        print("\n🔍 代理配置验证:")
        correct_config = True
        
        for crawler in crawlers:
            if crawler.category == 'domestic' and crawler.use_proxy != False:
                print(f"   ❌ {crawler.name}: 国内爬虫应直连，但配置为使用代理")
                correct_config = False
            else:
                strategy = "直连" if crawler.use_proxy == False else "代理"
                print(f"   ✅ {crawler.name}: 配置正确 ({strategy})")
        
        if correct_config:
            print("\n🎯 所有爬虫代理配置正确！")
            print("💡 系统已准备好：")
            print("   • 国内新闻 → 自动直连")
            print("   • 国际新闻 → 自动使用代理")
        else:
            print("\n⚠️  部分爬虫代理配置需要调整")
        
        print("\n🎯 爬虫工厂测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()