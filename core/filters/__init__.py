#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

新闻过滤器模实现5步判断逻辑:白名单校验 可信度校内容属性校冗余去重 AI判断

支持AI判断W1H检测、去重)

"""

from .source_validator import SourceValidator, ValidationResult

from .deduplication import DeduplicationFilter, DedupResult

from .ai_filter_agent import AIFilterAgent, AIFactCheckResult, AIDedupResult, AIFilterLog

__all__ = [

    'SourceValidator',

    'ValidationResult',

    'DeduplicationFilter',

    'DedupResult',

    'AIFilterAgent',

    'AIFactCheckResult',

    'AIDedupResult',

    'AIFilterLog'

]
