#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BGE-M3 历史关联引擎

架构：
  DB embedding(BLOB, float32×1024) → numpy → FAISS 内存内积索引
  → 余弦相似度 Top-K → 意义分类（时间/空间/趋势线索）→ 噪音过滤

权重（README 配置）：semantic 0.7 / time 0.2 / entity 0.1
相似度阈值：0.53
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ─── 配置 ────────────────────────────────────────────────────────────────────

MIN_SIMILARITY = 0.53
MAX_DISPLAY    = 10
W_SEMANTIC     = 0.7
W_TIME         = 0.2
W_ENTITY       = 0.1

_ORG_SUFFIXES    = ('公司', '集团', '银行', '大学', '研究院', '研究所', '机构',
                    '组织', '委员会', '议会', '国会', '政府', '部门', '部', '局',
                    '厅', '院', '社', '报', '台', '基金', '协会')
_PLACE_SUFFIXES  = ('市', '省', '县', '区', '国', '洲', '岛', '地区', '特区')
_PERSON_SUFFIXES = ('总统', '总理', '主席', '部长', '省长', '市长', '局长', '书记',
                    '教授', '博士', '发言人', '将军', '先生', '女士')


# ─── 数据类 ──────────────────────────────────────────────────────────────────

@dataclass
class RelatedRecord:
    news_id:       str
    title:         str
    pub_date:      str
    similarity:    float
    unified_score: float
    time_score:    float
    time_type:     str
    matched_entities: List[str] = field(default_factory=list)
    clue_type:     str = "趋势线索"

    # 兼容旧 RelatedNews 字段名（report_generator 中使用）
    @property
    def related_score(self) -> float:
        return self.unified_score

    @property
    def matched_keywords(self) -> List[str]:
        return self.matched_entities


# ─── 模型单例 ────────────────────────────────────────────────────────────────

_model = None
_LOCAL_MODEL_PATH = None

def _get_local_model_path():
    """获取本地模型路径"""
    global _LOCAL_MODEL_PATH
    if _LOCAL_MODEL_PATH is None:
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        _LOCAL_MODEL_PATH = project_root / 'models' / 'bge-m3'
    return _LOCAL_MODEL_PATH


def _get_model(max_retries: int = 2):
    """
    惰性加载 BGE-M3 模型
    
    加载优先级：
    1. 本地 models/bge-m3/ 目录
    2. HuggingFace 缓存（~/.cache/huggingface/）
    3. 从 HuggingFace Hub 自动下载
    
    失败时返回 None，使用简单聚类降级
    """
    global _model
    if _model is not None:
        return _model
    
    import os
    os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
    
    local_path = _get_local_model_path()
    
    if local_path.exists():
        try:
            t0 = time.time()
            logger.info(f"从本地加载 BGE-M3 模型: {local_path}")
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(str(local_path), device='cpu')
            logger.info(f"BGE-M3 本地加载完成，耗时 {time.time() - t0:.1f}s")
            return _model
        except Exception as e:
            logger.warning(f"BGE-M3 本地加载失败: {e}")
    
    try:
        t0 = time.time()
        logger.info("从 HuggingFace Hub 下载 BGE-M3 模型（首次下载约 2GB）...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('BAAI/bge-m3', device='cpu')
        logger.info(f"BGE-M3 下载并加载完成，耗时 {time.time() - t0:.1f}s")
        return _model
    except Exception as e:
        logger.warning(f"BGE-M3 从 HuggingFace 下载失败: {e}")
    
    logger.info("BGE-M3 模型不可用，将使用简单聚类")
    return None


def encode_text(text: str) -> Optional[np.ndarray]:
    """将文本编码为 L2 归一化 1024 维 float32 向量。"""
    try:
        model = _get_model()
        if model is None:
            return None
        vec = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return vec.astype(np.float32)
    except Exception as e:
        logger.error(f"BGE-M3 编码失败: {e}")
        return None


# ─── FAISS 索引 ──────────────────────────────────────────────────────────────

class _FAISSIndex:
    """内积 FAISS 索引（等价余弦，因向量已 L2 归一化）。"""

    def __init__(self, dim: int = 1024):
        import faiss
        self._idx  = faiss.IndexFlatIP(dim)
        self._ids: List[str]   = []
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


# ─── 辅助 ────────────────────────────────────────────────────────────────────

def _extract_entities(text: str) -> set:
    """提取人名/地名/机构名（jieba 优先，无 jieba 时按空格分词）。"""
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


def _is_noise(clue: str, sim: float, common: set) -> bool:
    """趋势线索 + 无共同实体 + 相似度不足 → 视为噪音，过滤。"""
    return clue == '趋势线索' and not common and sim < 0.65


# ─── 主引擎 ──────────────────────────────────────────────────────────────────

class BGE3HistoryRelationEngine:
    """
    BGE-M3 + FAISS 历史关联引擎。

    使用：
        engine = BGE3HistoryRelationEngine(history_news_list)
        records = engine.find_related_news(target_news, top_k=5)
    """

    def __init__(self, history_news: List[Dict]):
        self._index = _FAISSIndex()
        self._cur_entities: set = set()
        self._build_index(history_news)

    def _build_index(self, history_news: List[Dict]) -> None:
        added = skipped = 0
        for news in history_news:
            vec = _vec_from_news(news)
            if vec is None:
                skipped += 1
                continue
            news_id  = str(news.get('news_id', ''))
            title    = news.get('translated_title') or news.get('title', '')
            pub_date = news.get('pub_date', news.get('publish_date', ''))
            self._index.add(vec, news_id, {
                'title': title, 'pub_date': pub_date, 'news_id': news_id
            })
            added += 1
        logger.info(f"BGE-M3 索引: {added} 条已索引, {skipped} 条跳过")

    def find_related_news(
        self,
        target_news: Dict,
        top_k: int = 5,
        threshold: float = MIN_SIMILARITY,
    ) -> List[RelatedRecord]:
        if self._index.size == 0:
            return []

        target_news_id = str(target_news.get('news_id', ''))

        # 编码当前新闻（优先 DB 向量，其次在线编码标题+摘要）
        query_vec = _vec_from_news(target_news)
        if query_vec is None:
            title   = target_news.get('translated_title') or target_news.get('title', '')
            content = (target_news.get('translated_content')
                       or target_news.get('content', ''))[:200]
            query_vec = encode_text(f"{title} {content}".strip())
        if query_vec is None:
            logger.warning("当前新闻无法编码，跳过 BGE-M3 检索")
            return []

        title_text = (target_news.get('translated_title')
                      or target_news.get('title', ''))
        self._cur_entities = _extract_entities(title_text)

        candidates = self._index.search(query_vec, top_k * 2)

        results: List[RelatedRecord] = []
        for sim, news_id, meta in candidates:
            # 排除当前新闻自身
            if str(news_id) == target_news_id:
                continue
            if sim < threshold:
                continue
            hist_title   = meta['title']
            hist_pub     = meta['pub_date']
            hist_ents    = _extract_entities(hist_title)
            common       = self._cur_entities & hist_ents
            clue         = _clue_type(self._cur_entities, hist_ents)

            if _is_noise(clue, sim, common):
                continue

            t_score, t_type = _time_score_and_type(hist_pub)
            e_score = min(1.0, len(common) * 0.3)
            unified = round(W_SEMANTIC * sim + W_TIME * t_score + W_ENTITY * e_score, 4)

            results.append(RelatedRecord(
                news_id=news_id,
                title=hist_title,
                pub_date=hist_pub,
                similarity=round(sim, 4),
                unified_score=unified,
                time_score=t_score,
                time_type=t_type,
                matched_entities=sorted(common),
                clue_type=clue,
            ))

        results.sort(key=lambda r: r.unified_score, reverse=True)
        return results[:top_k]


# ─── 工厂 ────────────────────────────────────────────────────────────────────

def get_bge3_engine(history_news: List[Dict]) -> BGE3HistoryRelationEngine:
    return BGE3HistoryRelationEngine(history_news)


# ─── 格式化（与 TF-IDF 版接口一致）─────────────────────────────────────────

def format_related_table(records: List[RelatedRecord]) -> str:
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


def format_related_section(records: List[RelatedRecord], cur_title: str) -> str:
    if not records:
        return "未找到显著历史关联事件。"

    timeline = [r for r in records if r.clue_type == '时间线索']
    spatial  = [r for r in records if r.clue_type == '空间线索']
    trend    = [r for r in records if r.clue_type == '趋势线索']

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


# ─── 内部工具 ────────────────────────────────────────────────────────────────

def _vec_from_news(news: Dict) -> Optional[np.ndarray]:
    """优先从 news['embedding'] BLOB 取向量（DB 预计算），否则在线编码。"""
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
    return None
