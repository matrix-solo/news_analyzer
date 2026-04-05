#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
éåæ å°å?
å°ææéåæ å°ä¸ºåèè¡¨è¿°
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class FieldMappingRule:
    """éåæ å°èå"""
    original: str
    mapped: str
    description: str = ""

class FieldMapper:
    """éåæ å°å?""

    DEFAULT_MAPPINGS: Dict[str, str] = {
        'æ¿æ²': 'å®èå¨æ?,'
        'æ¶æ¿': 'æ¶äºè¦é',
        'æ¿ç­': 'æ¿ç­è£è¯'
    }

    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger("FieldMapper")
        self.config_path = Path(config_path) if config_path else None
        self.mappings: Dict[str, FieldMappingRule] = {}
        self._load_config()

    def _load_config(self):
    """å è½½æ å°éç½®"""
        self._init_default_mappings()

        if not self.config_path:
            return

        if not self.config_path.exists():
            self.logger.warning(f"éç½®æä¶ä¸å­å? {self.config_path}")
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            field_mapping = config.get('field_mapping', {})
            rules = field_mapping.get('rules', [])

            for rule in rules:
                original = rule.get('original', '')
                mapped = rule.get('mapped', '')
                description = rule.get('description', '')

                if original and mapped:
                    self.mappings[original] = FieldMappingRule(
                        original=original,
                        mapped=mapped,
                        description=description
                    )

            self.logger.info(f"å è½½éåæ å°èå: {len(self.mappings)}æ?")

        except Exception as e:
            self.logger.error(f"å è½½æ å°éç½®å¤±è'¥: {e}"')

    def _init_default_mappings(self):
        """åååéè®¤æ å°?""
        for original, mapped in self.DEFAULT_MAPPINGS.items():
            self.mappings[original] = FieldMappingRule(
                original=original,
                mapped=mapped,
                description=f"éè®¤æ å°: {original} -> {mapped}"
            )

    def map_field(self, field: str) -> str:
        """
        æ å°éå

        Args:
            field: ååéååç°

        Returns:
            str: æ å°åçéååç°
        """
        if field in self.mappings:
            mapped = self.mappings[field].mapped
            self.logger.debug(f"éåæ å°: {field} -> {mapped}")
            return mapped

        return field

    def map_fields(self, fields: List[str]) -> List[str]:
        """
        æéæ å°éå

        Args:
            fields: ååéååè¡¨

        Returns:
            List[str]: æ å°åçéååè¡¨
        """
        return [self.map_field(f) for f in fields]

    def get_mapping_rule(self, field: str) -> Optional[FieldMappingRule]:
        """
        è·åæ å°èå

        Args:
            field: ååéååç°

        Returns:
            Optional[FieldMappingRule]: æ å°èåïå¦æä¸å­å¨è¿åNone
        """
        return self.mappings.get(field)

    def add_mapping(self, original: str, mapped: str, description: str = ""):
        """
        æ·å æ å°èå

        Args:
            original: ååéå
            mapped: æ å°åéå?
            description: æè¿°
        """
        self.mappings[original] = FieldMappingRule(
            original=original,
            mapped=mapped,
            description=description
        )
        self.logger.info(f"æ·å éåæ å°: {original} -> {mapped}")

    def remove_mapping(self, original: str) -> bool:
        """
        çé¤æ å°èå

        Args:
            original: ååéå

        Returns:
            bool: æ¯å¦æåçé¤
        """
        if original in self.mappings:
            del self.mappings[original]
            self.logger.info(f"çé¤éåæ å°: {original}")
            return True
        return False

    def get_all_mappings(self) -> Dict[str, FieldMappingRule]:
        """è·åæææ å°èå?""
        return self.mappings.copy()

    def is_sensitive_field(self, field: str) -> bool:
        """
        å¤æ­æ¯å¦ä¸ºææéå?

        Args:
            field: éååç°

        Returns:
            bool: æ¯å¦ä¸ºææéå?
        """
        return field in self.mappings

    def get_reverse_mapping(self, mapped_field: str) -> Optional[str]:
        """
        ååæ¥æ¾ååéå

        Args:
            mapped_field: æ å°åçéå

        Returns:
            Optional[str]: ååéåïå¦æä¸å­å¨è¿åNone
        """
        for original, rule in self.mappings.items():
            if rule.mapped == mapped_field:
                return original
        return None
