#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量采集追踪器 - 基于 pub_date 实现增量采集，避免重复采集
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from core.config.loader import PROJECT_ROOT as _project_root
_state_dir = Path(_project_root) / "data" / "incremental"


class IncrementalTracker:
    """记录每个信源的最后采集时间，实现增量采集"""

    def __init__(self):
        _state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = _state_dir / "tracker_state.json"
        self._state = self._load_state()

    def _load_state(self) -> dict:
        if self._state_file.exists():
            try:
                return json.loads(self._state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_state(self):
        try:
            self._state_file.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"保存增量状态失败: {e}")

    def get_intelligent_cutoff_date(self, source_name: str) -> Optional[datetime]:
        """获取建议的截断日期（增量起始点）"""
        src = self._state.get(source_name, {})
        last_date_str = src.get("last_pub_date")
        if not last_date_str:
            return None
        try:
            return datetime.fromisoformat(last_date_str).replace(tzinfo=None)
        except Exception:
            return None

    def get_suggested_max_items(self, source_name: str, default_max: int) -> int:
        """获取建议的最大采集条目数"""
        src = self._state.get(source_name, {})
        downtime = self.get_downtime_hours(source_name)
        if downtime > 12:
            return min(default_max * 2, 50)
        return default_max

    def get_downtime_hours(self, source_name: str) -> float:
        """获取距上次采集的小时数"""
        src = self._state.get(source_name, {})
        last_run_str = src.get("last_run")
        if not last_run_str:
            return 24.0
        try:
            last_run = datetime.fromisoformat(last_run_str).replace(tzinfo=None)
            now = datetime.now().replace(tzinfo=None)
            return (now - last_run).total_seconds() / 3600
        except Exception:
            return 24.0

    def diagnose_interruption_type(self, source_name: str) -> str:
        """诊断中断类型"""
        hours = self.get_downtime_hours(source_name)
        if hours < 2:
            return "normal"
        elif hours < 24:
            return "short_interruption"
        elif hours < 72:
            return "day_interruption"
        else:
            return "long_interruption"

    def update_state(self, source_name: str, latest_pub_date: str, items_count: int):
        """更新信源采集状态"""
        self._state[source_name] = {
            "last_pub_date": latest_pub_date,
            "last_run": datetime.now().isoformat(),
            "last_count": items_count
        }
        self._save_state()


_tracker_instance = None


def get_incremental_tracker() -> IncrementalTracker:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = IncrementalTracker()
    return _tracker_instance
