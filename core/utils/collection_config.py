#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""采集配置管理器"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class CollectionConfigManager:
    def get_source_config(self, source_name: str) -> dict:
        return {}

    def is_source_enabled(self, source_name: str) -> bool:
        return True

    def detect_gap(
        self,
        source_name: str,
        collected_count: int,
        db_latest_pub_date: Optional[str] = None,
        rss_earliest_pub_date: Optional[str] = None,
        rss_latest_pub_date: Optional[str] = None,
    ) -> dict:
        """
        检测 RSS 采集是否存在遗漏间隙。

        核心逻辑：
        如果 DB 中最新 pub_date 早于 RSS feed 中最早 pub_date，
        说明中间有一段时间的新闻被 RSS 滚动窗口丢弃，存在遗漏。

        Returns:
            dict: {has_gap, gap_type, gap_score, suggestion, ...}
        """
        default = {
            'has_gap': False,
            'gap_type': 'none',
            'gap_score': 0,
            'gap_duration_hours': 0,
            'suggestion': '采集正常',
            'rss_earliest': rss_earliest_pub_date,
            'db_latest': db_latest_pub_date,
        }

        if not db_latest_pub_date or not rss_earliest_pub_date:
            return default

        try:
            db_latest = self._parse_date(db_latest_pub_date)
            rss_earliest = self._parse_date(rss_earliest_pub_date)

            if db_latest is None or rss_earliest is None:
                return default

            # DB 最新时间 < RSS 最早时间 → 中间有间隙
            if db_latest < rss_earliest:
                gap_hours = (rss_earliest - db_latest).total_seconds() / 3600
                gap_score = min(1.0, gap_hours / 24)  # 24小时=满分
                return {
                    'has_gap': True,
                    'gap_type': 'rss_rollover',
                    'gap_score': round(gap_score, 2),
                    'gap_duration_hours': round(gap_hours, 1),
                    'suggestion': f'疑似遗漏 {gap_hours:.0f} 小时新闻（RSS滚动窗口覆盖不到）',
                    'rss_earliest': rss_earliest_pub_date,
                    'db_latest': db_latest_pub_date,
                }

            # 采集到 0 条但 RSS 有内容 → 也可能有问题
            if collected_count == 0 and rss_latest_pub_date:
                rss_latest = self._parse_date(rss_latest_pub_date)
                if rss_latest and db_latest:
                    stale_hours = (rss_latest - db_latest).total_seconds() / 3600
                    if stale_hours > 6:
                        return {
                            'has_gap': True,
                            'gap_type': 'stale_data',
                            'gap_score': min(1.0, stale_hours / 24),
                            'gap_duration_hours': round(stale_hours, 1),
                            'suggestion': f'RSS有新闻但未入库，最近 {stale_hours:.0f} 小时可能遗漏',
                            'rss_earliest': rss_earliest_pub_date,
                            'db_latest': db_latest_pub_date,
                        }

        except Exception as e:
            logger.debug(f"间隙检测异常 [{source_name}]: {e}")

        return default

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """尝试解析 ISO 格式日期字符串"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00')).replace(tzinfo=None)
        except (ValueError, TypeError):
            return None


_instance = None


def get_collection_config_manager() -> CollectionConfigManager:
    global _instance
    if _instance is None:
        _instance = CollectionConfigManager()
    return _instance
