#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试 - Step 8 热度评分模块

测试范围：
- 热度评分计算
- 热榜匹配
- 降级策略
- 批量处理
"""

import os
import sys
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.processor.heat_processor import (
    HeatProcessor,
    _score_from_matches,
    _keyword_heat,
    _SIM_THRESHOLD
)


class TestHeatProcessor:
    """热度处理器测试"""

    @pytest.fixture
    def processor(self):
        """创建处理器实例"""
        return HeatProcessor()


class TestScoreCalculation(TestHeatProcessor):
    """评分计算测试"""

    def test_score_no_match(self):
        """测试无匹配评分"""
        platform_sims = {}
        score = _score_from_matches(platform_sims)
        assert score == 0

    def test_score_single_platform_85(self):
        """测试单平台匹配0.85评分"""
        platform_sims = {'weibo': 0.85}
        score = _score_from_matches(platform_sims)
        assert score == 4

    def test_score_single_platform_90(self):
        """测试单平台匹配0.90评分"""
        platform_sims = {'weibo': 0.91}
        score = _score_from_matches(platform_sims)
        assert score == 5

    def test_score_single_platform_high(self):
        """测试单平台高相似度评分"""
        platform_sims = {'weibo': 0.95}
        score = _score_from_matches(platform_sims)
        assert score == 5

    def test_score_two_platforms(self):
        """测试两平台匹配评分"""
        platform_sims = {'weibo': 0.90, 'zhihu': 0.88}
        score = _score_from_matches(platform_sims)
        assert score == 7

    def test_score_three_platforms(self):
        """测试三平台匹配评分"""
        platform_sims = {'weibo': 0.90, 'zhihu': 0.88, 'douyin': 0.86}
        score = _score_from_matches(platform_sims)
        assert score == 8

    def test_score_four_platforms(self):
        """测试四平台匹配评分"""
        platform_sims = {'weibo': 0.90, 'zhihu': 0.88, 'douyin': 0.86, 'bilibili': 0.85}
        score = _score_from_matches(platform_sims)
        assert score >= 9


class TestKeywordHeat(TestHeatProcessor):
    """关键词热度测试"""

    def test_keyword_heat_basic(self):
        """测试关键词热度基本功能"""
        text = "AI 人工智能 突破"
        score = _keyword_heat(text)
        assert score >= 0

    def test_keyword_heat_empty(self):
        """测试空文本热度"""
        score = _keyword_heat("")
        assert score == 0

    def test_keyword_heat_no_match(self):
        """测试无关键词匹配"""
        score = _keyword_heat("完全不相关的文本内容")
        assert score >= 0


class TestSimThreshold(TestHeatProcessor):
    """相似度阈值测试"""

    def test_sim_threshold_value(self):
        """测试阈值配置"""
        assert _SIM_THRESHOLD == 0.85


class TestCalculateHeatScore(TestHeatProcessor):
    """计算热度评分测试"""

    def test_calculate_heat_score_method_exists(self, processor):
        """测试方法存在"""
        assert hasattr(processor, 'calculate_heat_score')

    def test_calculate_heat_score_returns_int(self, processor):
        """测试返回整数"""
        news = {
            'news_id': 'test123',
            'title': '测试新闻标题'
        }
        score = processor.calculate_heat_score(news)
        assert isinstance(score, int)

    def test_calculate_heat_score_in_range(self, processor):
        """测试评分在有效范围内"""
        news = {
            'news_id': 'test123',
            'title': '测试新闻标题'
        }
        score = processor.calculate_heat_score(news)
        assert 0 <= score <= 10


class TestBatchProcessing(TestHeatProcessor):
    """批量处理测试"""

    def test_calculate_batch_method_exists(self, processor):
        """测试批量方法存在"""
        assert hasattr(processor, 'calculate_batch')

    def test_calculate_batch_returns_list(self, processor):
        """测试批量返回列表"""
        news_list = [
            {'news_id': 'n1', 'title': '新闻1'},
            {'news_id': 'n2', 'title': '新闻2'},
        ]
        scores = processor.calculate_batch(news_list)
        assert isinstance(scores, list)
        assert len(scores) == len(news_list)

    def test_calculate_batch_all_ints(self, processor):
        """测试批量返回全是整数"""
        news_list = [
            {'news_id': 'n1', 'title': '新闻1'},
            {'news_id': 'n2', 'title': '新闻2'},
        ]
        scores = processor.calculate_batch(news_list)
        assert all(isinstance(s, int) for s in scores)


class TestProcessorBuild(TestHeatProcessor):
    """处理器构建测试"""

    def test_is_built_initially_false(self, processor):
        """测试初始状态未构建"""
        assert processor.is_built() == False

    def test_build_with_empty_list(self, processor):
        """测试空列表构建"""
        processor.build([])
        assert processor.is_built() == True


class TestNewsWithEmbedding(TestHeatProcessor):
    """带embedding的新闻测试"""

    def test_news_with_embedding(self, processor):
        """测试带embedding的新闻"""
        embedding = np.random.randn(1024).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        news = {
            'news_id': 'test123',
            'title': '测试新闻',
            'embedding': embedding.tobytes()
        }
        score = processor.calculate_heat_score(news)
        assert isinstance(score, int)


class TestFallback(TestHeatProcessor):
    """降级策略测试"""

    def test_fallback_returns_int(self, processor):
        """测试降级返回整数"""
        news = {'news_id': 'test', 'title': '测试'}
        score = processor._fallback(news)
        assert isinstance(score, int)

    def test_fallback_with_empty_title(self, processor):
        """测试空标题降级"""
        news = {'news_id': 'test', 'title': ''}
        score = processor._fallback(news)
        assert isinstance(score, int)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
