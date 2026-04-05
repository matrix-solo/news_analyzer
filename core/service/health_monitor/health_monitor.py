#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""健康监控器"""
import logging
logger = logging.getLogger(__name__)

class HealthMonitor:
    def record_success(self, source: str):
        pass
    def record_failure(self, source: str, error: str = ""):
        pass
    def get_health_status(self, source: str) -> dict:
        return {"status": "unknown"}

_instance = None

def get_health_monitor() -> HealthMonitor:
    global _instance
    if _instance is None:
        _instance = HealthMonitor()
    return _instance
