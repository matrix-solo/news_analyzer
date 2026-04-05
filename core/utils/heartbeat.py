#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心跳监控模块 - 任务运行状态追踪与告警

功能：
1. 任务启动/结束记录心跳
2. 超时检测与告警
3. 运行状态查询
"""

import os
import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger("Heartbeat")

_project_root = Path(__file__).parent.parent.parent
_heartbeat_dir = _project_root / "data" / "heartbeats"

_TIMEOUT_MINUTES = int(os.getenv("HEARTBEAT_TIMEOUT_MINUTES", "120"))


@dataclass
class HeartbeatStatus:
    """心跳状态"""
    task_name: str
    status: str          # running / success / failed / timeout
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    progress: int = 0    # 0-100
    message: str = ""
    error: Optional[str] = None


class HeartbeatMonitor:
    """心跳监控器（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        _heartbeat_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True

    def start(self, task_name: str, message: str = "") -> HeartbeatStatus:
        """任务启动，记录心跳"""
        status = HeartbeatStatus(
            task_name=task_name,
            status="running",
            start_time=datetime.now().isoformat(),
            message=message
        )
        self._save(status)
        logger.info(f"[{task_name}] 开始运行")
        return status

    def update(self, task_name: str, progress: int, message: str = ""):
        """更新进度"""
        status = self._load(task_name)
        if status:
            status.progress = min(max(progress, 0), 100)
            status.message = message
            self._save(status)

    def success(self, task_name: str, message: str = ""):
        """任务成功完成"""
        status = self._load(task_name)
        if status:
            now = datetime.now()
            start = datetime.fromisoformat(status.start_time)
            status.status = "success"
            status.end_time = now.isoformat()
            status.duration_seconds = (now - start).total_seconds()
            status.progress = 100
            status.message = message or "执行成功"
            self._save(status)
            logger.info(f"[{task_name}] 执行成功，耗时 {status.duration_seconds:.1f}s")

    def fail(self, task_name: str, error: str = ""):
        """任务失败"""
        status = self._load(task_name)
        if status:
            now = datetime.now()
            start = datetime.fromisoformat(status.start_time)
            status.status = "failed"
            status.end_time = now.isoformat()
            status.duration_seconds = (now - start).total_seconds()
            status.error = error
            self._save(status)
            logger.error(f"[{task_name}] 执行失败: {error}")

    def check_timeout(self, task_name: str) -> bool:
        """
        检查任务是否超时

        Returns:
            True 表示已超时
        """
        status = self._load(task_name)
        if not status or status.status != "running":
            return False

        start = datetime.fromisoformat(status.start_time)
        timeout_at = start + timedelta(minutes=_TIMEOUT_MINUTES)
        if datetime.now() > timeout_at:
            status.status = "timeout"
            status.error = f"超时（>{_TIMEOUT_MINUTES}分钟）"
            self._save(status)
            logger.warning(f"[{task_name}] 任务超时")
            return True
        return False

    def get_status(self, task_name: str) -> Optional[HeartbeatStatus]:
        """获取单个任务状态"""
        return self._load(task_name)

    def get_all_status(self) -> Dict[str, HeartbeatStatus]:
        """获取所有任务状态"""
        result = {}
        for f in _heartbeat_dir.glob("*.json"):
            task_name = f.stem
            s = self._load(task_name)
            if s:
                result[task_name] = s
        return result

    def cleanup_old_status(self, days: int = 7):
        """清理旧的心跳记录"""
        cutoff = datetime.now() - timedelta(days=days)
        for f in _heartbeat_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                end_time_str = data.get("end_time")
                if end_time_str:
                    end_time = datetime.fromisoformat(end_time_str)
                    if end_time < cutoff:
                        f.unlink()
            except Exception:
                pass

    def _save(self, status: HeartbeatStatus):
        hb_file = _heartbeat_dir / f"{status.task_name}.json"
        hb_file.write_text(json.dumps(asdict(status), ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self, task_name: str) -> Optional[HeartbeatStatus]:
        hb_file = _heartbeat_dir / f"{task_name}.json"
        if not hb_file.exists():
            return None
        try:
            data = json.loads(hb_file.read_text(encoding="utf-8"))
            return HeartbeatStatus(**data)
        except Exception as e:
            logger.warning(f"读取心跳文件失败 {hb_file}: {e}")
            return None


# 模块级便捷访问
def heartbeat(task_name: str) -> HeartbeatMonitor:
    """获取心跳监控器并自动启动任务记录"""
    monitor = HeartbeatMonitor()
    monitor.start(task_name)
    return monitor


def get_heartbeat_monitor() -> HeartbeatMonitor:
    return HeartbeatMonitor()
