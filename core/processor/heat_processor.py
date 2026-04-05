#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热度评分处理器

算法（README 定义）：
  Step1: 获取四平台热榜（HotboardManager 统一管理）
  Step2: BGE-M3 向量化热榜标题 → FAISS 内积索引
  Step3: 新闻向量化（优先 DB embedding）→ 余弦相似度匹配
  Step4: 评分规则
    - 无匹配:                           0 分
    - 单平台匹配, 相似度 0.85-0.90:     4 分
    - 单平台匹配, 相似度 > 0.90:        5 分
    - 2 个平台匹配:                     7 分
    - 3 个平台匹配:                     8 分
    - 4 个平台匹配:                   9-10 分

降级策略：
  faiss / sentence-transformers 未安装 → 关键词匹配（每命中热榜词 +1，最高 5 分）
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

_SIM_THRESHOLD = 0.85   # 匹配阈值


# ─── 向量热榜索引（统一由 HotboardManager 管理）───────────────────────────────

_hotboard_cache = None


def _get_hotboard_cache():
    """通过 HotboardManager 获取统一的缓存实例，与 task1 阶段共享同一份数据。"""
    global _hotboard_cache
    if _hotboard_cache is not None and not _hotboard_cache.is_expired():
        return _hotboard_cache

    try:
        from core.utils.hotboard_manager import get_hotboard_manager
        manager = get_hotboard_manager()
        cache = manager.get_cache()
        _hotboard_cache = cache
        return cache
    except Exception as e:
        logger.warning(f"热榜缓存获取失败（降级）: {e}")
        return None


# ─── 评分规则 ────────────────────────────────────────────────────────────────

def _score_from_matches(platform_sims: Dict[str, float]) -> int:
    """
    README 评分规则映射。
    platform_sims: {platform: max_similarity}
    """
    n = len(platform_sims)
    if n == 0:
        return 0
    if n == 1:
        sim = next(iter(platform_sims.values()))
        return 5 if sim > 0.90 else 4
    if n == 2:
        return 7
    if n == 3:
        return 8
    # n >= 4
    avg_sim = sum(platform_sims.values()) / n
    return 10 if avg_sim > 0.92 else 9


# ─── 降级：关键词匹配 ────────────────────────────────────────────────────────

def _keyword_heat(text: str) -> int:
    """关键词匹配降级：每命中一条热榜词得 1 分，上限 5。"""
    try:
        from core.utils.hotboard_manager import get_hotboard_manager
        manager = get_hotboard_manager()
        cache = manager.get_cache(force_refresh=False)
        if cache is None:
            return 0
        titles = cache.get_all_titles()
    except Exception:
        return 0

    hit = sum(1 for t in titles if t and t in text)
    return min(hit, 5)


# ─── 主处理器 ────────────────────────────────────────────────────────────────

class HeatProcessor:
    """
    热度评分处理器。

    calculate_heat_score(news) -> int (0-10)
    """

    def calculate_heat_score(self, news: Dict) -> int:
        """
        计算单条新闻的热度评分（0-10 整数）。

        BGE-M3 路径：
            1. 获取新闻向量（DB BLOB 或在线编码）
            2. 与热榜 FAISS 索引做余弦相似度匹配
            3. 按匹配平台数量和相似度映射得分

        降级路径（faiss/model 不可用）：
            关键词命中计数，上限 5 分
        """
        # 构建查询向量
        query_vec = self._get_query_vec(news)
        if query_vec is None:
            return self._fallback(news)

        # 获取热榜向量索引
        cache = _get_hotboard_cache()
        if cache is None:
            return self._fallback(news)

        platform_sims = cache.match_platforms(query_vec)
        score = _score_from_matches(platform_sims)

        if platform_sims:
            logger.debug(
                f"热度匹配: {list(platform_sims.keys())} → {score}分"
            )

        return score

    @staticmethod
    def _get_query_vec(news: Dict) -> Optional[np.ndarray]:
        """优先用 DB 预计算向量，否则在线编码标题。"""
        blob = news.get('embedding')
        if blob and isinstance(blob, (bytes, bytearray)):
            try:
                vec = np.frombuffer(blob, dtype=np.float32).copy()
                if vec.shape == (1024,):
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec /= norm
                    return vec
            except Exception:
                pass

        # 在线编码
        try:
            from core.processor.history_relation_engine_bge3 import encode_text
            title = (news.get('translated_title') or news.get('title', '')).strip()
            if title:
                return encode_text(title)
        except Exception:
            pass
        return None

    @staticmethod
    def _fallback(news: Dict) -> int:
        text = (news.get('translated_title', '') + ' '
                + news.get('title', '') + ' '
                + (news.get('translated_content') or ''))
        return _keyword_heat(text)

    def calculate_batch(self, news_list: List[Dict]) -> List[int]:
        """
        批量计算热度评分（优化版）
        
        一次性编码所有新闻标题，然后批量匹配热榜索引
        
        Args:
            news_list: 新闻列表
            
        Returns:
            热度评分列表，与输入顺序一致
        """
        if not news_list:
            return []
        
        cache = _get_hotboard_cache()
        if cache is None:
            return [self._fallback(news) for news in news_list]
        
        from core.processor.history_relation_engine_bge3 import _get_model

        model = _get_model()
        if model is None:
            logger.warning("BGE3模型不可用，使用关键词热度评分")
            return [self._fallback(news) for news in news_list]

        titles = []
        for news in news_list:
            title = (news.get('translated_title') or news.get('title', '')).strip()
            titles.append(title if title else " ")

        try:
            vecs = model.encode(titles, normalize_embeddings=True, show_progress_bar=False).astype(np.float32)
        except Exception as e:
            logger.warning(f"批量编码失败: {e}")
            return [self._fallback(news) for news in news_list]
        
        scores = []
        for i, vec in enumerate(vecs):
            platform_sims = cache.match_platforms(vec)
            score = _score_from_matches(platform_sims)
            scores.append(score)
            
            if platform_sims:
                logger.debug(f"热度匹配 [{i}]: {list(platform_sims.keys())} → {score}分")
        
        return scores
