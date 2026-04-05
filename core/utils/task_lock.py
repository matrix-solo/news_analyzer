#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务锁模块 - 防止定时任务并发冲突

用途：确保同一时间只有一个同类任务在运行
跨平台支持：
- Windows: 基于文件存储 PID + 时间戳的锁
- Unix/Linux: 使用 fcntl 文件锁
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_project_root = Path(__file__).parent.parent.parent
_lock_dir = _project_root / "data" / "locks"


class TaskLock:
    """跨平台任务锁"""

    DEFAULT_TIMEOUT = 7200  # 默认超时 2 小时

    def __init__(self, task_name: str, timeout: int = DEFAULT_TIMEOUT):
        self.task_name = task_name
        self.timeout = timeout
        _lock_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = _lock_dir / f"{task_name}.lock"
        self._lock_handle = None

    def acquire(self, blocking: bool = True) -> bool:
        """获取锁，返回 True 表示成功"""
        if sys.platform == "win32":
            return self._acquire_windows(blocking)
        else:
            return self._acquire_unix(blocking)

    def _acquire_windows(self, blocking: bool) -> bool:
        """Windows 文件锁实现"""
        if self.lock_file.exists():
            if self._is_lock_expired():
                logger.warning(f"[{self.task_name}] 发现过期锁，强制释放")
                self._force_release()
            else:
                if not blocking:
                    logger.info(f"[{self.task_name}] 锁已被占用")
                    return False
                logger.info(f"[{self.task_name}] 等待锁释放...")
                while self.lock_file.exists() and not self._is_lock_expired():
                    time.sleep(1)
                if self._is_lock_expired():
                    self._force_release()

        try:
            lock_data = {
                "pid": os.getpid(),
                "task": self.task_name,
                "start_time": datetime.now().isoformat(),
                "timeout": self.timeout,
                "expire_at": (datetime.now() + timedelta(seconds=self.timeout)).isoformat()
            }
            self.lock_file.write_text(json.dumps(lock_data, ensure_ascii=False), encoding="utf-8")
            logger.debug(f"[{self.task_name}] 锁已获取 (PID={os.getpid()})")
            return True
        except Exception as e:
            logger.error(f"[{self.task_name}] 获取锁失败: {e}")
            return False

    def _acquire_unix(self, blocking: bool) -> bool:
        """Unix fcntl 文件锁实现"""
        import fcntl
        try:
            self._lock_handle = open(self.lock_file, "w")
            flag = fcntl.LOCK_EX if blocking else (fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                fcntl.flock(self._lock_handle, flag)
                self._lock_handle.write(str(os.getpid()))
                self._lock_handle.flush()
                return True
            except IOError:
                self._lock_handle.close()
                self._lock_handle = None
                return False
        except Exception as e:
            logger.error(f"[{self.task_name}] 获取锁失败: {e}")
            return False

    def release(self):
        """释放锁"""
        if sys.platform == "win32":
            try:
                if self.lock_file.exists():
                    self.lock_file.unlink()
                    logger.debug(f"[{self.task_name}] 锁已释放")
            except Exception as e:
                logger.warning(f"[{self.task_name}] 释放锁失败: {e}")
        else:
            import fcntl
            if self._lock_handle:
                try:
                    fcntl.flock(self._lock_handle, fcntl.LOCK_UN)
                    self._lock_handle.close()
                    self._lock_handle = None
                    if self.lock_file.exists():
                        self.lock_file.unlink()
                except Exception as e:
                    logger.warning(f"[{self.task_name}] 释放锁失败: {e}")

    def _is_lock_expired(self) -> bool:
        """检查锁是否已超时"""
        try:
            data = json.loads(self.lock_file.read_text(encoding="utf-8"))
            expire_at = datetime.fromisoformat(data["expire_at"])
            return datetime.now() > expire_at
        except Exception:
            return True  # 解析失败视为过期

    def _force_release(self):
        """强制释放锁（清除过期/僵尸锁）"""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception as e:
            logger.warning(f"[{self.task_name}] 强制释放锁失败: {e}")

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"无法获取任务锁: {self.task_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


@contextmanager
def task_lock(task_name: str, timeout: int = TaskLock.DEFAULT_TIMEOUT, blocking: bool = True):
    """
    任务锁上下文管理器

    Usage:
        with task_lock("collect"):
            do_collect()
    """
    lock = TaskLock(task_name, timeout)
    acquired = lock.acquire(blocking=blocking)
    if not acquired:
        logger.warning(f"[{task_name}] 任务已在运行，跳过本次执行")
        raise RuntimeError(f"无法获取任务锁: {task_name}")
    try:
        yield lock
    finally:
        lock.release()


def check_lock_status(task_name: str) -> dict:
    """查询锁状态"""
    lock_file = _lock_dir / f"{task_name}.lock"
    if not lock_file.exists():
        return {"locked": False, "pid": None, "start_time": None, "expire_at": None}

    try:
        data = json.loads(lock_file.read_text(encoding="utf-8"))
        expire_at = datetime.fromisoformat(data.get("expire_at", ""))
        is_expired = datetime.now() > expire_at
        return {
            "locked": not is_expired,
            "pid": data.get("pid"),
            "start_time": data.get("start_time"),
            "expire_at": data.get("expire_at"),
            "expired": is_expired
        }
    except Exception:
        return {"locked": True, "pid": None, "start_time": None, "expire_at": None}
