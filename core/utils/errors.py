#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错误类型定义"""

class NewsAnalyzerError(Exception):
    """基础错误类"""
    pass

class CollectionError(NewsAnalyzerError):
    pass

class ProcessingError(NewsAnalyzerError):
    pass

class StorageError(NewsAnalyzerError):
    pass
