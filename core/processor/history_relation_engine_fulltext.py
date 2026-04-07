#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BGE-M3 全文向量历史关联引擎（索引B）

架构：
- 独立于标题向量索引A
- 使用全文（original_article）进行向量化
- 动态阈值 + unified_score 过滤

与索引A的区别：
- 索引A: 用于事件聚类、HOT10查询，输入为 title embedding
- 索引B: 用于深度分析历史关联，输入为 original_article embedding
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

MIN_SIMILARITY = 0.53
W_SEMANTIC = 0.7
W_TIME = 0.2
W_ENTITY = 0.1


@dataclass
class FullTextRelatedRecord:
    """全文关联记录"""
    news_id: str
    title: str
    pub_date: str
    full_text: str
    similarity: float
    unified_score: float
    time_score: float
    time_type: str
    matched_entities: List[str] = field(default_factory=list)
    clue_type: str = "趋势线索"

    @property
    def related_score(self) -> float:
        return self.unified_score


_model = None


def _get_local_model_path():
    """获取本地模型路径"""
    from pathlib import Path
    return Path(__file__).parent.parent.parent / 'models' / 'bge-m3'


def _get_model():
    """惰性加载 BGE-M3；优先从本地加载，失败则从 HF Hub 下载。"""
    global _model
    if _model is not None:
        return _model
    import os
    os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
    from sentence_transformers import SentenceTransformer

    local_path = _get_local_model_path()

    if local_path.exists():
        try:
            t0 = time.time()
            logger.info(f"从本地加载 BGE-M3 模型（全文索引）: {local_path}")
            _model = SentenceTransformer(str(local_path), device='cpu')
            logger.info(f"BGE-M3 本地加载完成，耗时 {time.time() - t0:.1f}s")
            return _model
        except Exception as e:
            logger.warning(f"BGE-M3 本地加载失败: {e}，尝试从 HF Hub 下载")

    # 本地模型不可用时，从 HF Hub 下载（与 Index A 行为一致）
    try:
        t0 = time.time()
        logger.info("从 HuggingFace Hub 下载 BGE-M3 模型（全文索引）...")
        _model = SentenceTransformer('BAAI/bge-m3', device='cpu')
        logger.info(f"BGE-M3 下载加载完成，耗时 {time.time() - t0:.1f}s")
        return _model
    except Exception as e:
        logger.warning(f"BGE-M3 模型不可用（本地和远程均失败）: {e}")
        return None


def encode_text(text: str) -> Optional[np.ndarray]:
    """将文本编码为 L2 归一化 1024 维 float32 向量"""
    if not text or not text.strip():
        return None
    try:
        model = _get_model()
        vec = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return vec.astype(np.float32)
    except Exception as e:
        logger.error(f"BGE-M3 编码失败: {e}")
        return None


class _FAISSIndex:
    """内积 FAISS 索引"""
    def __init__(self, dim: int = 1024):
        import faiss
        self._idx = faiss.IndexFlatIP(dim)
        self._ids: List[str] = []
        self._meta: List[Dict] = []

    def add(self, vec: np.ndarray, news_id: str, meta: Dict) -> None:
        self._idx.add(vec.reshape(1, -1))
        self._ids.append(news_id)
        self._meta.append(meta)

    def search(self, query: np.ndarray, top_k: int) -> List[Tuple[float, str, Dict]]:
        if self._idx.ntotal == 0:
            return []
        k = min(top_k, self._idx.ntotal)
        dists, indices = self._idx.search(query.reshape(1, -1), k)
        results = []
        for dist, idx in zip(dists[0], indices[0]):
            if idx >= 0:
                results.append((float(dist), self._ids[idx], self._meta[idx]))
        return results

    @property
    def size(self) -> int:
        return self._idx.ntotal


_ORG_SUFFIXES = ('公司', '集团', '银行', '大学', '研究院', '研究所', '机构',
                  '组织', '委员会', '议会', '国会', '政府', '部门', '部', '局',
                  '厅', '院', '社', '报', '台', '基金', '协会')
_PLACE_SUFFIXES = ('市', '省', '县', '区', '国', '洲', '岛', '地区', '特区')
_PERSON_SUFFIXES = ('总统', '总理', '主席', '部长', '省长', '市长', '局长', '书记',
                    '教授', '博士', '发言人', '将军', '先生', '女士')


def _extract_entities(text: str) -> set:
    """提取人名/地名/机构名"""
    all_sfx = _ORG_SUFFIXES + _PLACE_SUFFIXES + _PERSON_SUFFIXES
    try:
        import jieba
        words = jieba.lcut(text)
    except ImportError:
        words = text.split()
    return {w for w in words if len(w) >= 2 and any(w.endswith(s) for s in all_sfx)}


def _time_score_and_type(pub_date_str: str) -> Tuple[float, str]:
    try:
        pub = datetime.fromisoformat(pub_date_str[:10])
        now = datetime.now().replace(tzinfo=None)
        delta = (now - pub).days
    except Exception:
        return 0.3, '历史背景'

    if delta <= 7:
        return 1.0, '本周关联'
    elif delta <= 30:
        return round(1.0 - (delta - 7) / 23 * 0.4, 3), '近期关联'
    else:
        return round(max(0.2, 0.6 - (delta - 30) / 60 * 0.4), 3), '历史背景'


def _clue_type(cur_ents: set, hist_ents: set) -> str:
    common = cur_ents & hist_ents
    if not common:
        return '趋势线索'
    if any(e.endswith(s) for e in common for s in _PLACE_SUFFIXES):
        return '空间线索'
    return '时间线索'


def _calculate_dynamic_threshold(
    candidates: List[FullTextRelatedRecord],
    min_score: float = 0.3,
    dynamic_percentile: float = 0.2
) -> float:
    """
    计算动态阈值

    公式：动态阈值 = max(min_score, 百分位阈值)

    设计原则：宁可少而精，不可用低质量凑数
    """
    if not candidates:
        return min_score

    scores = [c.unified_score for c in candidates]
    sorted_scores = sorted(scores, reverse=True)

    index = int(len(sorted_scores) * dynamic_percentile)
    if index >= len(sorted_scores):
        percentile_threshold = sorted_scores[-1] if sorted_scores else min_score
    else:
        percentile_threshold = sorted_scores[index]

    return max(min_score, percentile_threshold)


class BGE3FullTextEngine:
    """
    全文向量历史关联引擎（索引B）

    独立于现有的标题向量索引，用于深度分析时的历史关联

    使用：
        engine = BGE3FullTextEngine()
        engine.add_full_text(news_id, title, pub_date, full_text)
        records = engine.find_related_full_text(target_text, top_k=5)
    """

    def __init__(self):
        self._index = _FAISSIndex()
        self._news_store: Dict[str, Dict] = {}

    def add_full_text(self, news_id: str, title: str, pub_date: str, full_text: str) -> bool:
        """
        添加全文到索引

        Args:
            news_id: 新闻ID
            title: 新闻标题
            pub_date: 发布日期
            full_text: 完整文章内容

        Returns:
            是否添加成功
        """
        if not full_text or not full_text.strip():
            logger.debug(f"跳过空全文: {news_id}")
            return False

        vec = encode_text(full_text)
        if vec is None:
            logger.warning(f"全文编码失败: {news_id}")
            return False

        self._index.add(vec, news_id, {
            'title': title,
            'pub_date': pub_date,
            'news_id': news_id,
            'full_text': full_text
        })

        self._news_store[news_id] = {
            'title': title,
            'pub_date': pub_date,
            'full_text': full_text
        }

        return True

    def add_news(self, news: Dict) -> bool:
        """
        从新闻字典添加

        Args:
            news: 新闻字典，需包含 news_id, title, full_text

        Returns:
            是否添加成功
        """
        return self.add_full_text(
            news.get('news_id', ''),
            news.get('translated_title') or news.get('title', ''),
            news.get('pub_date', news.get('publish_date', '')),
            news.get('original_article', '') or news.get('full_text', '')
        )

    def find_related_full_text(
        self,
        target_text: str,
        top_k: int = 5,
        min_score: float = 0.3,
        dynamic_percentile: float = 0.2
    ) -> List[FullTextRelatedRecord]:
        """
        基于全文的关联搜索

        流程：
        1. 编码目标文本
        2. 向量搜索获取候选
        3. 计算所有候选的 unified_score
        4. 动态阈值 = max(min_score, 百分位阈值)
        5. 过滤：unified_score >= 动态阈值
        6. 按 unified_score 排序，取前 top_k

        设计原则：宁可少而精，不可用低质量凑数

        Args:
            target_text: 目标文本（今日新闻全文）
            top_k: 返回数量上限
            min_score: 绝对质量底线
            dynamic_percentile: 动态阈值百分位（0.2 = 前20%分位数）

        Returns:
            关联记录列表
        """
        if self._index.size == 0:
            return []

        query_vec = encode_text(target_text)
        if query_vec is None:
            logger.warning("目标文本无法编码")
            return []

        target_entities = _extract_entities(target_text)

        candidates = self._index.search(query_vec, top_k * 3)

        results: List[FullTextRelatedRecord] = []
        for sim, news_id, meta in candidates:
            hist_title = meta['title']
            hist_pub = meta['pub_date']
            hist_full_text = meta.get('full_text', '')
            hist_entities = _extract_entities(hist_full_text) if hist_full_text else set()
            common = target_entities & hist_entities
            clue = _clue_type(target_entities, hist_entities)

            t_score, t_type = _time_score_and_type(hist_pub)
            e_score = min(1.0, len(common) * 0.3)
            unified = round(W_SEMANTIC * sim + W_TIME * t_score + W_ENTITY * e_score, 4)

            results.append(FullTextRelatedRecord(
                news_id=news_id,
                title=hist_title,
                pub_date=hist_pub,
                full_text=hist_full_text,
                similarity=round(sim, 4),
                unified_score=unified,
                time_score=t_score,
                time_type=t_type,
                matched_entities=sorted(common),
                clue_type=clue,
            ))

        dynamic_threshold = _calculate_dynamic_threshold(
            results,
            min_score=min_score,
            dynamic_percentile=dynamic_percentile
        )

        filtered = [r for r in results if r.unified_score >= dynamic_threshold]

        filtered.sort(key=lambda r: r.unified_score, reverse=True)

        return filtered[:top_k]

    def get_full_text(self, news_id: str) -> Optional[str]:
        """获取已存储的全文"""
        return self._news_store.get(news_id, {}).get('full_text')


def format_fulltext_related_table(records: List[FullTextRelatedRecord]) -> str:
    """格式化关联表格"""
    if not records:
        return ""
    lines = [
        "| 线索类型 | 日期 | 历史事件标题 | 语义相似度 | 综合评分 |",
        "|----------|------|-------------|-----------|---------|",
    ]
    icons = {'时间线索': '📅', '空间线索': '🗺️', '趋势线索': '📊'}
    for r in records:
        icon = icons.get(r.clue_type, '🔗')
        lines.append(
            f"| {icon} {r.clue_type} | {r.pub_date[:10]} | {r.title[:30]} "
            f"| {r.similarity:.2f} | {r.unified_score:.3f} |"
        )
    return "\n".join(lines)


def format_fulltext_related_section(records: List[FullTextRelatedRecord], cur_title: str) -> str:
    """格式化关联章节"""
    if not records:
        return "未找到显著历史关联事件。"

    timeline = [r for r in records if r.clue_type == '时间线索']
    spatial = [r for r in records if r.clue_type == '空间线索']
    trend = [r for r in records if r.clue_type == '趋势线索']

    parts: List[str] = []

    if timeline:
        parts.append("#### 📅 事件发展脉络")
        parts.append("> 同一实体/事件的历史发展：\n")
        parts.append(f"🔴 **今日** {cur_title}\n   └─ 当前事件\n")
        for r in timeline:
            ents = "、".join(r.matched_entities[:3]) if r.matched_entities else "相关实体"
            parts.append(f"⚪ **{r.pub_date[:10]}** {r.title}\n   └─ 关联实体：{ents}\n")

    if spatial:
        parts.append("#### 🗺️ 同地区相关动态")
        for r in spatial:
            parts.append(f"- **{r.pub_date[:10]}** {r.title}")

    if trend:
        parts.append("#### 📊 趋势线索")
        for r in trend:
            parts.append(f"- **{r.pub_date[:10]}** {r.title}（相似度 {r.similarity:.2f}）")

    return "\n".join(parts)