#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一RSS采集器 - 合并 RSSCollector 和 RSSIncrementalCollector

功能：
1. 核心层（必选）：RSS获取、解析、代理配置
2. 增量层（默认启用）：缓存、去重、归档
3. 后台服务层（可选）：定时抓取守护进程

设计原则：
- 单一入口，统一维护
- 功能通过参数组合
- 向后兼容现有调用
"""

import os
import sys
import json
import time
import logging
import hashlib
import threading
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.collector.sources import RSSSource, RSSSourceManager
from core.collector.parser import RSSParser, RSSFeed, RSSItem


@dataclass
class CachedNewsItem:
    """缓存的新闻条目"""
    id: str
    title: str
    content: str
    link: str
    source: str
    published: str
    crawl_time: str
    domain: str = "general"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CachedNewsItem':
        return cls(**data)


class UnifiedRSSCollector:
    """
    统一RSS采集器
    
    使用方式：
    ```python
    # 单次采集（无增量、无后台）
    collector = UnifiedRSSCollector(incremental_mode=False)
    feeds = collector.fetch_all()
    
    # 增量采集（有缓存、去重）
    collector = UnifiedRSSCollector()
    result = collector.crawl_once()
    
    # 后台服务
    collector = UnifiedRSSCollector(background_mode=True)
    collector.start_background(interval=1800)
    ```
    """
    
    DEFAULT_INTERVAL = 1800
    ARCHIVE_TIME = "00:10"
    
    def __init__(
        self,
        source_manager: RSSSourceManager = None,
        storage_dir: str = None,
        incremental_mode: bool = True,
        background_mode: bool = False
    ):
        """
        初始化统一采集器
        
        Args:
            source_manager: RSS源管理器
            storage_dir: 存储目录
            incremental_mode: 是否启用增量模式（缓存、去重、归档）
            background_mode: 是否启用后台服务模式
        """
        self.logger = logging.getLogger("UnifiedRSSCollector")
        self.source_manager = source_manager or RSSSourceManager()
        self.parser = RSSParser()
        
        self._setup_session()
        
        self._fetch_status: Dict[str, Dict] = {}
        self._cache: Dict[str, RSSFeed] = {}
        
        self.incremental_mode = incremental_mode
        self.background_mode = background_mode
        
        if incremental_mode:
            self._init_incremental_mode(storage_dir)
        
        if background_mode:
            self._init_background_mode()
    
    def _setup_session(self):
        """配置HTTP会话"""
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })
        
        http_proxy = os.getenv('RSS_HTTP_PROXY') or os.getenv('HTTP_PROXY')
        https_proxy = os.getenv('RSS_HTTPS_PROXY') or os.getenv('HTTPS_PROXY')
        
        if http_proxy or https_proxy:
            proxies = {}
            if http_proxy:
                proxies['http'] = http_proxy
            if https_proxy:
                proxies['https'] = https_proxy
            self.session.proxies.update(proxies)
            self.logger.info(f"RSS采集使用代理: {proxies}")
    
    def _init_incremental_mode(self, storage_dir: str = None):
        """初始化增量模式"""
        self.storage_dir = Path(storage_dir or project_root / "data" / "rss_cache")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.backup_dir = self.storage_dir / "backup"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.today_cache: Dict[str, CachedNewsItem] = {}
        self.today_file: Optional[Path] = None
        self.seen_ids: Set[str] = set()
        
        self._last_archive_date: Optional[str] = None
        
        self.stats = {
            'total_crawls': 0,
            'total_new_items': 0,
            'total_duplicates': 0,
            'last_crawl_time': None,
            'last_archive_time': None,
            'failed_sources': 0
        }
        
        self.failed_sources: Dict[str, int] = {}
        
        self._load_today_cache()
    
    def _init_background_mode(self):
        """初始化后台服务模式"""
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def _get_today_file(self) -> Path:
        """获取今天的缓存文件路径"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        return self.storage_dir / f"rss_cache_{date_str}.json"
    
    def _load_today_cache(self):
        """加载今天的缓存"""
        if not self.incremental_mode:
            return
        
        self.today_file = self._get_today_file()
        
        if self.today_file.exists():
            try:
                with open(self.today_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for item_data in data.get('items', []):
                    item = CachedNewsItem.from_dict(item_data)
                    self.today_cache[item.id] = item
                    self.seen_ids.add(item.id)
                
                self.stats['total_new_items'] = len(self.today_cache)
                self.logger.info(f"加载今日缓存: {len(self.today_cache)} 条")
                
            except Exception as e:
                self.logger.error(f"加载缓存失败: {e}")
    
    def _save_cache(self):
        """保存缓存到文件"""
        if not self.incremental_mode:
            return
        
        try:
            data = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'items': [item.to_dict() for item in self.today_cache.values()],
                'stats': self.stats
            }
            
            with open(self.today_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"保存缓存失败: {e}")
    
    def _generate_news_id(self, title: str, link: str, published: str = "") -> str:
        """生成新闻唯一ID"""
        content = f"{title}_{link}_{published}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _guess_domain(self, category: str) -> str:
        """根据分类猜测领域"""
        if not category:
            return '社会'
        
        category_lower = category.lower()
        
        domain_mapping = {
            '科技': '科技', 'tech': '科技', 'technology': '科技',
            '财经': '经济', 'finance': '经济', 'economy': '经济', 'business': '经济',
            '体育': '体育', 'sport': '体育', 'sports': '体育',
            '娱乐': '文化', 'entertainment': '文化',
            '国际': '政治', 'world': '政治',
            '军事': '军事', 'military': '军事',
            '时政': '政治', 'politics': '政治',
            '社会': '社会', 'society': '社会',
        }
        
        for key, domain in domain_mapping.items():
            if key in category_lower:
                return domain
        
        return '社会'
    
    def fetch_feed(
        self,
        source: RSSSource,
        timeout: int = 30,
        use_backup: bool = False
    ) -> Optional[RSSFeed]:
        """
        获取单个RSS源
        
        Args:
            source: RSS源配置
            timeout: 超时时间
            use_backup: 是否使用备份源
        
        Returns:
            RSSFeed对象，失败返回None
        """
        rss_url = source.rss_url_backup if use_backup else source.rss_url
        
        if not rss_url:
            if not use_backup and source.rss_url_backup:
                return self.fetch_feed(source, timeout, use_backup=True)
            return None
        
        try:
            self.logger.debug(f"获取RSS: {source.name}")
            
            response = self.session.get(rss_url, timeout=timeout)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            if 'charset' not in content_type.lower():
                response.encoding = response.apparent_encoding or 'utf-8'
            
            feed = self.parser.parse(response.text, source.name, source.type)
            
            if feed and feed.items:
                feed.source_name = source.name
                feed.source_type = source.type
                feed.used_backup = use_backup
                self._cache[source.name] = feed
                self._fetch_status[source.name] = {
                    "status": "success",
                    "items": len(feed.items),
                    "used_backup": use_backup
                }
                return feed
            else:
                if not use_backup and source.rss_url_backup:
                    return self.fetch_feed(source, timeout, use_backup=True)
                return None
            
        except Exception as e:
            self.logger.error(f"获取失败: {source.name} - {e}")
            self._fetch_status[source.name] = {
                "status": "failed",
                "error": str(e)
            }
            
            if not use_backup and source.rss_url_backup:
                self.logger.info(f"切换备份源: {source.name}")
                return self.fetch_feed(source, timeout, use_backup=True)
            
            return None
    
    def fetch_all(self, source_type: str = None) -> Dict[str, RSSFeed]:
        """
        获取所有RSS源
        
        Args:
            source_type: 源类型过滤 (domestic/international/None表示全部)
        
        Returns:
            源名称到RSSFeed的映射
        """
        results = {}
        
        if source_type:
            sources = self.source_manager.get_sources_by_type(source_type)
        else:
            sources = self.source_manager.get_enabled_sources()
        
        for source in sources:
            feed = self.fetch_feed(source)
            if feed:
                results[source.name] = feed
            time.sleep(0.5)
        
        return results
    
    def crawl_once(self) -> Dict:
        """
        执行一次增量抓取
        
        Returns:
            抓取结果统计
        """
        if not self.incremental_mode:
            self.logger.warning("增量模式未启用，使用 fetch_all() 代替")
            feeds = self.fetch_all()
            return {'success': True, 'feeds': len(feeds)}
        
        self.logger.info("=" * 60)
        self.logger.info(f"📡 增量抓取开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)
        
        start_time = time.time()
        new_items = 0
        duplicates = 0
        errors = 0
        
        sources = self.source_manager.get_enabled_sources()
        
        for source in sources:
            try:
                feed = self.fetch_feed(source)
                
                if not feed or not feed.items:
                    continue
                
                source_new = 0
                for item in feed.items:
                    news_id = self._generate_news_id(
                        item.title,
                        item.link,
                        item.pub_date.isoformat() if item.pub_date else ""
                    )
                    
                    if news_id in self.seen_ids:
                        duplicates += 1
                        continue
                    
                    cached_item = CachedNewsItem(
                        id=news_id,
                        title=item.title,
                        content=item.content or item.description or "",
                        link=item.link,
                        source=source.name,
                        published=item.pub_date.isoformat() if item.pub_date else "",
                        crawl_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        domain=self._guess_domain(item.category)
                    )
                    
                    self.today_cache[news_id] = cached_item
                    self.seen_ids.add(news_id)
                    new_items += 1
                    source_new += 1
                
                self.logger.info(f"  {source.name}: 新增 {source_new} 条")
                
            except Exception as e:
                self.logger.error(f"  {source.name}: 错误 - {e}")
                errors += 1
        
        self._save_cache()
        
        if new_items > 0:
            self._create_backup()
        
        elapsed = time.time() - start_time
        
        self.stats['total_crawls'] += 1
        self.stats['total_new_items'] += new_items
        self.stats['total_duplicates'] += duplicates
        self.stats['last_crawl_time'] = datetime.now().isoformat()
        
        result = {
            'success': True,
            'new_items': new_items,
            'duplicates': duplicates,
            'errors': errors,
            'total_cached': len(self.today_cache),
            'elapsed_seconds': round(elapsed, 2)
        }
        
        self.logger.info(f"✅ 抓取完成: 新增 {new_items}, 重复 {duplicates}, 总计 {len(self.today_cache)}")
        
        return result
    
    def _create_backup(self):
        """创建缓存备份"""
        if not self.today_cache:
            return
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f"backup_{timestamp}.json"
            
            data = {
                'timestamp': timestamp,
                'items': [item.to_dict() for item in self.today_cache.values()]
            }
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            
            self._cleanup_old_backups()
            
        except Exception as e:
            self.logger.error(f"备份失败: {e}")
    
    def _cleanup_old_backups(self, keep_days: int = 7):
        """清理旧备份"""
        try:
            cutoff = datetime.now() - timedelta(days=keep_days)
            
            for backup_file in self.backup_dir.glob("backup_*.json"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff:
                    backup_file.unlink()
                    
        except Exception as e:
            self.logger.error(f"清理备份失败: {e}")
    
    def start_background(self, interval: int = None):
        """
        启动后台定时抓取
        
        Args:
            interval: 抓取间隔（秒），默认1800（30分钟）
        """
        if not self.background_mode:
            self._init_background_mode()
            self.background_mode = True
        
        if self._running:
            self.logger.warning("抓取服务已在运行")
            return
        
        interval = interval or self.DEFAULT_INTERVAL
        self._running = True
        self._stop_event.clear()
        
        def _run_loop():
            self.logger.info(f"🚀 RSS增量抓取服务启动 (间隔: {interval}秒)")
            
            while not self._stop_event.is_set():
                try:
                    self.crawl_once()
                    self._check_and_archive()
                except Exception as e:
                    self.logger.error(f"抓取异常: {e}")
                
                for _ in range(interval):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
            
            self.logger.info("RSS增量抓取服务已停止")
        
        self._thread = threading.Thread(target=_run_loop, daemon=True)
        self._thread.start()
    
    def stop_background(self):
        """停止后台抓取"""
        if not self._running:
            return
        
        self._stop_event.set()
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=5)
        
        self._save_cache()
        self.logger.info("抓取服务已停止")
    
    def _check_and_archive(self):
        """检查并执行每日归档"""
        if not self.incremental_mode:
            return
        
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')
        
        if self._last_archive_date == current_date:
            return
        
        if current_time >= self.ARCHIVE_TIME:
            self.logger.info(f"🕛 执行每日归档 ({self.ARCHIVE_TIME})")
            archive_file = self.archive_yesterday()
            
            if archive_file:
                self._last_archive_date = current_date
                self.stats['last_archive_time'] = now.isoformat()
                
                self.today_cache.clear()
                self.seen_ids.clear()
                self._load_today_cache()
                
                self.logger.info("✅ 归档完成，缓存已重置")
    
    def archive_yesterday(self) -> Optional[Path]:
        """归档昨天的数据"""
        if not self.incremental_mode:
            return None
        
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_file = self.storage_dir / f"rss_cache_{yesterday}.json"
        
        if not yesterday_file.exists():
            self.logger.info(f"昨天无缓存文件: {yesterday}")
            return None
        
        archive_dir = self.storage_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        archive_file = archive_dir / f"rss_cache_{yesterday}_archived.json"
        
        try:
            import shutil
            shutil.copy2(str(yesterday_file), str(archive_file))
            
            with open(yesterday_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            summary_file = archive_dir / f"rss_summary_{yesterday}.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"RSS缓存归档 - {yesterday}\n")
                f.write("=" * 50 + "\n")
                f.write(f"总条目: {len(data.get('items', []))}\n")
                f.write(f"抓取次数: {data.get('stats', {}).get('total_crawls', 0)}\n")
                f.write(f"归档时间: {datetime.now().isoformat()}\n")
            
            self.logger.info(f"✅ 归档完成: {archive_file}")
            
            return archive_file
            
        except Exception as e:
            self.logger.error(f"归档失败: {e}")
            return None
    
    def get_today_news(self) -> List[CachedNewsItem]:
        """获取今天的所有新闻"""
        if not self.incremental_mode:
            return []
        return list(self.today_cache.values())
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        result = {
            'is_running': self._running if self.background_mode else False,
            'incremental_mode': self.incremental_mode,
            'background_mode': self.background_mode
        }
        
        if self.incremental_mode:
            result.update({
                **self.stats,
                'current_cache_size': len(self.today_cache),
                'cache_file': str(self.today_file),
                'failed_sources_count': len(self.failed_sources)
            })
        
        return result
    
    def get_fetch_report(self) -> str:
        """获取RSS采集状态报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("RSS采集状态报告")
        lines.append("=" * 60)
        lines.append("")
        
        success_count = 0
        failed_count = 0
        backup_count = 0
        total_items = 0
        
        for name, status in self._fetch_status.items():
            if status.get("status") == "success":
                success_count += 1
                total_items += status.get("items", 0)
                if status.get("used_backup"):
                    backup_count += 1
            else:
                failed_count += 1
        
        lines.append(f"成功源: {success_count}")
        lines.append(f"失败源: {failed_count}")
        lines.append(f"使用备份源: {backup_count}")
        lines.append(f"总新闻数: {total_items}")
        
        return "\n".join(lines)
    
    def close(self):
        """关闭资源"""
        self.stop_background()
        self.session.close()
        self.logger.info("RSS采集器已关闭")


def run_once():
    """执行一次抓取"""
    collector = UnifiedRSSCollector(incremental_mode=True)
    try:
        result = collector.crawl_once()
        return result
    finally:
        collector.close()


def run_daemon(interval: int = 1800):
    """运行守护进程"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    collector = UnifiedRSSCollector(incremental_mode=True, background_mode=True)
    shutdown_requested = False
    
    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        logging.info("收到退出信号，正在停止...")
        shutdown_requested = True
        collector.stop_background()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        collector.start_background(interval)
        
        max_runtime = 24 * 60 * 60
        start_time = time.time()
        
        while not shutdown_requested:
            time.sleep(1)
            if time.time() - start_time > max_runtime:
                logging.info("达到最大运行时间，自动退出")
                break
            
    except Exception as e:
        logging.error(f"守护进程异常: {e}")
    finally:
        collector.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="统一RSS采集器")
    parser.add_argument('--daemon', action='store_true', help='以守护进程方式运行')
    parser.add_argument('--interval', type=int, default=1800, help='抓取间隔(秒)')
    parser.add_argument('--once', action='store_true', help='只执行一次')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if args.daemon:
        run_daemon(args.interval)
    else:
        run_once()
