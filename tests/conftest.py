#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Pytest 全局配置文件

功能:

1. 设置测试环境变量

2. 提供全局 fixtures

3. 配置测试标记

4. 配置日志输出

"""

import os

import sys

import pytest

import tempfile

import logging

from pathlib import Path

from typing import Dict, Any, List, Generator

project_root = Path(__file__).parent.parent

sys.path.insert(0, str(project_root))

os.environ['TEST_MODE'] = 'true'

os.environ['DEEPSEEK_API_KEY'] = 'test-deepseek-key-for-testing'

os.environ['DOUBAO_API_KEY'] = 'test-doubao-key-for-testing'

os.environ['QWEN_API_KEY'] = 'test-qwen-key-for-testing'

def pytest_configure(config):

    """Pytest 配置钩子"""

    config.addinivalue_line(

        "markers", "unit: 单元测试(快速、隔离、无外部依赖)"

    )

    config.addinivalue_line(

        "markers", "integration: 集成测试(需要外部资源或服务)"

    )

    config.addinivalue_line(

        "markers", "e2e: 端到端测试(完整流程测试)"

    )

    config.addinivalue_line(

        "markers", "slow: 慢速测试(运行时间 > 5秒)"

    )

    config.addinivalue_line(

        "markers", "requires_api: 需要API 密钥的测试"

    )

@pytest.fixture(scope="session")

def test_logger():

    """测试日志记录器"""

    logger = logging.getLogger("test")

    logger.setLevel(logging.DEBUG)

    return logger

@pytest.fixture

def temp_dir(tmp_path) -> Path:

    """临时目录"""

    return tmp_path

@pytest.fixture

def temp_db_path(tmp_path) -> str:

    """临时数据库路径"""

    return str(tmp_path / "test_news.db")

@pytest.fixture

def isolated_db(temp_db_path):

    """完全隔离的数据库实例"""

    from core.storage.database import NewsDatabase, NewsData

    NewsDatabase._instance = None

    NewsDatabase._initialized = False

    db = NewsDatabase(temp_db_path)

    try:

        yield db

    finally:

        try:

            if hasattr(db, '_NewsDatabase__conn') and db._NewsDatabase__conn:

                db._NewsDatabase__conn.close()

        except:

            pass

        import gc

        gc.collect()

        for ext in ['', '-wal', '-shm']:

            file_path = temp_db_path + ext

            if os.path.exists(file_path):

                try:

                    os.unlink(file_path)

                except:

                    pass

        NewsDatabase._instance = None

        NewsDatabase._initialized = False

@pytest.fixture

def sample_news() -> Dict[str, Any]:

    """示例新闻数据"""

    return {

        'id': 'test_001',

        'title': 'Test News Title',

        'translated_title': '测试新闻标题',

        'content': 'This is test content for the news article. It contains multiple sentences for testing purposes.',

        'domain': '政治',

        'source_name': '路透社',

        'source_type': 'international',

        'pub_date': '2026-03-10',

        'link': 'https://example.com/news/001',

        'fact_check': {

            'is_factual': True,

            'w5h1_analysis': {

                'what': '测试事件',

                'who': '测试人物',

                'when': '2026 年 3 月 10 日',

                'where': '测试地点',

                'why': '测试原因',

                'how': '测试方式'

            },

            'confidence': 0.9

        }

    }

@pytest.fixture

def sample_news_list() -> List[Dict[str, Any]]:

    """示例新闻列表"""

    return [

        {

            'id': '001',

            'title': 'Political News',

            'translated_title': '政治新闻',

            'content': '政治新闻内容,包含多个句子用于测试',

            'domain': '政治',

            'source_name': '路透社',

            'pub_date': '2026-03-10',

            'link': 'https://example.com/news/001'

        },

        {

            'id': '002',

            'title': 'Economic News',

            'translated_title': '经济新闻',

            'content': '经济新闻内容,包含多个句子用于测试',

            'domain': '经济',

            'source_name': '新华社',

            'pub_date': '2026-03-10',

            'link': 'https://example.com/news/002'

        },

        {

            'id': '003',

            'title': 'Tech News',

            'translated_title': '科技新闻',

            'content': '科技新闻内容,包含多个句子用于测试',

            'domain': '科技',

            'source_name': 'BBC',

            'pub_date': '2026-03-10',

            'link': 'https://example.com/news/003'

        }

    ]

@pytest.fixture

def mock_env(monkeypatch):

    """模拟环境变量"""

    monkeypatch.setenv('AI_FILTER_PROVIDER', 'doubao')

    monkeypatch.setenv('AI_FILTER_MODEL', 'test-model')

    monkeypatch.setenv('AI_FILTER_KEY', 'test-api-key')

    monkeypatch.setenv('AI_FILTER_BASE_URL', 'https://test.api.com/v1')

@pytest.fixture

def mock_ai_response() -> Dict[str, Any]:

    """模拟 AI 响应"""

    return {

        'is_factual': True,

        'content_type': 'news',

        'w5h1_score': 5,

        'w5h1_analysis': {

            'what': '测试事件',

            'who': '测试人物',

            'when': '2026 年 3 月 10 日',

            'where': '测试地点',

            'why': '测试原因',

            'how': '测试方式'

        },

        'confidence': 0.9,

        'domain': '政治',

        'translated_title': '翻译后的标题',

        'translated_content': '翻译后的内容',

        'short_summary': '这是简短摘要'

    }

@pytest.fixture

def rss_sample_entry() -> Dict[str, Any]:

    """RSS 示例条目"""

    return {

        'title': 'Breaking News: Test Event',

        'link': 'https://example.com/breaking/001',

        'published': 'Tue, 10 Mar 2026 10:00:00 GMT',

        'summary': 'This is a summary of the breaking news.',

        'source': 'Reuters'

    }

@pytest.fixture

def rss_sample_feed():

    """RSS 示例 Feed"""

    class MockFeed:

        def __init__(self):

            self.entries = [

                type('Entry', (), {

                    'title': 'Test Entry 1',

                    'link': 'https://example.com/1',

                    'published': 'Tue, 10 Mar 2026 10:00:00 GMT',

                    'summary': 'Summary 1'

                })(),

                type('Entry', (), {

                    'title': 'Test Entry 2',

                    'link': 'https://example.com/2',

                    'published': 'Tue, 10 Mar 2026 11:00:00 GMT',

                    'summary': 'Summary 2'

                })()

            ]

            self.feed = type('Feed', (), {

                'title': 'Test Feed',

                'link': 'https://example.com/feed'

            })()

    return MockFeed()

@pytest.fixture(scope="session")

def fixtures_dir() -> Path:

    """Fixtures 目录路径"""

    return Path(__file__).parent / "fixtures"

def pytest_collection_modifyitems(config, items):

    """根据测试文件位置自动添加标记"""

    for item in items:

        test_path = Path(item.fspath)

        if "unit" in str(test_path):

            item.add_marker(pytest.mark.unit)

        elif "integration" in str(test_path):

            item.add_marker(pytest.mark.integration)

        elif "e2e" in str(test_path):

            item.add_marker(pytest.mark.e2e)
