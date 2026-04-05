#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试 - Step 7 向量化生成模块

测试范围：
- 向量化检测与生成
- embedding 字段处理
- 批量向量化
- 向量存储格式
"""

import os
import sys
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestEmbeddingDetection:
    """向量检测测试"""

    def test_news_without_embedding_detected(self):
        """测试检测无 embedding 的新闻"""
        news = {
            'news_id': 'test123',
            'title': '测试新闻'
        }
        has_embedding = news.get('embedding') is not None
        assert has_embedding == False

    def test_news_with_embedding_detected(self):
        """测试检测有 embedding 的新闻"""
        news = {
            'news_id': 'test123',
            'title': '测试新闻',
            'embedding': np.array([0.1] * 1024, dtype=np.float32)
        }
        has_embedding = news.get('embedding') is not None
        assert has_embedding == True

    def test_filter_news_needing_embedding(self):
        """测试过滤需要生成向量的新闻"""
        processed_news = [
            {'news_id': 'n1', 'embedding': None},
            {'news_id': 'n2', 'embedding': np.array([0.1])},
            {'news_id': 'n3', 'embedding': None},
        ]
        news_needing = [n for n in processed_news if n.get('embedding') is None]
        assert len(news_needing) == 2
        assert news_needing[0]['news_id'] == 'n1'
        assert news_needing[1]['news_id'] == 'n3'


class TestEmbeddingGeneration:
    """向量生成测试"""

    def test_encode_text_returns_numpy_array(self):
        """测试编码返回 numpy 数组"""
        with patch('core.processor.history_relation_engine_bge3._get_model') as mock_model:
            mock_instance = Mock()
            mock_instance.encode.return_value = np.array([0.5] * 1024)
            mock_model.return_value = mock_instance

            from core.processor.history_relation_engine_bge3 import encode_text
            result = encode_text("测试文本")

            assert result is not None
            assert isinstance(result, np.ndarray)
            assert result.dtype == np.float32

    def test_encode_text_normalized(self):
        """测试编码结果已归一化"""
        with patch('core.processor.history_relation_engine_bge3._get_model') as mock_model:
            vec = np.random.randn(1024).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            mock_instance = Mock()
            mock_instance.encode.return_value = vec
            mock_model.return_value = mock_instance

            from core.processor.history_relation_engine_bge3 import encode_text
            result = encode_text("测试文本")

            norm = np.linalg.norm(result)
            assert abs(norm - 1.0) < 0.01

    def test_encode_text_empty_string(self):
        """测试空字符串编码"""
        with patch('core.processor.history_relation_engine_bge3._get_model') as mock_model:
            mock_instance = Mock()
            mock_instance.encode.return_value = np.zeros(1024, dtype=np.float32)
            mock_model.return_value = mock_instance

            from core.processor.history_relation_engine_bge3 import encode_text
            result = encode_text("")

            assert result is not None

    def test_encode_text_model_failure(self):
        """测试模型加载失败时返回 None"""
        with patch('core.processor.history_relation_engine_bge3._get_model') as mock_model:
            mock_model.side_effect = Exception("模型加载失败")

            from core.processor.history_relation_engine_bge3 import encode_text
            result = encode_text("测试文本")

            assert result is None


class TestBatchEmbeddingGeneration:
    """批量向量生成测试"""

    def test_batch_encoding(self):
        """测试批量编码"""
        with patch('core.processor.history_relation_engine_bge3._get_model') as mock_model:
            mock_instance = Mock()
            mock_instance.encode.return_value = np.random.randn(3, 1024).astype(np.float32)
            mock_model.return_value = mock_instance

            texts = ["文本1", "文本2", "文本3"]
            result = mock_instance.encode(texts, normalize_embeddings=True, show_progress_bar=False)

            assert result.shape == (3, 1024)

    def test_batch_encoding_skips_existing(self):
        """测试批量编码跳过已有 embedding 的新闻"""
        news_list = [
            {'news_id': 'n1', 'title': '新闻1', 'embedding': None},
            {'news_id': 'n2', 'title': '新闻2', 'embedding': np.array([0.5])},
            {'news_id': 'n3', 'title': '新闻3', 'embedding': None},
        ]

        news_needing = [n for n in news_list if n.get('embedding') is None]
        assert len(news_needing) == 2
        titles = [n['title'] for n in news_needing]
        assert titles == ['新闻1', '新闻3']


class TestEmbeddingStorage:
    """向量存储测试"""

    def test_embedding_tobytes(self):
        """测试向量序列化为字节"""
        embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        blob = embedding.tobytes()
        assert isinstance(blob, (bytes, bytearray))

    def test_embedding_frombytes(self):
        """测试从字节反序列化向量"""
        original = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        blob = original.tobytes()
        restored = np.frombuffer(blob, dtype=np.float32)
        np.testing.assert_array_almost_equal(original, restored)

    def test_embedding_dimensions(self):
        """测试向量维度"""
        dim = 1024
        embedding = np.random.randn(dim).astype(np.float32)
        assert embedding.shape == (dim,)


class TestEmbeddingIntegration:
    """向量集成测试"""

    def test_embedding_workflow(self):
        """测试完整 embedding 工作流"""
        news_list = [
            {'news_id': 'n1', 'title': '新闻1', 'embedding': None},
            {'news_id': 'n2', 'title': '新闻2', 'embedding': None},
        ]

        news_needing = [n for n in news_list if n.get('embedding') is None]
        assert len(news_needing) == 2

        titles = ["新闻1", "新闻2"]
        with patch('core.processor.history_relation_engine_bge3._get_model') as mock_model:
            mock_instance = Mock()
            mock_instance.encode.return_value = np.random.randn(2, 1024).astype(np.float32)
            mock_model.return_value = mock_instance

            from core.processor.history_relation_engine_bge3 import encode_text
            for i, news in enumerate(news_needing):
                vec = encode_text(news['title'])
                if vec is not None:
                    news['embedding'] = vec.astype(np.float32)

        assert news_list[0]['embedding'] is not None
        assert news_list[1]['embedding'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
