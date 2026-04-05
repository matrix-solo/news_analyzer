#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热榜数据获取器（已弃用，请使用 core.utils.hotboard_manager）

数据源：UAPI 热榜接口（https://uapis.cn/api/misc/hotboard）
平台：weibo / zhihu / baidu / toutiao
缓存：数据库 hotboard_cache 表，有效期 3 小时

[DEPRECATED] 此模块保留用于向后兼容，所有新代码应使用
core.utils.hotboard_manager.HotboardManager 获取热榜数据。
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)

# ─── 配置 ────────────────────────────────────────────────────────────────────

_UAPI_BASE   = "https://uapis.cn/api/v1/misc/hotboard"
_PLATFORMS   = ["weibo", "zhihu", "baidu", "toutiao"]
_CACHE_TTL_H = 3          # 热榜缓存有效时长（小时）
_TIMEOUT     = 15         # 单次请求超时（秒）
_MAX_ITEMS   = 50         # 每平台最多取条数


@dataclass
class HotItem:
    platform:  str
    rank:      int
    title:     str
    hot_value: int = 0
    url:       str = ""


# ─── 主类 ────────────────────────────────────────────────────────────────────

class HotboardFetcher:
    """
    热榜数据获取器（单例）。

    fetch_hotboard() 返回 List[HotItem]：
    - 优先从数据库缓存读取（TTL 3h 内）
    - 缓存过期则拉取四平台热榜并写入数据库
    - 任何单平台失败静默跳过，不阻断整体
    """

    def __init__(self):
        self._api_key: str = os.getenv("HOTBOARD_API_KEY", "")
        if not self._api_key:
            logger.warning("HOTBOARD_API_KEY 未配置，热榜获取将失败")

    # ── 公共接口 ────────────────────────────────────────────────────────────

    def fetch_hotboard(self) -> List[HotItem]:
        """返回四平台热榜列表，优先缓存。"""
        # 1. 尝试从 DB 缓存读取
        cached = self._load_from_cache()
        if cached:
            return cached

        # 2. 拉取新数据
        items = self._fetch_all_platforms()
        if items:
            self._save_to_cache(items)
        return items

    def titles(self) -> List[str]:
        """返回所有热榜标题（供热度评分使用）。"""
        return [item.title for item in self.fetch_hotboard()]

    def get_all_titles(self) -> List[str]:
        """返回所有热榜标题（别名方法）。"""
        return self.titles()

    # ── 平台拉取 ────────────────────────────────────────────────────────────

    def _fetch_all_platforms(self) -> List[HotItem]:
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
        """解析热度值，支持多种格式如 '1131055' 或 '928 万热度'"""
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

    # ── 数据库缓存 ──────────────────────────────────────────────────────────

    def _load_from_cache(self) -> Optional[List[HotItem]]:
        try:
            from core.storage.database import get_db
            db = get_db()
            expires_after = datetime.now() - timedelta(hours=_CACHE_TTL_H)
            with db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT platform, rank, title, hot_value, url FROM hotboard_cache "
                    "WHERE fetched_at > ? ORDER BY platform, rank",
                    (expires_after.isoformat(),),
                ).fetchall()
            if not rows:
                return None
            items = [
                HotItem(platform=r[0], rank=r[1], title=r[2],
                        hot_value=r[3] or 0, url=r[4] or "")
                for r in rows
            ]
            logger.debug(f"热榜从缓存读取: {len(items)} 条")
            return items
        except Exception as e:
            logger.debug(f"热榜缓存读取失败（降级拉取）: {e}")
            return None

    def _save_to_cache(self, items: List[HotItem]) -> None:
        try:
            from core.storage.database import get_db
            db = get_db()
            expires_at = (datetime.now() + timedelta(hours=_CACHE_TTL_H)).isoformat()
            with db.get_connection() as conn:
                # 清理同平台旧缓存
                conn.execute("DELETE FROM hotboard_cache")
                conn.executemany(
                    "INSERT INTO hotboard_cache (platform, rank, title, hot_value, url, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    [(it.platform, it.rank, it.title, it.hot_value, it.url, expires_at)
                     for it in items],
                )
        except Exception as e:
            logger.warning(f"热榜缓存写入失败（不影响主流程）: {e}")


# ─── 单例 ────────────────────────────────────────────────────────────────────

_instance: Optional[HotboardFetcher] = None


def get_hotboard_fetcher() -> HotboardFetcher:
    global _instance
    if _instance is None:
        _instance = HotboardFetcher()
    return _instance
