#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理模块
"""

import re
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class FileManager:
    """文件管理器"""
    
    ILLEGAL_CHARS = r'[<>:"/\\|?*]'
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path('.')
    
    def safe_filename(self, name: str, max_length: int = 200) -> str:
        """生成安全的文件名"""
        safe_name = re.sub(self.ILLEGAL_CHARS, '_', name)
        safe_name = safe_name.strip('. ')
        
        name_upper = safe_name.upper()
        if name_upper in self.RESERVED_NAMES:
            safe_name = f"_{safe_name}"
        
        if len(safe_name) > max_length:
            safe_name = safe_name[:max_length]
        
        return safe_name or 'unnamed'
    
    def ensure_dir(self, dir_path: Path) -> Path:
        """确保目录存在"""
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def write_json(self, file_path: Path, data: dict, indent: int = 2):
        """写入JSON文件"""
        import json
        self.ensure_dir(file_path.parent)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
    
    def read_json(self, file_path: Path) -> dict:
        """读取JSON文件"""
        import json
        if not file_path.exists():
            return {}
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def write_text(self, file_path: Path, content: str):
        """写入文本文件"""
        self.ensure_dir(file_path.parent)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def read_text(self, file_path: Path) -> str:
        """读取文本文件"""
        if not file_path.exists():
            return ''
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
