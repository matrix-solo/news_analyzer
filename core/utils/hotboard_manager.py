#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热榜数据统一管理器

设计原则（第一性原理）：
  1. 单一缓存权威 — 热榜数据只能有一个真实来源，所有评分逻辑从同一个缓存实例获取
  2. 缓存生命周期内数据不变 — TTL 有效期内任何阶段访问，返回完全一致的内容
  3. 向量化与数据同生命周期 — embedding 和原始数据在同一次操作中完成

数据流：
  [API 拉取] → [向量化] → [FAISS 索引] → [持久化 DB]
                                     ↓
  [任何需要热榜的地方] ← HotboardManager.get_cache() ← [缓存实例]
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_CACHE_TTL_HOURS = 6
_PLATFORMS = ["weibo", "zhihu", "baidu", "toutiao"]
_UAPI_BASE = "https://uapis.cn/api/v1/misc/hotboard"
_TIMEOUT = 15
_MAX_ITEMS = 50


@dataclass
class HotItem:
    platform: str
    rank: int
    title: str
    hot_value: int = 0
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "rank": self.rank,
            "title": self.title,
            "hot_value": self.hot_value,
            "url": self.url,
        }


class HotboardCache:
    def __init__(self):
        self._indices: Dict[str, tuple] = {}
        self._items: List[HotItem] = []
        self._expires_at: Optional[datetime] = None
        self._built: bool = False

    def is_expired(self) -> bool:
        if self._expires_at is None:
            return True
        return datetime.now() > self._expires_at

    @property
    def items(self) -> List[HotItem]:
        return self._items

    @property
    def platforms(self) -> List[str]:
        return list(self._indices.keys())

    def get_all_titles(self) -> List[str]:
        return [item.title for item in self._items]

    def match_platforms(self, query_vec: np.ndarray, threshold: float = 0.85) -> Dict[str, float]:
        matched: Dict[str, float] = {}
        for platform, (idx, _) in self._indices.items():
            if idx.ntotal == 0:
                continue
            dists, _ = idx.search(query_vec.reshape(1, -1), 1)
            sim = float(dists[0][0])
            if np.isnan(sim) or sim < threshold:
                continue
            matched[platform] = sim
        return matched

    def build_index(self, items: List[HotItem]) -> None:
        from core.processor.history_relation_engine_bge3 import _get_model
        import faiss

        self._items = items
        self._built = False
        self._indices = {}

        model = _get_model()
        if model is None:
            logger.warning("BGE3 模型不可用，热榜索引未构建")
            return

        by_platform: Dict[str, List[str]] = {}
        for item in items:
            by_platform.setdefault(item.platform, []).append(item.title)

        for platform, titles in by_platform.items():
            vecs = model.encode(titles, normalize_embeddings=True,
                                show_progress_bar=False).astype(np.float32)
            idx = faiss.IndexFlatIP(1024)
            idx.add(vecs)
            self._indices[platform] = (idx, titles)

        self._built = True
        total = sum(len(v) for v in by_platform.values())
        logger.info(f"热榜 FAISS 索引构建完成: {total} 条（{len(by_platform)} 平台）")

    def rebuild_from_embeddings(self, items: List[HotItem],
                                 embeddings: Optional[np.ndarray]) -> None:
        import faiss

        self._items = items
        self._indices = {}

        if embeddings is None:
            logger.warning("无预存 embedding，从头编码")
            self.build_index(items)
            return

        by_platform: Dict[str, List[str]] = {}
        for item in items:
            by_platform.setdefault(item.platform, []).append(item.title)

        offset = 0
        for platform, titles in by_platform.items():
            n = len(titles)
            vecs = embeddings[offset:offset + n].astype(np.float32)
            idx = faiss.IndexFlatIP(1024)
            idx.add(vecs)
            self._indices[platform] = (idx, titles)
            offset += n

        self._built = True
        total = sum(len(v) for v in by_platform.values())
        logger.info(f"热榜 FAISS 索引从 DB embeddings 重建完成: {total} 条")


class HotboardManager:
    _cache: Optional[HotboardCache] = None
    _api_key: str = ""

    def __init__(self):
        self._api_key = os.getenv("HOTBOARD_API_KEY", "")
        if not self._api_key:
            logger.warning("HOTBOARD_API_KEY 未配置，热榜获取将失败")

    def get_cache(self, force_refresh: bool = False) -> Optional[HotboardCache]:
        if HotboardManager._cache is None:
            HotboardManager._cache = HotboardCache()

        if force_refresh or HotboardManager._cache.is_expired():
            # 优先从 DB 加载（使用预存 embeddings，无需重新向量化）
            if not force_refresh:
                if self._load_from_db():
                    return HotboardManager._cache

            # DB 也没有或强制刷新 → 调用 API
            if not self._refresh():
                if not HotboardManager._cache._built:
                    self._load_from_db()

        return HotboardManager._cache if HotboardManager._cache._built else None

    def _refresh(self) -> bool:
        items = self._fetch_from_api()
        if not items:
            logger.warning("热榜 API 获取为空，尝试从 DB 加载")
            return False

        cache = HotboardManager._cache
        cache._expires_at = datetime.now() + timedelta(hours=_CACHE_TTL_HOURS)
        cache.build_index(items)
        self._save_to_db(items)
        logger.info(f"热榜缓存刷新成功: {len(items)} 条，TTL {_CACHE_TTL_HOURS}h")
        return True

    def _fetch_from_api(self) -> List[HotItem]:
        all_items: List[HotItem] = []
        for platform in _PLATFORMS:
            try:
                items = self._fetch_platform(platform)
                all_items.extend(items)
                logger.debug(f"热榜 {platform}: {len(items)} 条")
            except Exception as e:
                logger.debug(f"热榜 {platform} 获取失败（跳过）: {e}")
        logger.info(f"热榜获取完成: {len(all_items)} 条（{len(_PLATFORMS)} 平台）")
        return all_items

    def _fetch_platform(self, platform: str) -> List[HotItem]:
        url = f"{_UAPI_BASE}?key={self._api_key}&type={platform}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        items: List[HotItem] = []
        raw_list = data.get("list", data.get("data", []))
        for rank, entry in enumerate(raw_list[:_MAX_ITEMS], start=1):
            title = (entry.get("title") or entry.get("name") or "").strip()
            if not title:
                continue
            hot_str = entry.get("hot_value", entry.get("hot", entry.get("hotValue", "0")))
            hot_value = self._parse_hot_value(hot_str)
            items.append(HotItem(
                platform=platform,
                rank=rank,
                title=title,
                hot_value=hot_value,
                url=entry.get("url", entry.get("mobileUrl", "")),
            ))
        return items

    def _parse_hot_value(self, hot_str) -> int:
        if hot_str is None:
            return 0
        if isinstance(hot_str, (int, float)):
            return int(hot_str)
        try:
            hot_str = str(hot_str).strip()
            if not hot_str:
                return 0
            if "万" in hot_str:
                num_str = hot_str.replace("万", "").replace("热度", "").strip()
                return int(float(num_str) * 10000)
            if "亿" in hot_str:
                num_str = hot_str.replace("亿", "").strip()
                return int(float(num_str) * 100000000)
            return int(float(hot_str.replace("热度", "").strip()))
        except (ValueError, AttributeError):
            return 0

    def _save_to_db(self, items: List[HotItem]) -> None:
        try:
            from core.storage.database import get_db
            db = get_db()
            expires_at = (datetime.now() + timedelta(hours=_CACHE_TTL_HOURS)).strftime('%Y-%m-%d %H:%M:%S')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            from core.processor.history_relation_engine_bge3 import _get_model
            model = _get_model()
            embeddings = None
            if model and items:
                titles = [item.title for item in items]
                embeddings = model.encode(titles, normalize_embeddings=True,
                                          show_progress_bar=False)

            cache_data = []
            for i, item in enumerate(items):
                emb = None
                if embeddings is not None:
                    emb = embeddings[i].tobytes() if hasattr(embeddings[i], 'tobytes') else embeddings[i]
                cache_data.append({
                    "platform": item.platform,
                    "rank": item.rank,
                    "title": item.title,
                    "hot_value": item.hot_value,
                    "url": item.url,
                    "embedding": emb,
                    "expires_at": expires_at,
                    "fetched_at": now,
                })

            saved = db.save_hotboard_cache(cache_data, ttl_hours=_CACHE_TTL_HOURS)
            logger.info(f"热榜缓存已持久化: {saved} 条")
        except Exception as e:
            logger.warning(f"热榜缓存持久化失败（不影响流程）: {e}")

    def _load_from_db(self) -> bool:
        try:
            from core.storage.database import get_db
            db = get_db()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT platform, rank, title, hot_value, url, embedding FROM hotboard_cache "
                    "WHERE expires_at > ? ORDER BY platform, rank",
                    (now,),
                ).fetchall()

            if not rows:
                logger.warning("数据库中无有效热榜缓存")
                return False

            items = []
            embeddings = []
            for r in rows:
                items.append(HotItem(
                    platform=r[0], rank=r[1], title=r[2],
                    hot_value=r[3] or 0, url=r[4] or ""
                ))
                emb = r[5]
                if emb is not None:
                    try:
                        vec = np.frombuffer(emb, dtype=np.float32)
                        embeddings.append(vec)
                    except Exception:
                        pass

            has_all_embeddings = len(embeddings) == len(items)
            emb_array = np.stack(embeddings) if has_all_embeddings else None

            logger.info(f"从数据库加载热榜缓存: {len(items)} 条")

            cache = HotboardManager._cache
            cache._expires_at = datetime.now() + timedelta(hours=_CACHE_TTL_HOURS)
            cache.rebuild_from_embeddings(items, emb_array)
            return True

        except Exception as e:
            logger.warning(f"从数据库加载热榜缓存失败: {e}")
            return False


_instance: Optional[HotboardManager] = None


def get_hotboard_manager() -> HotboardManager:
    global _instance
    if _instance is None:
        _instance = HotboardManager()
    return _instance


def keyword_match_heat(text: str) -> int:
    try:
        manager = get_hotboard_manager()
        cache = manager.get_cache(force_refresh=False)
        if cache is None:
            return 0
        titles = cache.get_all_titles()
    except Exception:
        return 0

    hit = sum(1 for t in titles if t and t in text)
    return min(hit, 5)
