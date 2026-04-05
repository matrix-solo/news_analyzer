#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 兜底抽取器（第一阶段：接口就绪，默认轻量）

策略：
- 仅在规则解析结果置信度不足时调用
- 当前实现优先做：标签抽取（可选）与摘要补全（可选）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.processor.ai_processor import AIProcessor

logger = logging.getLogger(__name__)


@dataclass
class AIFallbackResult:
    domain: Optional[str] = None
    tags: List[str] = None
    summary: Optional[str] = None
    used: bool = False


class AIFallbackExtractor:
    def __init__(self, ai_processor: Optional[AIProcessor] = None):
        self.ai = ai_processor or AIProcessor()

    def enrich(
        self,
        news: Dict[str, Any],
        *,
        enable_tags: bool = True,
        enable_summary: bool = False,
        max_tags: int = 5,
        purpose: str = "FILTER",
    ) -> AIFallbackResult:
        content = (news.get("content") or "").strip()
        if not content:
            return AIFallbackResult(domain=None, tags=[], summary=None, used=False)

        tags: List[str] = []
        summary: Optional[str] = None

        try:
            if enable_tags:
                tags = self.ai.extract_tags(content, max_tags=max_tags, purpose=purpose) or []
        except Exception as e:
            logger.warning(f"AI兜底标签抽取失败: {e}")

        try:
            if enable_summary and not news.get("short_summary"):
                summary = self.ai.generate_summary(content, purpose=purpose)
        except Exception as e:
            logger.warning(f"AI兜底摘要生成失败: {e}")

        return AIFallbackResult(domain=None, tags=tags, summary=summary, used=bool(tags or summary))

