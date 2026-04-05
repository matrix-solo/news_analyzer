#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""热度评分器"""
import logging
logger = logging.getLogger(__name__)

class HeatScorer:
    def calculate_heat_score_for_text(self, text: str) -> float:
        return 0.5

    def update_hotboard_cache(self, titles: list) -> list:
        return titles

_instance = None

def get_heat_scorer() -> HeatScorer:
    global _instance
    if _instance is None:
        _instance = HeatScorer()
    return _instance
