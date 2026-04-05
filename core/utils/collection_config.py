#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""采集配置管理器"""
import logging
logger = logging.getLogger(__name__)

class CollectionConfigManager:
    def get_source_config(self, source_name: str) -> dict:
        return {}
    def is_source_enabled(self, source_name: str) -> bool:
        return True

_instance = None

def get_collection_config_manager() -> CollectionConfigManager:
    global _instance
    if _instance is None:
        _instance = CollectionConfigManager()
    return _instance
