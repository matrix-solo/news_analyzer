#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻过滤器模块

提供信源校验功能
"""

from .source_validator import SourceValidator, ValidationResult

__all__ = [
    'SourceValidator',
    'ValidationResult',
]
