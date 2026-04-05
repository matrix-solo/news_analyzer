#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模块 - SQLite 数据存储（事务安全版）

改进点：
1. 使用事务保证原子性操作
2. FTS5全文搜索自动同步
3. 批量插入性能优化
4. N+1查询优化
5. 连接池支持
"""

import sqlite3
import json
import logging
import hashlib
import threading
import random
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NewsData:
    """新闻数据结构"""
    news_id: str
    title: str
    translated_title: Optional[str] = None
    link: Optional[str] = None
    source: Optional[str] = None
    source_name: Optional[str] = None
    pub_date: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    who: Optional[str] = None
    what: Optional[str] = None
    when_time: Optional[str] = None
    where_place: Optional[str] = None
    why: Optional[str] = None
    how: Optional[str] = None
    domain: Optional[str] = None
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    embedding: Optional[bytes] = None
    # 语义评分字段
    source_score: Optional[float] = None
    heat_score: Optional[float] = None
    influence_score: Optional[float] = None
    value_score: Optional[float] = None
    final_score: Optional[float] = None
    # 解析中间层扩展字段
    extraction_method: Optional[str] = None
    raw_item_json: Optional[str] = None
    raw_news_id: Optional[int] = None
    # 处理状态字段
    repair_count: int = 0
    combined_processing_status: Optional[str] = None
    validation_status: Optional[str] = None
    # P-01/P-02 修复：新增字段
    accuracy_score: Optional[float] = None
    original_summary: Optional[str] = None
    # P-03 修复：分类置信度
    classification_confidence: Optional[float] = None


class ConnectionPool:
    """SQLite连接池（线程安全）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = None, max_connections: int = 5):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = None, max_connections: int = 5):
        if self._initialized:
            return
        
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool = []
        self._pool_lock = threading.Lock()
        self._initialized = True
        
        # 初始化连接池
        for _ in range(max_connections):
            conn = self._create_connection()
            self._pool.append(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """创建新连接"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        # 启用外键支持
        conn.execute('PRAGMA foreign_keys = ON')
        # 启用WAL模式提高并发性能
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
        # 等待锁释放（减少 database is locked）
        conn.execute('PRAGMA busy_timeout = 5000')
        return conn
    
    @contextmanager
    def get_connection(self):
        """获取连接（上下文管理器）"""
        conn = None
        try:
            with self._pool_lock:
                if self._pool:
                    conn = self._pool.pop()
                else:
                    conn = self._create_connection()
            yield conn
        finally:
            if conn:
                with self._pool_lock:
                    if len(self._pool) < self.max_connections:
                        self._pool.append(conn)
                    else:
                        conn.close()


class NewsDatabase:
    """新闻数据库管理器（事务安全版）"""
    
    # SQL语句常量
    INSERT_NEWS_SQL = """
        INSERT INTO news (
            id, title, translated_title, link, source, source_name,
            pub_date, content, summary,
            who, what, when_time, where_place, why, how,
            domain, tags, keywords,
            source_score, heat_score, influence_score, value_score, final_score,
            extraction_method, raw_item_json, raw_news_id,
            embedding,
            repair_count, combined_processing_status, validation_status,
            accuracy_score, original_summary, classification_confidence
        ) VALUES (
            :news_id, :title, :translated_title, :link, :source, :source_name,
            :pub_date, :content, :summary,
            :who, :what, :when_time, :where_place, :why, :how,
            :domain, :tags, :keywords,
            :source_score, :heat_score, :influence_score, :value_score, :final_score,
            :extraction_method, :raw_item_json, :raw_news_id,
            :embedding,
            :repair_count, :combined_processing_status, :validation_status,
            :accuracy_score, :original_summary, :classification_confidence
        )
    """
    
    INSERT_PROCESSED_SQL = """
        INSERT OR IGNORE INTO processed_news (news_id, processed_at)
        VALUES (:news_id, :processed_at)
    """
    
    def __init__(self, db_path: str = None, use_pool: bool = True):
        if db_path is None:
            from core.config.loader import PROJECT_ROOT
            data_dir = Path(PROJECT_ROOT) / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "news.db"
        
        self.db_path = Path(db_path)
        self.use_pool = use_pool
        
        if use_pool:
            self._pool = ConnectionPool(str(self.db_path))
        
        self._init_database()

    def _execute_with_retry(
        self,
        conn: sqlite3.Connection,
        sql: str,
        params: Any = None,
        *,
        max_retries: int = 3,
        base_delay: float = 0.2,
    ):
        """
        写操作重试封装：处理 SQLite 锁竞争。
        仅用于 INSERT/UPDATE/DELETE 等写语句。
        """
        last_err = None
        for attempt in range(max_retries + 1):
            try:
                cur = conn.cursor()
                if params is None:
                    return cur.execute(sql)
                return cur.execute(sql, params)
            except sqlite3.OperationalError as e:
                last_err = e
                msg = str(e).lower()
                if "locked" not in msg and "busy" not in msg:
                    raise
                if attempt >= max_retries:
                    raise
                # 抖动退避，减少惊群
                delay = base_delay * (2 ** attempt) + random.uniform(0, base_delay)
                logger.warning(f"SQLite写入被锁，{delay:.2f}s后重试... ({attempt + 1}/{max_retries})")
                import time
                time.sleep(delay)
        raise last_err
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        if self.use_pool:
            with self._pool.get_connection() as conn:
                yield conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"事务回滚: {e}")
                raise
    
    def _init_database(self):
        """初始化数据库表结构和触发器"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 新闻表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    translated_title TEXT,
                    link TEXT,
                    source TEXT,
                    source_name TEXT,
                    pub_date DATETIME,
                    content TEXT,
                    summary TEXT,

                    who TEXT,
                    what TEXT,
                    when_time TEXT,
                    where_place TEXT,
                    why TEXT,
                    how TEXT,

                    domain TEXT,
                    tags TEXT,
                    keywords TEXT,

                    source_score REAL,
                    heat_score REAL,
                    influence_score REAL,
                    value_score REAL,
                    final_score REAL,

                    extraction_method TEXT DEFAULT 'unknown',
                    raw_item_json TEXT,
                    raw_news_id INTEGER,

                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pub_date ON news(pub_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON news(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON news(domain)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_final_score ON news(final_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON news(source)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_extraction_method ON news(extraction_method)')

            # 迁移：添加缺失字段（支持已有数据库升级）
            self._migrate_add_missing_columns(conn)

            # 去重基线表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_news (
                    news_id TEXT PRIMARY KEY,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_news(processed_at)')
            
            # 全文搜索虚拟表
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS news_fts USING fts5(
                    title,
                    translated_title,
                    content,
                    keywords,
                    tags,
                    content='news',
                    content_rowid='rowid'
                )
            ''')
            
            # 创建触发器自动同步FTS5
            self._create_fts_triggers(cursor)

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    snapshot_json TEXT NOT NULL,
                    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_context_date ON market_context(date)')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hotboard_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    hot_value INTEGER DEFAULT 0,
                    url TEXT,
                    embedding TEXT,
                    expires_at DATETIME,
                    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hotboard_platform ON hotboard_cache(platform)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hotboard_expires ON hotboard_cache(expires_at)')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS raw_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    news_id TEXT UNIQUE,
                    raw_json TEXT NOT NULL,
                    source_name TEXT,
                    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_news_fetched_at ON raw_news(fetched_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_news_processed ON raw_news(processed)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_news_source ON raw_news(source_name)')

            conn.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")

    def _migrate_add_missing_columns(self, conn):
        """迁移：添加缺失的字段以支持 force_stored 修复机制"""
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(news)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        migrations = [
            ('repair_count', 'INTEGER DEFAULT 0'),
            ('combined_processing_status', 'TEXT'),
            ('validation_status', 'TEXT'),
            ('accuracy_score', 'REAL'),
            ('original_summary', 'TEXT'),
            ('classification_confidence', 'REAL'),
        ]

        for col_name, col_type in migrations:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE news ADD COLUMN {col_name} {col_type}")
                    logger.info(f"数据库迁移：添加字段 {col_name}")
                except Exception as e:
                    logger.warning(f"添加字段 {col_name} 失败（可能已存在）: {e}")

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_repair_count ON news(repair_count)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_combined_status ON news(combined_processing_status)')

    def _create_fts_triggers(self, cursor):
        """创建FTS5同步触发器"""
        # INSERT触发器
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS news_fts_insert AFTER INSERT ON news
            BEGIN
                INSERT INTO news_fts(rowid, title, translated_title, content, keywords, tags)
                VALUES (new.rowid, new.title, new.translated_title, new.content, new.keywords, new.tags);
            END
        ''')
        
        # UPDATE触发器
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS news_fts_update AFTER UPDATE ON news
            BEGIN
                UPDATE news_fts SET
                    title = new.title,
                    translated_title = new.translated_title,
                    content = new.content,
                    keywords = new.keywords,
                    tags = new.tags
                WHERE rowid = old.rowid;
            END
        ''')
        
        # DELETE触发器
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS news_fts_delete AFTER DELETE ON news
            BEGIN
                DELETE FROM news_fts WHERE rowid = old.rowid;
            END
        ''')
    
    def insert_news_with_processed(self, news: NewsData) -> bool:
        """
        插入新闻并标记为已处理（原子操作）
        
        使用事务保证两个操作要么都成功，要么都失败
        """
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                # 检查是否已存在
                cursor.execute('SELECT 1 FROM news WHERE id = ?', (news.news_id,))
                if cursor.fetchone():
                    logger.debug(f"新闻已存在: {news.news_id}")
                    return False
                
                # 插入新闻
                news_dict = self._news_to_dict(news)
                self._execute_with_retry(conn, self.INSERT_NEWS_SQL, news_dict)
                
                # 标记为已处理
                self._execute_with_retry(conn, self.INSERT_PROCESSED_SQL, {
                    'news_id': news.news_id,
                    'processed_at': datetime.now().isoformat()
                })
                
                logger.debug(f"插入新闻成功: {news.news_id}")
                return True
                
        except sqlite3.IntegrityError as e:
            logger.warning(f"新闻已存在（完整性错误）: {news.news_id} - {e}")
            return False
        except Exception as e:
            logger.error(f"插入新闻失败: {e}")
            raise
    
    def insert_news_batch(self, news_list: List[NewsData]) -> int:
        """
        批量插入新闻（事务优化版）
        
        使用executemany提高性能，单事务处理
        """
        if not news_list:
            return 0
        
        success_count = 0
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                # 准备数据
                news_dicts = []
                processed_dicts = []
                now = datetime.now().isoformat()
                
                for news in news_list:
                    news_dict = self._news_to_dict(news)
                    news_dicts.append(news_dict)
                    processed_dicts.append({
                        'news_id': news.news_id,
                        'processed_at': now
                    })
                
                # 批量插入新闻
                # executemany 也可能触发锁竞争，这里简化为失败时整体重试
                for attempt in range(4):
                    try:
                        cursor.executemany(self.INSERT_NEWS_SQL, news_dicts)
                        break
                    except sqlite3.OperationalError as e:
                        msg = str(e).lower()
                        if ("locked" not in msg and "busy" not in msg) or attempt >= 3:
                            raise
                        import time
                        delay = 0.3 * (2 ** attempt) + random.uniform(0, 0.2)
                        logger.warning(f"批量写入被锁，{delay:.2f}s后重试... ({attempt + 1}/3)")
                        time.sleep(delay)
                success_count = cursor.rowcount
                
                # 批量标记为已处理
                cursor.executemany(self.INSERT_PROCESSED_SQL, processed_dicts)
                
                logger.info(f"批量插入新闻: {success_count}/{len(news_list)}")
                return success_count
                
        except Exception as e:
            logger.error(f"批量插入失败: {e}")
            raise

    def insert_raw_news_batch(self, raw_items: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        批量插入原始新闻数据
        
        Args:
            raw_items: 原始新闻列表，每项包含:
                - news_id: 新闻唯一标识
                - raw_json: 原始JSON字符串
                - source_name: 来源名称
        
        Returns:
            字典 {news_id: raw_news_id} 映射
        """
        if not raw_items:
            return {}
        
        id_mapping = {}
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                for item in raw_items:
                    try:
                        cursor.execute('''
                            INSERT INTO raw_news (news_id, raw_json, source_name, fetched_at, processed)
                            VALUES (?, ?, ?, ?, 0)
                        ''', (
                            item['news_id'],
                            item['raw_json'],
                            item.get('source_name'),
                            now
                        ))
                        id_mapping[item['news_id']] = cursor.lastrowid
                    except sqlite3.IntegrityError:
                        cursor.execute(
                            'SELECT id FROM raw_news WHERE news_id = ?',
                            (item['news_id'],)
                        )
                        row = cursor.fetchone()
                        if row:
                            id_mapping[item['news_id']] = row[0]
                
                logger.info(f"批量插入原始数据: {len(id_mapping)}/{len(raw_items)} 条")
                return id_mapping
                
        except Exception as e:
            logger.error(f"批量插入原始数据失败: {e}")
            raise

    def update_raw_news_processed(self, news_id: str, raw_news_id: int):
        """
        更新原始数据为已处理状态
        
        Args:
            news_id: 新闻ID
            raw_news_id: 原始数据ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE raw_news 
                    SET processed = 1, news_id = ?
                    WHERE id = ?
                ''', (news_id, raw_news_id))
                conn.commit()
        except Exception as e:
            logger.error(f"更新原始数据状态失败: {e}")

    def get_raw_news_by_id(self, raw_news_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取原始数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM raw_news WHERE id = ?', (raw_news_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取原始数据失败: {e}")
            return None

    def get_raw_news_by_news_id(self, news_id: str) -> Optional[Dict[str, Any]]:
        """根据news_id获取原始数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM raw_news WHERE news_id = ?', (news_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取原始数据失败: {e}")
            return None

    def get_unprocessed_raw_news(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取未处理的原始数据"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT * FROM raw_news WHERE processed = 0 ORDER BY fetched_at DESC LIMIT ?',
                    (limit,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取未处理原始数据失败: {e}")
            return []

    def cleanup_raw_news(self, days: int = 30) -> int:
        """清理指定天数前的已处理原始数据"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM raw_news WHERE processed = 1 AND fetched_at < ?',
                    (cutoff.isoformat(),)
                )
                deleted = cursor.rowcount
                conn.commit()
                if deleted > 0:
                    logger.info(f"清理原始数据: {deleted} 条")
                return deleted
        except Exception as e:
            logger.error(f"清理原始数据失败: {e}")
            return 0

    def backup_database(self, backup_dir: Optional[str] = None) -> Optional[str]:
        """
        使用 SQLite 在线备份 API 创建一致性备份。
        返回备份文件路径；失败返回 None。
        """
        project_root = Path(__file__).parent.parent
        backup_root = Path(backup_dir) if backup_dir else (project_root / "data" / "backups")
        backup_root.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = backup_root / f"news.db.backup_{ts}"

        try:
            with self.get_connection() as conn:
                dest_conn = sqlite3.connect(dest)
                try:
                    conn.backup(dest_conn)
                finally:
                    dest_conn.close()
            logger.info(f"数据库备份完成: {dest}")
            return str(dest)
        except Exception as e:
            logger.warning(f"数据库备份失败: {e}")
            return None
    
    def check_news_exists(self, news_id: str) -> bool:
        """检查新闻是否存在（优化版）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM news WHERE id = ? LIMIT 1', (news_id,))
            return cursor.fetchone() is not None
    
    def check_news_processed(self, news_id: str) -> bool:
        """检查新闻是否已处理（优化版）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM processed_news WHERE news_id = ? LIMIT 1', (news_id,))
            return cursor.fetchone() is not None
    
    def filter_processed_ids(self, news_ids: List[str]) -> Set[str]:
        """
        批量检查哪些ID已处理（优化N+1查询）
        
        一次性查询所有ID，返回已处理的ID集合
        """
        if not news_ids:
            return set()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 使用IN子句批量查询
            placeholders = ','.join('?' * len(news_ids))
            sql = f"SELECT news_id FROM processed_news WHERE news_id IN ({placeholders})"
            cursor.execute(sql, news_ids)
            return {row['news_id'] for row in cursor.fetchall()}
    
    def get_recent_news(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取最近N小时的新闻"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM news 
                WHERE pub_date >= datetime('now', ?)
                ORDER BY final_score DESC, pub_date DESC
            ''', (f'-{hours} hours',))
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def get_history_news(self, days: int = 90) -> List[Dict[str, Any]]:
        """获取最近N天的新闻（历史关联分析用）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM news 
                WHERE pub_date >= datetime('now', ?)
                ORDER BY pub_date DESC
            ''', (f'-{days} days',))
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def search_by_keywords(self, keywords: List[str], days: int = 90) -> List[Dict[str, Any]]:
        """关键词搜索（安全版）"""
        if not keywords:
            return []
        
        # 清理关键词，防止注入
        cleaned_keywords = []
        for kw in keywords:
            # 移除FTS5特殊字符
            cleaned = kw.replace("'", "").replace('"', "").replace("*", "").replace("-", " ")
            if cleaned.strip():
                cleaned_keywords.append(cleaned)
        
        if not cleaned_keywords:
            return []
        
        query = ' OR '.join(cleaned_keywords)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT n.* FROM news n
                JOIN news_fts fts ON n.rowid = fts.rowid
                WHERE news_fts MATCH ?
                AND n.pub_date >= datetime('now', ?)
                ORDER BY fts.rank
            ''', (query, f'-{days} days'))
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def search_by_domain(self, domain: str, hours: int = 24) -> List[Dict[str, Any]]:
        """按领域查询"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM news 
                WHERE domain = ?
                AND pub_date >= datetime('now', ?)
                ORDER BY final_score DESC
            ''', (domain, f'-{hours} hours'))
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM news')
            total_news = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM news WHERE pub_date >= datetime("now", "-24 hours")')
            recent_24h = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM news WHERE pub_date >= datetime("now", "-7 days")')
            recent_7d = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM news WHERE pub_date >= datetime("now", "-30 days")')
            recent_30d = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM processed_news')
            processed = cursor.fetchone()['count']
            
            cursor.execute('''
                SELECT domain, COUNT(*) as count 
                FROM news 
                WHERE domain IS NOT NULL
                GROUP BY domain 
                ORDER BY count DESC
            ''')
            by_domain = {row['domain']: row['count'] for row in cursor.fetchall()}
            
            return {
                'total_news': total_news,
                'recent_24h': recent_24h,
                'recent_7d': recent_7d,
                'recent_30d': recent_30d,
                'processed': processed,
                'by_domain': by_domain
            }

    def get_source_latest_pub_date(self, source_name: str) -> Optional[str]:
        """获取指定信源的最新新闻发布时间"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(pub_date) as latest_pub_date 
                FROM news 
                WHERE source_name = ?
            ''', (source_name,))
            row = cursor.fetchone()
            return row['latest_pub_date'] if row and row['latest_pub_date'] else None
    
    def _news_to_dict(self, news: NewsData) -> Dict[str, Any]:
        """将NewsData转换为字典"""
        embedding = news.embedding
        if embedding is not None:
            if isinstance(embedding, np.ndarray):
                embedding = embedding.astype(np.float32).tobytes()
            elif isinstance(embedding, list):
                embedding = np.array(embedding, dtype=np.float32).tobytes()

        return {
            'news_id': news.news_id,
            'title': news.title,
            'translated_title': news.translated_title,
            'link': news.link,
            'source': news.source,
            'source_name': news.source_name,
            'pub_date': news.pub_date,
            'content': news.content,
            'summary': news.summary,
            'who': news.who,
            'what': news.what,
            'when_time': news.when_time,
            'where_place': news.where_place,
            'why': news.why,
            'how': news.how,
            'domain': news.domain,
            'tags': json.dumps(news.tags, ensure_ascii=False) if news.tags else None,
            'keywords': json.dumps(news.keywords, ensure_ascii=False) if news.keywords else None,
            'source_score': news.source_score,
            'heat_score': news.heat_score,
            'influence_score': news.influence_score,
            'value_score': news.value_score,
            'final_score': news.final_score,
            'embedding': embedding,
            'extraction_method': news.extraction_method or 'unknown',
            'raw_item_json': news.raw_item_json,
            'raw_news_id': news.raw_news_id,
            'repair_count': news.repair_count,
            'combined_processing_status': news.combined_processing_status,
            'validation_status': news.validation_status,
            'accuracy_score': news.accuracy_score,
            'original_summary': news.original_summary,
            'classification_confidence': news.classification_confidence,
        }
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        news = dict(row)

        if 'id' in news and 'news_id' not in news:
            news['news_id'] = news['id']

        # 解析 JSON 字段
        if news.get('tags'):
            try:
                news['tags'] = json.loads(news['tags'])
            except (json.JSONDecodeError, TypeError):
                news['tags'] = []
        
        if news.get('keywords'):
            try:
                news['keywords'] = json.loads(news['keywords'])
            except (json.JSONDecodeError, TypeError):
                news['keywords'] = []
        
        return news

    def get_hotboard_stats(self) -> Dict[str, Any]:
        """获取热榜缓存状态"""
        from datetime import datetime
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM hotboard_cache')
            total = cursor.fetchone()['count']
            
            cursor.execute('SELECT MAX(fetched_at) as last_fetch FROM hotboard_cache')
            row = cursor.fetchone()
            last_fetch = row['last_fetch'] if row else None
            
            # 使用参数化查询，避免时间格式不一致的问题
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('SELECT COUNT(*) as count FROM hotboard_cache WHERE expires_at > ?', (now,))
            valid = cursor.fetchone()['count']
            
            return {
                'total': total,
                'valid': valid,
                'last_fetch': last_fetch,
                'is_valid': valid > 0
            }

    def get_hotboard_cache(self, include_embedding: bool = False) -> List[Dict[str, Any]]:
        """获取热榜缓存数据"""
        from datetime import datetime
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if include_embedding:
                cursor.execute('''
                    SELECT platform, rank, title, hot_value, url, embedding, fetched_at
                    FROM hotboard_cache 
                    WHERE expires_at > ?
                    ORDER BY platform, rank
                ''', (now,))
            else:
                cursor.execute('''
                    SELECT platform, rank, title, hot_value, url, fetched_at
                    FROM hotboard_cache 
                    WHERE expires_at > ?
                    ORDER BY platform, rank
                ''', (now,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def save_hotboard_cache(self, cache_data: List[Dict[str, Any]], ttl_hours: int = 6) -> int:
        """保存热榜缓存数据"""
        if not cache_data:
            return 0
        
        from datetime import datetime, timedelta
        
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM hotboard_cache')
                
                expires_at = (datetime.now() + timedelta(hours=ttl_hours)).strftime('%Y-%m-%d %H:%M:%S')
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                count = 0
                for item in cache_data:
                    cursor.execute('''
                        INSERT INTO hotboard_cache 
                        (platform, rank, title, hot_value, url, embedding, expires_at, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('platform', ''),
                        item.get('rank', 0),
                        item.get('title', ''),
                        item.get('hot_value', 0),
                        item.get('url', ''),
                        item.get('embedding'),
                        expires_at,
                        now
                    ))
                    count += 1
                
                logger.info(f"热榜缓存保存: {count} 条")
                return count
        except Exception as e:
            logger.error(f"热榜缓存保存失败: {e}")
            return 0

    def get_news_by_status(self, status: Optional[str]) -> List[Dict[str, Any]]:
        """获取指定状态的所有新闻，status=None 时查询 combined_processing_status 为 NULL 的记录"""
        with self.transaction() as conn:
            cursor = conn.cursor()
            if status is None:
                cursor.execute('''
                    SELECT * FROM news
                    WHERE combined_processing_status IS NULL
                    ORDER BY created_at DESC
                ''')
            else:
                cursor.execute('''
                    SELECT * FROM news
                    WHERE combined_processing_status = ?
                    ORDER BY created_at DESC
                ''', (status,))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def update_news(self, news_id: str, updates: Dict[str, Any]) -> bool:
        """更新单条新闻的指定字段"""
        if not updates:
            return False

        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [news_id]

        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE news SET {set_clause} WHERE id = ?
                ''', values)
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新新闻失败: {news_id}, error: {e}")
            return False


def get_db() -> NewsDatabase:
    """获取数据库实例（单例）"""
    return NewsDatabase()
