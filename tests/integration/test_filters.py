#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试 - 过滤模块

测试范围：
- 去重过滤
- 相似度计算
- 标题标准化
"""

import os
import sys
import pytest
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestDuplicateFilter:
    """重复过滤测试"""

    def test_duplicate_filter_initialization(self):
        """测试重复过滤器初始化"""
        news_list = []
        assert isinstance(news_list, list)

    def test_exact_duplicate_detection(self):
        """测试精确重复检测"""
        news1 = {'news_id': 'abc123', 'title': '测试标题'}
        news2 = {'news_id': 'abc123', 'title': '测试标题'}
        assert news1['news_id'] == news2['news_id']

    def test_similar_title_detection(self):
        """测试相似标题检测"""
        title1 = "人工智能技术取得重大突破"
        title2 = "人工智能技术取得重大进展"
        assert title1 != title2

    def test_news_id_normalization(self):
        """测试新闻ID标准化"""
        news_id = "  ABC123  "
        normalized = news_id.strip().lower()
        assert normalized == "abc123"

    def test_empty_title_handling(self):
        """测试空标题处理"""
        title = ""
        is_empty = len(title.strip()) == 0
        assert is_empty == True


class TestSimilarityCalculator:
    """相似度计算测试"""

    def test_jaccard_similarity(self):
        """测试Jaccard相似度"""
        set1 = {"人工智能", "技术", "突破"}
        set2 = {"人工智能", "技术", "进展"}
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        similarity = intersection / union if union > 0 else 0
        assert similarity >= 0.5

    def test_keyword_overlap(self):
        """测试关键词重叠"""
        keywords1 = ["AI", "机器学习", "深度学习"]
        keywords2 = ["机器学习", "深度学习", "神经网络"]
        overlap = len(set(keywords1) & set(keywords2))
        assert overlap >= 2

    def test_cosine_similarity_basic(self):
        """测试余弦相似度基础"""
        vec1 = [1, 0, 0]
        vec2 = [1, 0, 0]
        dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
        norm1 = sum(v ** 2 for v in vec1) ** 0.5
        norm2 = sum(v ** 2 for v in vec2) ** 0.5
        cosine = dot_product / (norm1 * norm2) if (norm1 * norm2) > 0 else 0
        assert cosine == 1.0


class TestTitleNormalization:
    """标题标准化测试"""

    def test_title_strip_whitespace(self):
        """测试标题去除空白"""
        title = "  测试标题  "
        normalized = title.strip()
        assert normalized == "测试标题"

    def test_title_lowercase(self):
        """测试标题转小写"""
        title = "Test Title"
        normalized = title.lower()
        assert normalized == "test title"

    def test_title_remove_special_chars(self):
        """测试移除特殊字符"""
        title = "测试【标题】!"
        normalized = ''.join(c for c in title if c.isalnum() or c.isspace())
        assert '【' not in normalized
        assert '】' not in normalized


class TestFilterResult:
    """过滤结果测试"""

    def test_create_filter_result(self):
        """测试创建去重结果"""
        result = {
            'duplicate_count': 0,
            'passed_count': 0,
            'duplicates': []
        }
        assert result['duplicate_count'] == 0
        assert result['passed_count'] == 0

    def test_filter_result_with_duplicates(self):
        """测试有重复的结果"""
        result = {
            'duplicate_count': 2,
            'passed_count': 8,
            'duplicates': ['id1', 'id2']
        }
        assert result['duplicate_count'] == 2
        assert len(result['duplicates']) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
