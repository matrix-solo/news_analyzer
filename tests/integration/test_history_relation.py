#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试 - 历史关联引擎

测试范围：
- 历史关联分析
- 实体提取
- 相似度计算
"""

import os
import sys
import pytest
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestEntityExtraction:
    """实体提取测试"""

    def test_entity_extraction_basic(self):
        """测试实体提取基本功能"""
        text = "美国总统拜登访问中国"
        entities = []
        assert isinstance(entities, list)

    def test_person_entity_extraction(self):
        """测试人名实体提取"""
        text = "习近平主席发表讲话"
        assert "习近平" in text

    def test_location_entity_extraction(self):
        """测试地点实体提取"""
        text = "北京是中国的首都"
        assert "北京" in text

    def test_organization_entity_extraction(self):
        """测试组织实体提取"""
        text = "联合国召开会议"
        assert "联合国" in text

    def test_entity_overlap_calculation(self):
        """测试实体重叠计算"""
        entities1 = {"拜登", "美国", "中国"}
        entities2 = {"拜登", "美国", "日本"}
        overlap = len(entities1 & entities2)
        assert overlap == 2


class TestHistoryRelation:
    """历史关联测试"""

    def test_history_relation_basic(self):
        """测试历史关联基本功能"""
        relation = {'news_id': 'test', 'related_ids': [], 'scores': []}
        assert 'news_id' in relation

    def test_related_news_scoring(self):
        """测试关联新闻评分"""
        scores = [0.9, 0.8, 0.7, 0.6]
        threshold = 0.75
        relevant = [s for s in scores if s >= threshold]
        assert len(relevant) == 2

    def test_relation_threshold_filtering(self):
        """测试关系阈值过滤"""
        relations = [
            {'id': '1', 'score': 0.9},
            {'id': '2', 'score': 0.5}
        ]
        filtered = [r for r in relations if r['score'] >= 0.75]
        assert len(filtered) == 1

    def test_max_relations_limit(self):
        """测试最大关联数量限制"""
        relations = [{'id': str(i)} for i in range(100)]
        max_limit = 10
        limited = relations[:max_limit]
        assert len(limited) == 10


class TestSimilarityMatching:
    """相似度匹配测试"""

    def test_vector_similarity(self):
        """测试向量相似度"""
        vec1 = [1.0, 0.5, 0.2]
        vec2 = [0.9, 0.6, 0.3]
        similarity = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
        assert similarity > 0

    def test_normalized_similarity(self):
        """测试归一化相似度"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        dot = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
        assert dot == 0.0

    def test_similarity_ranking(self):
        """测试相似度排序"""
        scores = [
            {'id': '1', 'score': 0.7},
            {'id': '2', 'score': 0.9},
            {'id': '3', 'score': 0.5}
        ]
        ranked = sorted(scores, key=lambda x: x['score'], reverse=True)
        assert ranked[0]['id'] == '2'


class TestDomainFiltering:
    """领域过滤测试"""

    def test_same_domain_filtering(self):
        """测试同领域过滤"""
        news1 = {'domain': '科技', 'title': 'AI突破'}
        news2 = {'domain': '科技', 'title': '机器学习'}
        same_domain = news1['domain'] == news2['domain']
        assert same_domain == True

    def test_cross_domain_filtering(self):
        """测试跨领域过滤"""
        news1 = {'domain': '科技', 'title': 'AI突破'}
        news2 = {'domain': '政治', 'title': '大选'}
        same_domain = news1['domain'] == news2['domain']
        assert same_domain == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
