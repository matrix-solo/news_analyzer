#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单元测试 - 工具模块

测试范围：
- 文本处理工具
- 标签格式
- JSON解析
"""

import os

import sys

import pytest

from pathlib import Path

from datetime import datetime

from unittest.mock import Mock, patch, MagicMock

project_root = Path(__file__).parent.parent.parent

sys.path.insert(0, str(project_root))

from core.utils.text_utils import get_news_title, format_tags, parse_json_str


class TestGetNewsTitle:
    """获取新闻标题测试"""

    def test_get_translated_title(self):
        """测试获取翻译标题"""
        news = {
            'translated_title': '翻译后的标题',
            'title': 'Original Title'
        }
        result = get_news_title(news)
        assert result == '翻译后的标题'

    def test_get_original_title(self):
        """测试获取原始标题"""
        news = {
            'title': 'Original Title'
        }
        result = get_news_title(news)
        assert result == 'Original Title'

    def test_get_title_with_fallback(self):
        """测试标题回退"""
        news = {}
        result = get_news_title(news)
        assert result == ''


class TestFormatTags:
    """格式化标签测试"""

    def test_format_tags_list(self):
        """测试格式化标签列表"""
        tags = ['政治', '国际', '中东']
        result = format_tags(tags)
        assert result == '政治, 国际, 中东'

    def test_format_tags_string(self):
        """测试格式化标签字符串"""
        tags = '政治,国际,中东'
        result = format_tags(tags)
        assert result == '政治,国际,中东'

    def test_format_tags_empty(self):
        """测试空标签"""
        result = format_tags([])
        assert result == ''
        result = format_tags('')
        assert result == ''

    def test_format_tags_none(self):
        """测试None标签"""
        result = format_tags(None)
        assert result == ''


class TestParseJsonStr:
    """解析JSON字符串测试"""

    def test_parse_valid_json(self):
        """测试解析有效JSON"""
        json_str = '{"key": "value", "number": 42}'
        result = parse_json_str(json_str)
        assert result == {"key": "value", "number": 42}

    def test_parse_invalid_json(self):
        """测试解析无效JSON"""
        json_str = 'not a valid json'
        result = parse_json_str(json_str)
        assert isinstance(result, dict)

    def test_parse_empty_string(self):
        """测试解析空字符串"""
        result = parse_json_str('')
        assert isinstance(result, dict)


class TestTextUtilsIntegration:
    """文本工具集成测试"""

    def test_full_text_pipeline(self):
        """测试完整文本处理流程"""
        news = {
            'title': '测试标题',
            'translated_title': 'Test Title',
            'tags': '["政治", "国际"]'
        }

        title = get_news_title(news)
        assert title == 'Test Title'

        tags = parse_json_str(news['tags'])
        assert tags == ["政治", "国际"]

        formatted_tags = format_tags(tags)
        assert formatted_tags == '政治, 国际'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
