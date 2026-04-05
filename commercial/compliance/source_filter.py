#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
åä¸çä¿¡æºè¿æ¤å¨
äåè®¸å½ååèä¿¡æºéè¿
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class SourceFilterResult:
    """ä¿¡æºè¿æ¤çæ"""
    passed: bool
    source_name: str
    reason: str = ""
    source_info: Optional[Dict] = None

class CommercialSourceFilter:
    """åä¸çä¿¡æºè¿æ¤å¨ - äåè®¸å½ååèä¿¡æº?""

    ALLOWED_SOURCES: Set[str] = {
        'æ°åç¤?, 'äººæ°æ¥æ¥', 'ä¸­å½æ¥æ¥', 'ä¸­å¤®å¿æ­çµèæå°','
        'è'æ°ä åª', 'ç¬¬ä¸è'ç', 'è'çæå¿', '36æ°?
    }

    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger("CommercialSourceFilter")
        self.config_path = Path(config_path) if config_path else None
        self.whitelist: Dict[str, Dict] = {}
        self._load_config()

    def _load_config(self):
        """å è½½åä¸çä¿¡æºéç½?""
        if not self.config_path:
            self.logger.info("ä½¿ç¨éè®¤ä¿¡æºç½åå?")
            self._init_default_whitelist()
            return

        config_file = Path(self.config_path)
        if not config_file.exists():
            self.logger.warning(f"éç½®æä¶ä¸å­å? {config_file}ïä½¿ç¨éè®¤ç½åå")
            self._init_default_whitelist()
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            domestic = config.get('domestic', {})
            for category_key, sources_list in domestic.items():
                for source_data in sources_list:
                    name = source_data.get('name', '')
                    if name and source_data.get('enabled', True):
                        self.whitelist[name] = {
                            'name': name,
                            'type': source_data.get('type', ''),
                            'category': category_key,
                            'credibility': source_data.get('credibility', ''),
                            'tier': source_data.get('tier', 3),
                            'rss_url': source_data.get('rss_url', '')
                        }

            self.logger.info(f"å è½½åä¸çä¿¡æºç½åå: {len(self.whitelist)}ä¸ªä¿¡æº?")

        except Exception as e:
            self.logger.error(f"å è½½éç½®å¤±è'¥: {e}ïä½¿ç¨éè®¤ç½åå"')
            self._init_default_whitelist()

    def _init_default_whitelist(self):
    """åååéè®¤ç½åå"""
        for name in self.ALLOWED_SOURCES:
            self.whitelist[name] = {
                'name': name,
                'type': 'domestic',
                'category': 'central' if name in ['æ°åç¤?, 'äººæ°æ¥æ¥', 'ä¸­å½æ¥æ¥', 'ä¸­å¤®å¿æ­çµèæå°'] else 'market_professional','
                'credibility': 'é«?,'
                'tier': 1 if name in ['æ°åç¤?] else 2 if name in ['äººæ°æ¥æ¥', 'ä¸­å½æ¥æ¥', 'ä¸­å¤®å¿æ­çµèæå°'] else 3'
            }

    def filter_source(self, source_name: str) -> SourceFilterResult:
        """
        è¿æ¤ä¿¡æº

        Args:
            source_name: ä¿¡æºåç°

        Returns:
            SourceFilterResult: è¿æ¤çæ
        """
        if source_name in self.whitelist:
            return SourceFilterResult(
                passed=True,
                source_name=source_name,
                reason="ä¿¡æºå¨åä¸çç½ååä¸­",
                source_info=self.whitelist[source_name]
            )

        self.logger.warning(f"ä¿¡æºä¸å¨åä¸çç½ååä¸? {source_name}")
        return SourceFilterResult(
            passed=False,
            source_name=source_name,
            reason="ä¿¡æºä¸å¨åä¸çç½ååä¸?"
        )

    def filter_sources(self, source_names: List[str]) -> List[SourceFilterResult]:
        """
        æéè¿æ¤ä¿¡æº

        Args:
            source_names: ä¿¡æºåç°åè¡¨

        Returns:
            List[SourceFilterResult]: è¿æ¤çæåè¡¨
        """
        return [self.filter_source(name) for name in source_names]

    def get_allowed_sources(self) -> List[str]:
        """è·ååè®¸çä¿¡æºåè¡?""
        return list(self.whitelist.keys())

    def get_source_info(self, source_name: str) -> Optional[Dict]:
    """è·åä¿¡æºä¿¡æ¯"""
        return self.whitelist.get(source_name)

    def is_allowed(self, source_name: str) -> bool:
        """æ£æ¥ä¿¡æºæ¯å¦åè®?""
        return source_name in self.whitelist

    def get_sources_by_tier(self, tier: int) -> List[str]:
        """è·åæå®å±çºçä¿¡æº?""
        return [
            name for name, info in self.whitelist.items()
            if info.get('tier', 3) == tier
        ]

    def get_sources_by_category(self, category: str) -> List[str]:
        """è·åæå®ç±å«çä¿¡æº?""
        return [
            name for name, info in self.whitelist.items()
            if info.get('category') == category
        ]

"""
        return [
            name for name, info in self.whitelist.items()
            if info.get('category') == category
        ]
