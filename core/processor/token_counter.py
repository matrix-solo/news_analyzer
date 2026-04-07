#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token 用量计数器 - 按天统计，超阈值自动切换

设计：
  - 在 BaseProvider.chat() 中作为副作用记录 response.usage
  - 按天自动重置（key 为 "2026-04-08" 格式）
  - 持久化到 data/token_usage.json（CI 中通过 actions/cache 缓存）
  - 超阈值时抛出 TokenLimitExceeded，触发 BACKUP provider 切换
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TokenLimitExceeded(Exception):
    """模型当日 token 用量超过阈值时抛出"""

    def __init__(self, model: str, used: int, limit: int, threshold: float):
        self.model = model
        self.used = used
        self.limit = limit
        self.threshold = threshold
        super().__init__(
            f"Token limit threshold reached for {model}: "
            f"{used:,}/{limit:,} ({used / limit * 100:.1f}% >= {threshold * 100:.0f}%)"
        )


class TokenCounter:
    """
    线程安全的 token 用量追踪器，按天自动重置。

    持久化格式（data/token_usage.json）:
    {
        "2026-04-08": {
            "doubao-seed-2-0-latest": {
                "prompt_tokens": 123456,
                "completion_tokens": 78901,
                "total_tokens": 202357,
                "api_calls": 42,
                "last_updated": "2026-04-08T12:00:00"
            }
        },
        "_metadata": {"version": 1, "created_at": "..."}
    }
    """

    _instance: Optional["TokenCounter"] = None
    _init_lock = threading.Lock()

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data")
        self.usage_file = self.data_dir / "token_usage.json"
        self._cache: Dict = {}
        self._file_lock = threading.Lock()
        self._load()

    @classmethod
    def get_instance(cls) -> "TokenCounter":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ─── 持久化 ──────────────────────────────────────────────────────────

    def _load(self):
        """从磁盘加载数据，损坏时优雅降级"""
        try:
            if self.usage_file.exists():
                with open(self.usage_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                self._cleanup_old_days()
                return
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.warning(f"Token usage 文件损坏/缺失，从零开始: {e}")
        self._cache = {"_metadata": {"version": 1, "created_at": datetime.now().isoformat()}}

    def _save(self):
        """持久化到磁盘，失败时仅记录日志"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.usage_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except (IOError, OSError) as e:
            logger.error(f"Token usage 持久化失败: {e}")

    def _cleanup_old_days(self, keep_days: int = 7):
        """清理 N 天前的历史数据"""
        today = datetime.now()
        keys_to_remove = []
        for key in self._cache:
            if key.startswith("_"):
                continue
            try:
                key_date = datetime.strptime(key, "%Y-%m-%d")
                if (today - key_date).days > keep_days:
                    keys_to_remove.append(key)
            except ValueError:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._cache[key]
        if keys_to_remove:
            self._save()

    # ─── 核心操作 ─────────────────────────────────────────────────────────

    @staticmethod
    def _today() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int) -> Dict:
        """
        记录一次 API 调用的 token 用量（线程安全）。

        Returns:
            当天该模型的累计用量 dict
        """
        day = self._today()

        with self._file_lock:
            if day not in self._cache:
                self._cache[day] = {}

            if model not in self._cache[day]:
                self._cache[day][model] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "api_calls": 0,
                    "last_updated": None,
                }

            entry = self._cache[day][model]
            entry["prompt_tokens"] += prompt_tokens
            entry["completion_tokens"] += completion_tokens
            entry["total_tokens"] += prompt_tokens + completion_tokens
            entry["api_calls"] += 1
            entry["last_updated"] = datetime.now().isoformat()

            self._save()

        return entry

    def get_usage(self, model: str) -> Dict:
        """获取当天某模型的累计用量"""
        day = self._today()
        return self._cache.get(day, {}).get(
            model,
            {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "api_calls": 0},
        )

    # ─── 阈值检查 ─────────────────────────────────────────────────────────

    def get_limit(self, model: str) -> int:
        """获取某模型的 token 日限额。0 表示不限制。"""
        # 优先级: env var > core_config.yaml > 0 (不限制)
        env_key = f"AI_TOKEN_LIMIT_{model.upper().replace('-', '_').replace('.', '_')}"
        val = os.getenv(env_key)
        if val:
            try:
                return int(val)
            except ValueError:
                pass

        try:
            from core.config.manager import get_config_manager

            mgr = get_config_manager()
            cfg = mgr.get("token_limits")
            if cfg:
                # 查找模型级别配置
                models_cfg = cfg.get("models", {})
                if model in models_cfg:
                    return int(models_cfg[model].get("limit", 0))
                # 使用默认值
                default = cfg.get("default_limit", 0)
                return int(default)
        except Exception:
            pass

        # 最后检查通用 env var
        default_env = os.getenv("AI_TOKEN_LIMIT_DEFAULT", "0")
        try:
            return int(default_env)
        except ValueError:
            return 0

    def get_threshold(self, model: str) -> float:
        """获取触发切换的阈值比例 (0.0-1.0)"""
        env_key = f"AI_TOKEN_THRESHOLD_{model.upper().replace('-', '_').replace('.', '_')}"
        val = os.getenv(env_key)
        if val:
            try:
                return float(val)
            except ValueError:
                pass

        try:
            from core.config.manager import get_config_manager

            mgr = get_config_manager()
            cfg = mgr.get("token_limits")
            if cfg:
                models_cfg = cfg.get("models", {})
                if model in models_cfg:
                    return float(models_cfg[model].get("threshold", 0.9))
                return float(cfg.get("default_threshold", 0.9))
        except Exception:
            pass

        default_env = os.getenv("AI_TOKEN_THRESHOLD_DEFAULT", "0.9")
        try:
            return float(default_env)
        except ValueError:
            return 0.9

    def is_over_threshold(self, model: str) -> bool:
        """检查某模型今天是否已超过阈值"""
        limit = self.get_limit(model)
        if limit <= 0:
            return False  # 未配置限额
        usage = self.get_usage(model)
        threshold = self.get_threshold(model)
        return usage.get("total_tokens", 0) >= limit * threshold

    def check_and_raise(self, model: str) -> None:
        """
        检查阈值，超限则抛出 TokenLimitExceeded。
        在 BaseProvider.chat() 开头调用。
        """
        limit = self.get_limit(model)
        if limit <= 0:
            return  # 未配置限额，放行
        usage = self.get_usage(model)
        total = usage.get("total_tokens", 0)
        threshold = self.get_threshold(model)
        if total >= limit * threshold:
            raise TokenLimitExceeded(model, total, limit, threshold)

    def get_stats(self) -> Dict:
        """获取当天的统计摘要（供日志/报告使用）"""
        day = self._today()
        day_data = self._cache.get(day, {})
        stats = {}
        for model, data in day_data.items():
            limit = self.get_limit(model)
            total = data.get("total_tokens", 0)
            stats[model] = {
                "total_tokens": total,
                "api_calls": data.get("api_calls", 0),
                "limit": limit,
                "usage_pct": round(total / limit * 100, 1) if limit > 0 else None,
                "over_threshold": self.is_over_threshold(model),
            }
        return stats
