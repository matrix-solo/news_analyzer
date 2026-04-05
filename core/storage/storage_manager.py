#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存储管理模块 - 文件存储管理
"""

import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class StorageManager:
    """存储管理器 - 管理文件存储（baseline / rejected_news / filter_logs）"""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            from core.config.loader import PROJECT_ROOT
            base_dir = Path(PROJECT_ROOT) / "data"

        self.base_dir = Path(base_dir)
        self.rejected_news = self.base_dir / "rejected_news"
        self.baseline_dir = self.base_dir / "baseline"
        self.filter_logs = self.base_dir / "filter_logs"

        for d in [self.rejected_news, self.baseline_dir, self.filter_logs]:
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error(f"创建目录失败 {d}: {e}")
                raise
    
    def _safe_filename(self, name: str) -> str:
        """生成安全的文件名"""
        illegal_chars = r'[<>"/\\|?*]'
        safe_name = re.sub(illegal_chars, '_', name)
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        return safe_name.strip()

    def save_baseline(self, news_ids: List[str], date_str: str = None) -> bool:
        """保存基线（已处理新闻ID）"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        baseline_file = self.baseline_dir / f"baseline_{date_str}.json"
        
        existing = set()
        if baseline_file.exists():
            try:
                with open(baseline_file, 'r', encoding='utf-8') as f:
                    existing = set(json.load(f))
            except (IOError, json.JSONDecodeError) as e:
                logger.warning(f"读取基线文件失败 {baseline_file}: {e}")
                existing = set()
        
        existing.update(news_ids)
        
        try:
            with open(baseline_file, 'w', encoding='utf-8') as f:
                json.dump(list(existing), f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"保存基线文件失败 {baseline_file}: {e}")
            raise
        
        return True
    
    def load_baseline(self, days: int = 90) -> set:
        """加载基线（已处理新闻ID）"""
        all_ids = set()
        
        for baseline_file in self.baseline_dir.glob('baseline_*.json'):
            try:
                with open(baseline_file, 'r', encoding='utf-8') as f:
                    ids = json.load(f)
                    if isinstance(ids, list):
                        all_ids.update(ids)
            except (IOError, json.JSONDecodeError) as e:
                logger.warning(f"读取基线文件失败 {baseline_file}: {e}")
        
        return all_ids


def get_storage() -> StorageManager:
    """获取存储管理器实例"""
    return StorageManager()
