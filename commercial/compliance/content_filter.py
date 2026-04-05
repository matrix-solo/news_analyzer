#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ææåå®è¿æ¤å?
æ£æµå¶è¿æ¤ææè¯åå®?
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import yaml

@dataclass
class SensitiveMatch:
    """ææè¯åéçæ?""
    keyword: str
    category: str
    level: str
    action: str
    position: int = 0

@dataclass
class ContentFilterResult:
    """åå®è¿æ¤çæ"""
    passed: bool
    content: str
    matches: List[SensitiveMatch] = field(default_factory=list)
    action: str = "pass"
    reason: str = ""

class SensitiveContentFilter:
    """ææåå®è¿æ¤å?""

    def __init__(self, keywords_path: str = None):
        self.logger = logging.getLogger("SensitiveContentFilter")
        self.keywords_path = Path(keywords_path) if keywords_path else None
        self.sensitive_keywords: Dict[str, List[str]] = {}
        self.category_config: Dict[str, Dict] = {}
        self._load_keywords()

    def _load_keywords(self):
    """å è½½ææè¯åº"""
        if not self.keywords_path:
            self.logger.warning("æªæå®ææè¯åºè·¯å¾ïä½¿ç¨ç©ºè¯åº?")
            return

        if not self.keywords_path.exists():
            self.logger.warning(f"ææè¯åºæä¶ä¸å­å? {self.keywords_path}")
            return

        try:
            with open(self.keywords_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            sensitive_config = config.get('sensitive_keywords', {})
            for category, cat_config in sensitive_config.items():
                keywords = cat_config.get('keywords', [])
                self.sensitive_keywords[category] = keywords
                self.category_config[category] = {
                    'description': cat_config.get('description', ''),
                    'level': cat_config.get('level', 'medium'),
                    'action': cat_config.get('action', 'review')
                }

            total_keywords = sum(len(kw) for kw in self.sensitive_keywords.values())
            self.logger.info(f"å è½½ææè¯åº: {len(self.sensitive_keywords)}ä¸ªç±å? å±{total_keywords}ä¸ªææè¯")

        except Exception as e:
            self.logger.error(f"å è½½ææè¯åºå¤±è'¥: {e}"')

    def _find_matches(self, content: str) -> List[SensitiveMatch]:
        """æ¥æ¾åå®ä¸­çææè¯åé?""
        matches = []

        for category, keywords in self.sensitive_keywords.items():
            cat_config = self.category_config.get(category, {})

            for keyword in keywords:
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                search_result = pattern.search(content)

                if search_result:
                    matches.append(SensitiveMatch(
                        keyword=keyword,
                        category=category,
                        level=cat_config.get('level', 'medium'),
                        action=cat_config.get('action', 'review'),
                        position=search_result.start()
                    ))

        return matches

    def filter_content(self, content: str) -> ContentFilterResult:
        """
        è¿æ¤åå®

        Args:
            content: å¾è¿æ¤çåå®

        Returns:
            ContentFilterResult: è¿æ¤çæ
        """
        if not content:
            return ContentFilterResult(
                passed=True,
                content=content,
                action="pass",
                reason="åå®ä¸ºç©º"
            )

        matches = self._find_matches(content)

        if not matches:
            return ContentFilterResult(
                passed=True,
                content=content,
                action="pass",
                reason="æªæ£æµå°ææè¯?"
            )

        high_level_matches = [m for m in matches if m.level == 'high']

        if high_level_matches:
            keywords_str = ', '.join([m.keyword for m in high_level_matches])
            self.logger.warning(f"æ£æµå°é«å±ææè¯? {keywords_str}")
            return ContentFilterResult(
                passed=False,
                content=content,
                matches=matches,
                action="reject",
                reason=f"æ£æµå°é«å±ææè¯? {keywords_str}"
            )

        review_matches = [m for m in matches if m.action == 'review']
        if review_matches:
            keywords_str = ', '.join([m.keyword for m in review_matches])
            self.logger.info(f"åå®éè¦äººå·¥å®¡æ ? {keywords_str}")
            return ContentFilterResult(
                passed=True,
                content=content,
                matches=matches,
                action="review",
                reason=f"æ£æµå°éå®¡æ ¸åå®: {keywords_str}"
            )

        reject_matches = [m for m in matches if m.action == 'reject']
        if reject_matches:
            keywords_str = ', '.join([m.keyword for m in reject_matches])
            return ContentFilterResult(
                passed=False,
                content=content,
                matches=matches,
                action="reject",
                reason=f"æ£æµå°ç¦æ­åå®: {keywords_str}"
            )

        return ContentFilterResult(
            passed=True,
            content=content,
            matches=matches,
            action="pass",
            reason="åå®éè¿æ£æµ?"
        )

    def filter_batch(self, contents: List[str]) -> List[ContentFilterResult]:
        """
        æéè¿æ¤åå®

        Args:
            contents: åå®åè¡¨

        Returns:
            List[ContentFilterResult]: è¿æ¤çæåè¡¨
        """
        return [self.filter_content(content) for content in contents]

    def add_keyword(self, keyword: str, category: str, level: str = 'medium', action: str = 'review'):
        """
        æ·å ææè¯?

        Args:
            keyword: ææè¯?
            category: ç±å«
            level: çºå« (high/medium/low)
            action: å¨ä½ (reject/review)
        """
        if category not in self.sensitive_keywords:
            self.sensitive_keywords[category] = []
            self.category_config[category] = {
                'description': f'èªå®äç±å? {category}',
                'level': level,
                'action': action
            }

        if keyword not in self.sensitive_keywords[category]:
            self.sensitive_keywords[category].append(keyword)
            self.logger.info(f"æ·å ææè¯? {keyword} -> {category}")

    def remove_keyword(self, keyword: str) -> bool:
        """
        çé¤ææè¯?

        Args:
            keyword: ææè¯?

        Returns:
            bool: æ¯å¦æåçé¤
        """
        for category, keywords in self.sensitive_keywords.items():
            if keyword in keywords:
                keywords.remove(keyword)
                self.logger.info(f"çé¤ææè¯? {keyword}")
                return True
        return False

    def get_all_keywords(self) -> Dict[str, List[str]]:
    """è·åææææè¯"""
        return self.sensitive_keywords.copy()

    def get_keywords_by_category(self, category: str) -> List[str]:
    """è·åæå®ç±å«çææè¯"""
        return self.sensitive_keywords.get(category, [])

    def get_stats(self) -> Dict:
    """è·åçè®¡ä¿¡æ¯"""
        return {
            'total_categories': len(self.sensitive_keywords),
            'total_keywords': sum(len(kw) for kw in self.sensitive_keywords.values()),
            'by_category': {
                cat: len(kw) for cat, kw in self.sensitive_keywords.items()
            }
        }
