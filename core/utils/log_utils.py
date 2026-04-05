#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志工具模块 - 包含日志脱敏功能
"""

import re
import logging
from typing import Any, Dict, List, Optional


# 敏感信息正则模式
SENSITIVE_PATTERNS = [
    # API密钥（降低最小长度要求）
    (r'(api[_-]?key[=:]\s*)[a-zA-Z0-9_\-]{8,}', r'\1***REDACTED***'),
    (r'(ark[_-]?api[_-]?key[=:]\s*)[a-zA-Z0-9_\-]{8,}', r'\1***REDACTED***'),
    (r'(deepseek[_-]?api[_-]?key[=:]\s*)[a-zA-Z0-9_\-]{8,}', r'\1***REDACTED***'),
    (r'(qwen[_-]?api[_-]?key[=:]\s*)[a-zA-Z0-9_\-]{8,}', r'\1***REDACTED***'),
    (r'(dashscope[_-]?api[_-]?key[=:]\s*)[a-zA-Z0-9_\-]{8,}', r'\1***REDACTED***'),
    
    # Bearer Token
    (r'(bearer\s+)[a-zA-Z0-9_\-\.]{8,}', r'\1***REDACTED***'),
    
    # 邮箱
    (r'[\w\.-]+@[\w\.-]+\.\w+', '***@***.***'),
    
    # 手机号（中国）
    (r'1[3-9]\d{9}', '1**********'),
    
    # 身份证号
    (r'\d{17}[\dXx]', '******************'),
    
    # 银行卡号
    (r'\d{16,19}', '***************'),
    
    # 密码字段
    (r'(password[=:]\s*)\S+', r'\1***REDACTED***'),
    (r'(smtp[_-]?password[=:]\s*)\S+', r'\1***REDACTED***'),
    
    # URL中的敏感参数
    (r'([?&](?:token|key|secret|password|auth)=[^&\s]+)', r'\1=***REDACTED***'),
]


def sanitize_text(text: str) -> str:
    """
    脱敏文本中的敏感信息
    
    Args:
        text: 原始文本
    
    Returns:
        脱敏后的文本
    """
    if not text or not isinstance(text, str):
        return text
    
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


def sanitize_dict(data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    脱敏字典中的敏感信息
    
    Args:
        data: 原始字典
        sensitive_keys: 额外的敏感键名列表
    
    Returns:
        脱敏后的字典
    """
    if not isinstance(data, dict):
        return data
    
    default_sensitive_keys = [
        'password', 'pwd', 'secret', 'token', 'api_key', 'apikey',
        'auth', 'credential', 'private_key', 'access_key'
    ]
    
    all_sensitive_keys = set(default_sensitive_keys)
    if sensitive_keys:
        all_sensitive_keys.update(k.lower() for k in sensitive_keys)
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # 敏感键直接脱敏
        if any(sk in key_lower for sk in all_sensitive_keys):
            sanitized[key] = '***REDACTED***'
        elif isinstance(value, str):
            sanitized[key] = sanitize_text(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, sensitive_keys)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item, sensitive_keys) if isinstance(item, dict)
                else sanitize_text(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized


class SanitizedLogger:
    """自动脱敏的日志记录器"""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def _sanitize_args(self, *args, **kwargs) -> tuple:
        """脱敏参数"""
        sanitized_args = tuple(
            sanitize_text(arg) if isinstance(arg, str)
            else sanitize_dict(arg) if isinstance(arg, dict)
            else arg
            for arg in args
        )
        return sanitized_args
    
    def debug(self, msg, *args, **kwargs):
        self._logger.debug(sanitize_text(str(msg)), *self._sanitize_args(*args), **kwargs)
    
    def info(self, msg, *args, **kwargs):
        self._logger.info(sanitize_text(str(msg)), *self._sanitize_args(*args), **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self._logger.warning(sanitize_text(str(msg)), *self._sanitize_args(*args), **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._logger.error(sanitize_text(str(msg)), *self._sanitize_args(*args), **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        self._logger.critical(sanitize_text(str(msg)), *self._sanitize_args(*args), **kwargs)


def get_sanitized_logger(name: str) -> SanitizedLogger:
    """
    获取自动脱敏的日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        SanitizedLogger 实例
    """
    return SanitizedLogger(logging.getLogger(name))


class SensitiveInfoFilter(logging.Filter):
    """日志过滤器 - 自动脱敏敏感信息"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录"""
        if record.msg:
            record.msg = sanitize_text(str(record.msg))
        
        if record.args:
            record.args = tuple(
                sanitize_text(arg) if isinstance(arg, str)
                else sanitize_dict(arg) if isinstance(arg, dict)
                else arg
                for arg in record.args
            )
        
        return True


def setup_secure_logging():
    """
    配置安全的日志记录
    
    在应用启动时调用此函数，确保所有日志都经过脱敏处理
    """
    # 获取根日志记录器
    root_logger = logging.getLogger()
    
    # 添加敏感信息过滤器
    sensitive_filter = SensitiveInfoFilter()
    
    for handler in root_logger.handlers:
        handler.addFilter(sensitive_filter)
    
    # 为所有现有日志记录器添加过滤器
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers:
                handler.addFilter(sensitive_filter)
