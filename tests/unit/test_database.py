#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单元测试 - 数据库模块

测试范围：
- 数据库初始化
- 新闻插入和去重
- 批量操作
- 并发写入
- 查询功能

注意：由于NewsDatabase ConnectionPool 使用单例模式，测试需要彻底重置单例状态以确保隔离
"""

import os

import sys

import pytest

import tempfile

import threading

import gc

from pathlib import Path

from datetime import datetime

project_root = Path(__file__).parent.parent.parent

sys.path.insert(0, str(project_root))

def reset_database_singleton():
    """彻底重置数据库单例状态"""
    from core.storage import database as db_module

    if hasattr(db_module, 'NewsDatabase'):

        db_module.NewsDatabase._instance = None

        db_module.NewsDatabase._initialized = False

    if hasattr(db_module, 'ConnectionPool'):

        db_module.ConnectionPool._instance = None

        db_module.ConnectionPool._initialized = False

    gc.collect()

@pytest.fixture

def isolated_db():

    """创建完全隔离的临时数据库"""

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:

        db_path = f.name

    reset_database_singleton()

    from core.storage.database import NewsDatabase, NewsData

    db = NewsDatabase(db_path)

    try:

        yield db

    finally:

        try:

            if hasattr(db, '_NewsDatabase__conn') and db._NewsDatabase__conn:

                db._NewsDatabase__conn.close()

        except:

            pass

        try:

            if hasattr(db, '_pool') and db._pool:

                for conn in db._pool._pool:

                    try:

                        conn.close()

                    except:

                        pass

        except:

            pass

        gc.collect()

        for ext in ['', '-wal', '-shm']:

            file_path = db_path + ext

            if os.path.exists(file_path):

                try:

                    os.unlink(file_path)

                except:

                    pass

        reset_database_singleton()

class TestNewsDatabase:

    """数据库模块测试"""

    def test_database_initialization(self, isolated_db):

        """测试数据库初始化"""

        stats = isolated_db.get_stats()

        assert stats['total_news'] == 0

        assert stats['recent_24h'] == 0

    def test_insert_news(self, isolated_db):

        """测试插入新闻"""

        from core.storage.database import NewsData

        news = NewsData(

            news_id='test_001',

            title='测试新闻标题',

            translated_title='Test News Title',

            link='https://example.com/news/001',

            source='test',

            source_name='测试来源',

            pub_date='2026-03-10T10:00:00',

            content='这是测试新闻内容',

            summary='测试摘要',

            domain='政治',

            score=85.0

        )

        result = isolated_db.insert_news_with_processed(news)

        assert result == True

        stats = isolated_db.get_stats()

        assert stats['total_news'] == 1

    def test_insert_duplicate_news(self, isolated_db):

        """测试插入重复新闻"""

        from core.storage.database import NewsData

        news = NewsData(

            news_id='test_dup_001',

            title='重复新闻',

            link='https://example.com/news/dup',

            source='test',

            source_name='测试来源',

            pub_date='2026-03-10T10:00:00',

            score=80.0

        )

        result1 = isolated_db.insert_news_with_processed(news)

        assert result1 == True

        result2 = isolated_db.insert_news_with_processed(news)

        assert result2 == False

        stats = isolated_db.get_stats()

        assert stats['total_news'] == 1

    def test_batch_insert(self, isolated_db):

        """测试批量插入"""

        from core.storage.database import NewsData

        news_list = [

            NewsData(

                news_id=f'test_batch_{i}',

                title=f'批量测试新闻{i}',

                link=f'https://example.com/news/batch/{i}',

                source='test',

                source_name='测试来源',

                pub_date='2026-03-10T10:00:00',

                score=70.0 + i

            )

            for i in range(10)

        ]

        count = isolated_db.insert_news_batch(news_list)

        assert count == 10

        stats = isolated_db.get_stats()

        assert stats['total_news'] == 10

    def test_filter_processed_ids(self, isolated_db):

        """测试批量去重查询"""

        from core.storage.database import NewsData

        news_list = [

            NewsData(

                news_id=f'test_filter_{i}',

                title=f'过滤测试{i}',

                link=f'https://example.com/filter/{i}',

                source='test',

                source_name='测试来源',

                pub_date='2026-03-10T10:00:00',

                score=70.0

            )

            for i in range(5)

        ]

        isolated_db.insert_news_batch(news_list)

        all_ids = [f'test_filter_{i}' for i in range(10)]

        processed = isolated_db.filter_processed_ids(all_ids)

        assert len(processed) == 5

        for i in range(5):

            assert f'test_filter_{i}' in processed

    def test_get_recent_news(self, isolated_db):

        """测试获取最近新闻"""

        from core.storage.database import NewsData

        news = NewsData(

            news_id='test_recent_001',

            title='最近新闻',

            link='https://example.com/recent/001',

            source='test',

            source_name='测试来源',

            pub_date=datetime.now().isoformat(),

            score=90.0

        )

        isolated_db.insert_news_with_processed(news)

        recent = isolated_db.get_recent_news(hours=24)

        assert len(recent) == 1

        assert recent[0]['id'] == 'test_recent_001'

    def test_concurrent_insert(self, isolated_db):

        """测试并发写入"""

        from core.storage.database import NewsData

        results = []

        def insert_news(thread_id):

            try:

                news = NewsData(

                    news_id=f'test_concurrent_{thread_id}',

                    title=f'并发测试{thread_id}',

                    link=f'https://example.com/concurrent/{thread_id}',

                    source='test',

                    source_name='测试来源',

                    pub_date=datetime.now().isoformat(),

                    score=70.0

                )

                result = isolated_db.insert_news_with_processed(news)

                results.append(result)

            except Exception as e:

                results.append(False)

        threads = []

        for i in range(5):

            t = threading.Thread(target=insert_news, args=(i,))

            threads.append(t)

            t.start()

        for t in threads:

            t.join()

        assert sum(results) >= 3

        stats = isolated_db.get_stats()

        assert stats['total_news'] >= 3

class TestNewsData:

    """NewsData 数据结构测试"""

    def test_news_data_creation(self):

        """测试 NewsData 创建"""

        from core.storage.database import NewsData

        news = NewsData(

            news_id='test_001',

            title='测试标题',

            score=85.0

        )

        assert news.news_id == 'test_001'

        assert news.title == '测试标题'

        assert news.score == 85.0

        assert news.translated_title is None

        assert news.tags is None

    def test_news_data_with_all_fields(self):

        """测试 NewsData 完整字段"""

        from core.storage.database import NewsData

        news = NewsData(

            news_id='test_002',

            title='完整测试',

            translated_title='Full Test',

            link='https://example.com/full',

            source='test',

            source_name='测试来源',

            pub_date='2026-03-10T10:00:00',

            content='完整内容',

            summary='完整摘要',

            domain='科技',

            score=90.0,

            tags=['AI', '科技'],

            who='测试人物',

            what='测试内容',

            when_time='2026-03-10',

            where_place='北京',

            why='测试目的',

            how='测试方法'

        )

        assert news.news_id == 'test_002'

        assert news.domain == '科技'

        assert news.tags == ['AI', '科技']

        assert news.who == '测试人物'

if __name__ == '__main__':

    pytest.main([__file__, '-v'])
